# AGENTS.md — Working Conventions

Level 3 in the `CONSTITUTION.md` §4 precedence order: these conventions say *how* work is done
here, they change often, and they override nothing above them. Read
`CONSTITUTION.md` → `PLAN.md` → `DESIGN.md` → this file, in that order.

## Environment baseline

- Python 3.12 (3.12.3 on the reference machine), Node 22 (v22.23.1).
- `uv` 0.12.14 at `~/.local/bin/uv`, **not on `PATH`**. It owns the project-local `.venv/`, and
  nothing is installed outside it.
- `relate` v1.3.0 installed by the human at `~/.local/bin/relate`, **also not on `PATH`**.
- The store is embedded in the sense that matters: one local file, no server, no network call at
  run time. It is reached through the `relate` **CLI binary** (D12); the `relate-db` Python package
  is neither installed nor a dependency, and `import relate` fails on purpose.
- Linux (WSL2, kernel 6.6) is where every command below was observed. The repository lives on a
  Windows drive, so `.venv/` is a **Linux** virtual environment: it is not reusable from Windows
  Python, and it is git-ignored, so a clean clone recreates it with one command.
- `uv` and `relate` are both off `PATH`. Either call them by full path or export the directory once
  per shell: `export PATH="$HOME/.local/bin:$PATH"`. The commands below assume the export.

## Layout

```
src/autopsy/__init__.py     package version; nothing else lives here by accident
src/autopsy/__main__.py     the whole public surface: python -m autopsy {build,demo,verify}
src/autopsy/store.py        the only seam to Relate: resolves the CLI, runs it without a shell,
                            owns the error contract (D12)
tests/                      pytest suite, mirroring src/, one behaviour per test
traces/                     committed sanitized traces, one per session (M1)
queries/                    the three demonstration queries (M3)
store/autopsy.rl            the committed single-file store (M2) — the deliverable
pyproject.toml · uv.lock    dependency manifest and lockfile; the lockfile is the environment
```

`src/` layout is deliberate (D9): it forces a real editable install, so `import autopsy` means the
installed package and never a stray directory that happened to be in the cwd. Directories annotated
with a milestone do not exist yet; do not create them ahead of that milestone.

## Commands

All of them run from the repository root.

```bash
uv sync                        # create .venv/ and install uv.lock exactly
uv sync --frozen               # same, refusing to re-resolve (what CI runs)
uv run pytest                  # the suite, inside the venv
uv run python -m autopsy --help
uv run python -m autopsy build # stubs until M2/M4: exit 3 and say so
uv add <package>==<version>    # the only way to add a dependency; never pip install
```

Invoking the Relate CLI by hand (it is not on `PATH`):

```bash
relate --version
relate -d "$TMP/src" --safe -c "CREATE (:Session {session_id:'probe'})"  # creates a directory store
relate clone "$TMP/src" "$TMP/autopsy.rl"                                 # SOURCE DEST: bundle it
relate info -d "$TMP/autopsy.rl" --json                                   # metadata without opening
```

`clone` copies an **existing** database; it does not create one from an empty directory. In code,
none of this is written by hand: everything goes through `autopsy.store`.

## Tests

- `uv run pytest`, no arguments: `testpaths = ["tests"]` is set in `pyproject.toml`.
- The suite must pass on a machine with **no `relate` binary and no network**: that is what CI is.
  A test that needs the CLI either skips or drives a stand-in process (`sys.executable`), never an
  assumption that the binary exists.
- One test per rule, asserting every observable effect of that rule: exit code, exact streams, and
  that rejected input left the store and counters unchanged. No golden files (D5).
- The constitution (§4) names the four blocks that must exist by M4: graph builder, demo queries,
  structural invariants of the store, and regeneration of the store from committed traces.

## Style

- Python 3.12, PEP 8, 4-space indent, 100-column soft limit, `from __future__ import annotations`,
  type hints on public functions.
- Absolute imports (`from autopsy.store import query`); no `sys.path` surgery, no relative-import
  tricks.
- Standard library first. A new dependency needs a reason in `PLAN.md` §2 and its own commit
  (`AGENTS.md` "Dependency policy").
- Docstrings explain **why** a rule exists, not what the next line says; identifiers, comments and
  messages are English.
- Errors are typed and named: define the exception, put the offending value in the message, never
  `except Exception: pass`. A missing tool and a rejected statement are different outcomes.
- No shell anywhere: subprocess calls take an argument list and `shell=False`.
- Exit codes are meaningful: `0` ok, `1` failure, `2` usage, `3` not implemented yet.
- Commands say on stdout what they did and on stderr why they failed. A stub never pretends.

## Environment

`.env` is git-ignored and never committed. The constitutional contract file is `.env.example`
(`CONSTITUTION.md` §VI and §6); it does **not** exist yet — see `PLAN.md` §8 L6 for why and what is
pending. Until it lands, this table is the contract.

| Variable | Used by | Meaning |
| --- | --- | --- |
| `AUTOPSY_RELATE_BIN` | `autopsy.store` | Path to the `relate` binary. Resolution order: explicit argument, this variable, `~/.local/bin/relate`, `PATH`. A value that does not resolve is an error, never a silent fallback. |
| `AUTOPSY_PROVIDER` · `AUTOPSY_MODEL` · `AUTOPSY_API_KEY` | live path (stretch, M6) | Provider selection is an environment decision, not a code one. Nothing in the replay path reads them, and no real value is ever committed. |
| `AUTOPSY_MAX_STEPS` · `AUTOPSY_MAX_TOKENS` | live path (stretch, M6) | Hard caps on any live run (§VI). An uncapped loop spends real money. |

## Package managers

- **Python: `uv`.** Authorized explicitly by the human author (see `CONSTITUTION.md` §3). It
  creates and manages the project-local `.venv/` the constitution requires; it replaces `pip`
  and `pip-tools`, not the `relate` CLI, and it adds no server.
- **Node: none today, and no Node package manager exists in this repository.** The viewer design
  (§5 of `DESIGN.md`) is one static directory with *no bundler, no framework and no dependency
  beyond the Relate WebAssembly package*; Node 22 only serves static files.
- **If a Node dependency ever becomes necessary, it is `pnpm` — never `npm`, never `yarn`.** The
  first `package.json` arrives together with:
  - `pnpm-workspace.yaml` carrying `minimumReleaseAge: 1440` (24-hour release cooldown; already
    pnpm's default, declared on purpose so the intent survives a version change) and
    `saveExact: true`;
  - a committed `pnpm-lock.yaml`;
  - the pnpm version pinned through `packageManager` + Corepack, and the Node version through
    `nodeVersion`, so "pnpm" and "Node 22" are pinned facts rather than local circumstances.
- Any *other* installer, package manager or tool still needs explicit authorization from the
  human author (`CONSTITUTION.md` §3). `uv` is the one standing exception; do not generalize it.

## Dependency policy

- **Exact versions only.** No `^`, no `~`, no ranges: `==` in Python, `saveExact` in Node.
- **Lockfiles are committed**: `uv.lock`, `pnpm-lock.yaml`. A resolve at install time is not a
  reproducible environment.
- **24-hour cooldown on fresh releases, on both sides**: `[tool.uv] exclude-newer = "1 day"`
  (`P1D`) once the recorder has a `pyproject.toml`, and `minimumReleaseAge: 1440` on the Node side.
  A per-package override (`exclude-newer-package`) is allowed only with a written reason in the
  commit message.
- Adding a dependency is a decision with its own rationale. The cost is not the package; it is
  that every future clean clone has to resolve it again.

## Branches and commits

- **Branch per milestone, off `main`.** The default branch is never the working branch. Names:
  `chore/m0-foundations`, `feat/m1-traces`, `feat/m2-graph-builder`, `feat/m3-queries`,
  `feat/m4-demo`, `docs/m5-readme`, `docs/m7-submission`.
- **Conventional Commits**, imperative and lowercase after the colon:
  `type(scope): summary` with `type` in `docs`, `chore`, `feat`, `fix`, `test`, `build`, `ci`.
- **One commit per reviewable work unit**, about 400 authored lines. Code, the tests that pin it and
  the documentation that describes it travel in the **same** commit, never as three.
- The commit body records what was verified and what was not. An unrun or red check is named as
  such: never implied green.
- **No push, no pull request, no merge**: those are the human's decisions (`CONSTITUTION.md` §4). A
  milestone branch stops at its last local commit.
- **Constitution amendments are their own commit** on the default branch, with their rationale,
  never inside a milestone commit (§5).
- A commit that touches the store or a committed trace records the exact command that produced it.

## Web and viewer

- The viewer is **out of scope for this cycle** (`DESIGN.md` §5). The interface is the committed
  store plus the CLI plus the Markdown report.
- No framework and no bundler. That is a design decision, not a preference: an artefact that needs
  `node_modules` to reproduce does not open cleanly on a stranger's clone.
- Revisit only if the viewer enters M6 with two clear days of buffer. Adopting a framework or a
  build step is a `DESIGN.md` amendment, never a quiet install.

## Git

- Repository hosted on Windows, terminal in WSL: use `git.exe`. Repository hosted on the native
  Linux filesystem: use `git`.

## Language

- Code, comments, identifiers, commit messages and repository documentation are written in English.
