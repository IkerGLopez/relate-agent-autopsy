"""The single seam between Agent Autopsy and the Relate CLI (D12).

Relate is reached through its command-line binary, never through a Python
binding: ``relate-db`` is not installed and is not a dependency. Everything
this project does to a store passes through this module, so no other module
locates the binary, builds a command line, opens a shell or parses a
subprocess result.

Three invariants, each with a reason:

- **The binary is resolved to a full path** in a fixed order, and a path that
  is not executable is an error that names it. ``relate`` is installed outside
  PATH on this machine, so "just call relate" is not reproducible.
- **No shell is ever involved.** Arguments travel as a list, so a value with a
  space or a quote reaches the CLI exactly as written; and nothing in a trace,
  a query file or an environment variable can be re-interpreted as shell
  syntax.
- **The project owns its error contract.** A missing CLI and a rejected
  statement are different outcomes for the caller (constitution §V: retry the
  plumbing, fail fast on logic), so they are different exceptions here, and
  the CLI's own exit code and diagnostic survive intact.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

#: Environment variable that overrides the search for the binary.
BINARY_ENV_VAR = "AUTOPSY_RELATE_BIN"

#: Where the human installed it, and how `relate` reaches this project.
FALLBACK_BINARY = Path.home() / ".local" / "bin" / "relate"

#: Upstream installation page, quoted in the error so a stranger can act.
INSTALL_URL = "https://relatedb.ai/docs/get-started/install"

#: A store command is local work; a hung CLI is a defect, not slowness.
DEFAULT_TIMEOUT_SECONDS = 300.0


class RelateNotFound(RuntimeError):
    """The ``relate`` binary could not be located or is not executable."""


class RelateError(RuntimeError):
    """The CLI ran and refused the command, or could not be started.

    The exit code and both streams are kept, because the caller has to be able
    to tell an error in the statement (exit 6, semantic error) from a missing
    binary or a storage problem.
    """

    def __init__(
        self,
        message: str,
        *,
        argv: Sequence[str],
        exit_code: int | None = None,
        stdout: str = "",
        stderr: str = "",
    ) -> None:
        super().__init__(message)
        self.argv = tuple(argv)
        self.exit_code = exit_code
        self.stdout = stdout
        self.stderr = stderr


@dataclass(frozen=True)
class RelateOutput:
    """One finished CLI invocation, as observed."""

    argv: tuple[str, ...]
    exit_code: int
    stdout: str
    stderr: str


def _require_executable(path: Path, source: str) -> Path:
    """Return ``path`` when it is an executable file, else raise."""
    if path.is_file() and os.access(path, os.X_OK):
        return path
    raise RelateNotFound(
        f"{source} points at {path}, which is not an executable file. "
        f"Install the Relate CLI from {INSTALL_URL}, or point ${BINARY_ENV_VAR} at it."
    )


def locate_binary(explicit: str | os.PathLike[str] | None = None) -> Path:
    """Resolve the ``relate`` binary to a full path.

    Order: an explicit argument, ``$AUTOPSY_RELATE_BIN``, the documented install
    location, then PATH. An explicit argument or variable that does not resolve
    is an error rather than a silent fallback: a caller that names a binary and
    gets a different one acts on a store it did not choose.
    """
    if explicit is not None:
        return _require_executable(Path(explicit).expanduser(), "the requested binary")
    from_environment = os.environ.get(BINARY_ENV_VAR, "").strip()
    if from_environment:
        return _require_executable(Path(from_environment).expanduser(), f"${BINARY_ENV_VAR}")
    if FALLBACK_BINARY.is_file() and os.access(FALLBACK_BINARY, os.X_OK):
        return FALLBACK_BINARY
    on_path = shutil.which("relate")
    if on_path:
        return Path(on_path)
    raise RelateNotFound(
        f"the Relate CLI was not found: no executable at ${BINARY_ENV_VAR}, "
        f"at {FALLBACK_BINARY}, or on PATH. Install it from {INSTALL_URL}."
    )


def run(
    args: Sequence[str],
    *,
    binary: str | os.PathLike[str] | None = None,
    check: bool = True,
    timeout: float | None = DEFAULT_TIMEOUT_SECONDS,
) -> RelateOutput:
    """Run ``relate`` with an argument vector, never through a shell.

    ``args`` excludes the program itself. With ``check`` (the default) a
    non-zero exit raises :class:`RelateError` carrying the exit code and both
    streams; with ``check=False`` the caller inspects
    :class:`RelateOutput` itself.
    """
    executable = locate_binary(binary)
    argv = [str(executable), *[str(arg) for arg in args]]
    try:
        completed = subprocess.run(  # noqa: S603 - argv list, shell disabled below
            argv,
            capture_output=True,
            text=True,
            shell=False,
            check=False,
            timeout=timeout,
        )
    except OSError as exc:
        raise RelateError(f"could not start {executable}: {exc}", argv=argv) from exc
    except subprocess.TimeoutExpired as exc:
        raise RelateError(
            f"{executable} did not finish within {timeout:g}s; the store may be locked "
            f"by another process.",
            argv=argv,
        ) from exc

    output = RelateOutput(
        argv=tuple(argv),
        exit_code=completed.returncode,
        stdout=completed.stdout,
        stderr=completed.stderr,
    )
    if check and output.exit_code != 0:
        raise RelateError(
            f"{executable} exited {output.exit_code}: {output.stderr.strip() or output.stdout.strip()}",
            argv=argv,
            exit_code=output.exit_code,
            stdout=output.stdout,
            stderr=output.stderr,
        )
    return output


def info(store: str | os.PathLike[str], *, binary: str | os.PathLike[str] | None = None) -> dict[str, Any]:
    """Return ``relate info --json`` for one store, as parsed JSON."""
    output = run(["info", "-d", str(store), "--json"], binary=binary)
    try:
        parsed = json.loads(output.stdout)
    except json.JSONDecodeError as exc:
        raise RelateError(
            f"`relate info` printed something that is not JSON: {output.stdout[:200]!r}",
            argv=output.argv,
            exit_code=output.exit_code,
            stdout=output.stdout,
            stderr=output.stderr,
        ) from exc
    if not isinstance(parsed, dict):
        raise RelateError(
            f"`relate info` returned {type(parsed).__name__}, expected a JSON object.",
            argv=output.argv,
            exit_code=output.exit_code,
            stdout=output.stdout,
            stderr=output.stderr,
        )
    return parsed


def query(
    store: str | os.PathLike[str],
    cypher: str,
    *,
    binary: str | os.PathLike[str] | None = None,
    max_rows: int = 0,
) -> list[dict[str, Any]]:
    """Run one read statement and return its rows.

    ``max_rows`` defaults to ``0`` (no cap) because the CLI truncates output at
    100 rows when it detects an agent harness (``DESIGN.md`` §0.2); a silently
    truncated result would be a wrong answer presented as a complete one.
    """
    output = run(
        ["-d", str(store), "--mode", "json", "--max-rows", str(max_rows), "-c", cypher],
        binary=binary,
    )
    try:
        payload = json.loads(output.stdout)
    except json.JSONDecodeError as exc:
        raise RelateError(
            f"`relate --mode json` printed something that is not JSON: {output.stdout[:200]!r}",
            argv=output.argv,
            exit_code=output.exit_code,
            stdout=output.stdout,
            stderr=output.stderr,
        ) from exc
    rows = payload.get("data") if isinstance(payload, dict) else None
    if not isinstance(rows, list):
        raise RelateError(
            f"`relate --mode json` returned no `data` list: {str(payload)[:200]}",
            argv=output.argv,
            exit_code=output.exit_code,
            stdout=output.stdout,
            stderr=output.stderr,
        )
    return rows
