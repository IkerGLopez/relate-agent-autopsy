"""The M0 sanity check for the Relate seam (D12, ``DESIGN.md`` §0).

One test, and it needs no ``relate`` binary: the CI runner has none, and a test
that skips everywhere proves nothing. It pins the three properties the rest of
the project builds on:

- the binary is resolved to an absolute path, and a path that cannot be
  executed is our own error naming it, not a bare ``FileNotFoundError``;
- arguments reach the process intact, which is only true if no shell parses
  the command line;
- a failure the CLI reports keeps its exit code and diagnostic instead of
  collapsing into a single untyped error.

The CLI's happy path (``relate clone`` and ``relate info --json`` on a real
store) is exercised by hand in the M0 definition of done, because it needs the
installed binary.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

from autopsy.store import BINARY_ENV_VAR, RelateError, RelateNotFound, locate_binary, run

# A stand-in program: it prints its own arguments as JSON, so the seam can be
# observed without Relate installed. `sys.executable` is always executable.
_ECHO_ARGV = "import json, sys; print(json.dumps(sys.argv[1:]))"
_EXIT_WITH_MESSAGE = "import sys; sys.exit('boom')"


def test_seam_resolves_a_full_path_and_never_uses_a_shell(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    # 1. Arguments travel as a list: the space inside "a b" survives, which is
    #    exactly what a shell would have split.
    output = run(["-c", _ECHO_ARGV, "a b", "--version"], binary=sys.executable)
    assert output.exit_code == 0
    assert json.loads(output.stdout) == ["a b", "--version"]
    assert Path(output.argv[0]).is_absolute()

    # 2. A named binary that cannot be executed is reported as ours, naming it.
    not_executable = tmp_path / "relate"
    not_executable.write_text("")
    monkeypatch.setenv(BINARY_ENV_VAR, str(not_executable))
    with pytest.raises(RelateNotFound) as named:
        locate_binary()
    assert str(not_executable) in str(named.value)

    # 3. A CLI failure keeps its exit code and its own diagnostic.
    monkeypatch.setenv(BINARY_ENV_VAR, sys.executable)
    unchecked = run(["-c", _EXIT_WITH_MESSAGE], check=False)
    assert unchecked.exit_code == 1
    assert "boom" in unchecked.stderr
    with pytest.raises(RelateError) as raised:
        run(["-c", _EXIT_WITH_MESSAGE])
    assert raised.value.exit_code == 1
