"""Command surface: ``python -m autopsy <command>``.

Three commands are the whole public surface (PLAN §2): ``build`` (traces ->
store), ``demo`` (run the three queries and print the report), ``verify``
(rebuild into a temporary store and compare normalized query results).

They are stubs today. A stub here is not a placeholder that pretends: each one
prints why it cannot run yet, names the milestone that implements it, and
exits with a non-zero code, so no caller, script or judge can mistake "nothing
happened" for success (constitution §VII).
"""

from __future__ import annotations

import argparse
import sys
from collections.abc import Sequence

PROGRAM = "python -m autopsy"

# Distinct from 1 (a real failure) and from 2 (argparse usage error): "this
# command exists, it is simply not built yet".
EXIT_NOT_IMPLEMENTED = 3

_NOT_IMPLEMENTED_HELP = " (not implemented yet: exits %d)" % EXIT_NOT_IMPLEMENTED


def _pending(command: str, milestone: str, detail: str) -> int:
    """Report a stub honestly and return its exit code."""
    print(f"{PROGRAM} {command}: not implemented yet ({milestone}).", file=sys.stderr)
    print(detail, file=sys.stderr)
    return EXIT_NOT_IMPLEMENTED


def build(_: argparse.Namespace) -> int:
    """Materialize the committed traces into ``store/autopsy.rl``."""
    return _pending(
        "build",
        "M2, graph builder",
        "Nothing was written: there are no traces (M1) and store/autopsy.rl does not exist.",
    )


def demo(_: argparse.Namespace) -> int:
    """Run the three demonstration queries and print the Markdown report."""
    return _pending(
        "demo",
        "M4, demo command and report",
        "Nothing was queried: it needs the committed store and the three queries (M2, M3).",
    )


def verify(_: argparse.Namespace) -> int:
    """Rebuild into a temporary store and compare normalized query results."""
    return _pending(
        "verify",
        "M4, regeneration check",
        "Nothing was compared: it needs build, the three queries and the committed store.",
    )


def build_parser() -> argparse.ArgumentParser:
    """Build the argument parser for the three commands."""
    parser = argparse.ArgumentParser(
        prog=PROGRAM,
        description="Agent Autopsy — a forensic report of agent decisions.",
    )
    subcommands = parser.add_subparsers(dest="command", required=True, metavar="<command>")

    for name, handler, help_text in (
        ("build", build, "materialize the committed traces into store/autopsy.rl"),
        ("demo", demo, "run the three demonstration queries and print the report"),
        ("verify", verify, "rebuild and compare against the committed store"),
    ):
        subparser = subcommands.add_parser(name, help=help_text + _NOT_IMPLEMENTED_HELP)
        subparser.set_defaults(handler=handler)

    return parser


def main(argv: Sequence[str] | None = None) -> int:
    """Parse ``argv`` and run one command, returning its exit code."""
    args = build_parser().parse_args(sys.argv[1:] if argv is None else list(argv))
    return int(args.handler(args))


if __name__ == "__main__":
    raise SystemExit(main())
