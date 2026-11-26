"""Agent Autopsy: forensic report of agent decisions.

The package holds one Python surface with two halves, and nothing else lives
here by accident:

- `autopsy.__main__`: the three-command public surface (`build`, `demo`,
  `verify`), invoked as `python -m autopsy <command>`.
- `autopsy.store`: the one seam between this project and the Relate CLI. No
  other module locates the binary, builds a command line or parses a
  subprocess result (D12).

The graph itself is the deliverable (constitution §I); this package builds and
reads it, and never describes it in place of querying it.
"""

__version__ = "0.0.0"

__all__ = ["__version__"]
