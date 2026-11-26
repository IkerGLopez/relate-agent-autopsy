# Agent Autopsy

Forensics for agent decisions. A small instrumented agent searches, reads, decides and acts, and
every step is recorded as a node or an edge in an embedded [Relate](https://relatedb.ai/docs/get-started/install)
graph. The deliverable is that store, committed to the repository and queryable by a stranger: what
the agent had in front of it, what it decided, what it did, and which policy — if any — supported
the decision.

**Status: skeleton.** Only M0 (foundations) is closed. Sections marked *pending* carry no verified
claim yet, and the three commands are stubs that exit non-zero on purpose. See `PLAN.md` for scope
and sequencing, `CONSTITUTION.md` for the rules.

## Use case

*Pending M5 — this section becomes the judge-facing narrative once `autopsy demo` runs.*

The report answers three questions that a trace viewer cannot, each from one query against the
committed store:

1. **Why did this decision happen?** — the causal chain of context, evidence and action behind one
   decision.
2. **Which sessions share the poisoned document?** — contamination fan-out across sessions on
   shared document nodes, the cross-session reach a per-session span tree cannot show.
3. **Which decisions have no valid supporting policy?** — decisions whose policy is absent or does
   not cover them.

The agent is deliberately shallow and its reasoning deliberately shallow on purpose: the value is
in the graph, not in the model.

## How it uses Relate

- **One committed store, one file.** `store/autopsy.rl` is a single-file Relate bundle, so the
  artefact travels as one file and `relate info` reads it without opening it.
- **One seam, over the CLI.** Everything this project does to a store goes through
  `src/autopsy/store.py`, which resolves the `relate` binary by full path, runs it with an argument
  list and no shell, and owns its error contract (D12). The `relate-db` Python package is neither
  installed nor a dependency.
- **Shared identity.** Documents, chunks, policies and entities are shared nodes across sessions,
  never per-session copies: the contamination query exists because of that.
- **Rebuildable.** `autopsy verify` rebuilds the store from the committed traces into a temporary
  directory and compares normalized query results, so "the store is the deliverable" stays a
  checkable claim rather than a promise.

Relate's own store modes, Cypher support and API surface are documented upstream; `DESIGN.md` §0
records exactly which of them this project verified, with the command for each.

## Setup and run

Observed on: Ubuntu (WSL2, Linux 6.6), Python 3.12.3, uv 0.12.14, `relate` v1.3.0 at
`~/.local/bin/relate`, git 2.51. Both `uv` and `relate` are installed **off `PATH`**, so the
commands below use full paths; `export PATH="$HOME/.local/bin:$PATH"` makes the short forms work.

From a clean clone:

```bash
# 1. Python environment: creates .venv/ and installs the locked versions
uv sync

# 2. The Relate CLI (not on PATH). Install it once from
#    https://relatedb.ai/docs/get-started/install, then:
~/.local/bin/relate --version        # Relate v1.3.0

# 3. The test suite
uv run pytest

# 4. The command surface
uv run python -m autopsy --help
```

Nothing is installed outside `.venv/`. There is no Node step: the viewer is out of scope for this
cycle and the interface is the committed store plus the CLI plus a Markdown report.

Environment variables, all optional on the replay path: `AUTOPSY_RELATE_BIN` (where the `relate`
binary lives, resolved before `~/.local/bin/relate` and `PATH`), and — for the optional live path
only — `AUTOPSY_PROVIDER`, `AUTOPSY_MODEL`, `AUTOPSY_API_KEY`, `AUTOPSY_MAX_STEPS`,
`AUTOPSY_MAX_TOKENS`. `.env` is git-ignored. The constitutional contract file is `.env.example`
(`CONSTITUTION.md` §VI); it is not committed yet, and `PLAN.md` §8 L6 records that gap rather than
hiding it. `AGENTS.md` carries the same table until the file lands.

The three commands exist as stubs at M0. Each prints why it cannot run yet and which milestone
implements it, and exits `3`:

```bash
uv run python -m autopsy build    # M2, graph builder
uv run python -m autopsy demo     # M4, demo and report
uv run python -m autopsy verify   # M4, regeneration check
```

## Where the data lives

| Path | What it is | Exists today |
| --- | --- | --- |
| `traces/` | one sanitized JSON trace per session, versioned by `trace_version` | no (M1) |
| `store/autopsy.rl` | the committed single-file store — the deliverable | no (M2) |
| `queries/` | the three demonstration queries | no (M3) |
| `src/autopsy/` | the package: command surface and the Relate seam | yes |
| `tests/` | the pytest suite | yes |
| `pyproject.toml` · `uv.lock` | dependency manifest and lockfile; the lockfile is the environment | yes |
| `CONSTITUTION.md` · `PLAN.md` · `DESIGN.md` · `AGENTS.md` | rules, scope and sequencing, design, working conventions | yes |
