# AGENTS.md — Working Conventions

Level 3 in the `CONSTITUTION.md` §4 precedence order: these conventions say *how* work is done
here, they change often, and they override nothing above them. Read
`CONSTITUTION.md` → `PLAN.md` → `DESIGN.md` → this file, in that order.

## Environment baseline

- Python 3.12, Node 22.
- `relate` v1.3.0 installed by the human at `~/.local/bin/relate`, **not on `PATH`** by default.
- The store is used as an embedded library, in the project-local virtual environment, with no
  server and no network calls at run time.

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
