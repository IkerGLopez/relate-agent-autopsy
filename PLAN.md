# PLAN — Agent Autopsy

**Status:** active · **Created:** 2026-11-26 · **Owner:** human author
**Hard deadline:** 2026-12-11 18:00 PST = **2026-12-12 03:00 CET**
**Remaining time measured at creation:** `date` = `Thu 26 Nov 2026 17:47 CET` → **15 days 9 hours**.

This plan states scope, sequencing, open work, per-principle status and risks. It is a plan, not a
certificate: nothing here proves the code satisfies the constitution, and nothing here is permission to
publish. Commit, push, pull request, merge and release remain the human's decisions (§4).

Precedence (§4): platform safety and the human's live instruction → constitution → this plan,
`AGENTS.md`, `DESIGN.md` → recommendations. Where this plan and the constitution disagree, the
constitution wins and this plan gets amended.

---

## 1. Scope

### 1.1 In scope

1. **Instrumented agent loop, replay implementation.** An owned loop with the single seam
   `next_step(messages, tools)` and one implemented backend: `replay`, which reads a committed trace.
2. **Three committed traces**, one per mandatory demonstration query, each sanitized and versioned by
   an explicit `trace_version` field.
3. **Graph builder** that materializes the three traces into one Relate store, with mechanical
   provenance edges only.
4. **One committed store** at `store/autopsy.rl`, plus a documented, deterministic regeneration path
   so the store can be rebuilt from the committed traces.
5. **Three demonstration queries** run against the committed store:
   causal path (why a decision happened), contamination fan-out (which sessions share a poisoned
   document), and decisions with no valid supporting policy.
6. **A demo command** and its Markdown-report fallback: `python -m autopsy demo`.
7. **A pytest suite** covering the four blocks §4 names: graph builder, demo queries, structural
   invariants of the store, regeneration of the store from committed traces.
8. **Judge-facing reproduction**: `README.md` with the exact commands a stranger runs on a clean clone,
   and `.env.example` for the secrets contract.
9. **A minimal GitHub Actions workflow** running `pytest` on push (human-triggered, see §6 R5).
10. **Submission artefacts**: final committed store, README, short video, Devpost submission.

### 1.2 Out of scope — the explicit cut

| Excluded | Why it is cut |
| --- | --- |
| Live agent path as a demo prerequisite | §IV: the live path is an optional trace producer, never a prerequisite for inspecting traces. Deferred to the buffer window and cut first. |
| Browser viewer (Node + WASM) as a planned deliverable | The scored artefact is the queryable store (§I). Stretch only; fallback is the CLI + Markdown report. |
| Multi-agent, multi-user, auth, permissions | §1: not a multi-agent framework, not a product with users. |
| General-purpose tracing of third-party agents | §1. |
| Prompt-injection detection or "safe agent" claims | §1: explicitly excluded, and not claimed anywhere. |
| Schema migrations, versioned store upgrade path | Single hackathon store, rebuilt from traces. |
| Production readiness, packaging for distribution, docs site | §1: no production commitments. |
| Extra demo sessions beyond the three | Each extra session costs curation days and adds no query coverage. |

### 1.3 Declared simplifications (§1 requires these to be declared)

- The corpus is tiny (three short sessions, a handful of documents). Vector search is therefore
  demonstrative, not evaluative: recall quality on a 20-chunk corpus proves nothing about real corpora.
- The agent is deliberately shallow; no claim is made about decision quality, safety or
  representativeness.
- Only the retry half of §V is demonstrated in the store. The "logic failure aborts" half is not
  demonstrated and is recorded as unverified unless a session can carry it cheaply (§5, principle V).
- No parallelism: one writer, one process, one store. Concurrency behaviour is untested and unclaimed.
- No live provider call is part of the reproduction path, so no rate-limit or cost behaviour is shown.

---

## 2. Decisions taken (and the reason)

These were decided with the human before this plan was written. They are recorded here so a later
reader can judge whether they still hold.

| # | Decision | Reason | Cost to reverse |
| --- | --- | --- | --- |
| D1 | **Embeddings: TF-IDF + TruncatedSVD (scikit-learn), ~128 dimensions, seeded, computed locally with no network.** | Only option that is deterministic, offline, and cheap on CPU; reproducibility is scored by a stranger on a clean clone. | Low — vectors live in one builder module and one node property. |
| D2 | **Replay-only scope. Live path is a stretch item inside the buffer window.** | §IV makes the live path optional; the three queries and the whole suite read from committed traces. | Low upward, free downward. |
| D3 | **Viewer is a stretch item; fallback is CLI + Markdown report.** | Removes the largest technical unknown from the critical path. | Low. |
| D4 | **Three sessions, one per mandatory query, with a visible retry in one of them.** | Each session justifies exactly one query; the retry gives §V evidence in the store. | Medium — traces are curated by hand. |
| D5 | **pytest, exactly the four §4 blocks. No golden-file snapshots.** | Covers what the constitution names, nothing that needs hand-maintained fixtures. | Low. |
| D6 | **Commit the `.rl` store and ship a deterministic regeneration path.** | The judge opens the binary without running anything (§I), and the §4 regeneration test needs a reference. | Low. |
| D7 | **`AGENTS.md` is created in the first work unit.** | Owns working conventions so delegated work does not reinvent commands and style. | Low. |
| D8 | **Minimal GitHub Actions workflow: `pytest` on push.** | External evidence that the suite runs clean. Accepted risk: it needs a network and a human push (§6 R5). | Low. |
| D9 | **Layout: `src/autopsy/`, `traces/`, `queries/`, `store/autopsy.rl`, `python -m autopsy <cmd>`.** | `src/` layout forces an editable install and blocks accidental imports; flat, predictable artefact paths. | Medium (README, imports, tests). |
| D10 | **Repo hygiene: `CONSTITUTION.md` is committed as its own standalone change; `constitution_template.md` is removed from the repository.** | §5: the constitution enters as its own change with its rationale, never inside a feature commit. The template is a local leftover, not a project artefact. | Constitution commit: low. Template deletion: irreversible by design. |
| D11 | **Branch per milestone; Conventional Commit messages; work-unit sized commits; no push.** | Keeps each milestone reviewable in isolation and keeps the remote untouched until the human decides (§4). | Low. |
| D12 | **The builder reaches Relate through exactly one seam (`store.py`) over the `relate` CLI; the `relate-db` Python package is neither installed nor a dependency.** | The Python library is absent today and the CLI surface is already verified (`DESIGN.md` §0); one seam keeps the store code testable and the dependency count at two. Closes R1/OW4, so M2 is not blocked. | Low — the seam is one module; a binding could replace its body without touching callers. |

Decisions taken unilaterally because they do not change the outcome:

- **Dependencies stay minimal:** `scikit-learn` (which brings `numpy`) and `pytest`. The Relate
  integration is the `relate` v1.3.0 CLI invoked by full path, **not** the `relate-db` Python package
  (D12). No web framework, no templating engine, no type checker, no pytest plugins. Report rendering
  is plain f-strings. Reason: every extra dependency is one more thing that can fail on the judge's machine.
- **Registry policy:** nothing is installed outside the project-local `.venv`, and no package manager is
  added beyond `pip` (§3).
- **Determinism is verified by query-result equality, not by byte equality of the `.rl` binary.**
  Reason: a store is a directory/bundle with internal layout the project does not control; asserting
  byte equality would test Relate, not this project.
- **Public command surface is three subcommands:** `build` (traces → store), `demo` (run the three
  queries and print the report), `verify` (rebuild into a temporary store and compare normalized query
  results with the committed store). Reason: `verify` is what makes §I and §VII checkable by a stranger
  with one command.
- **Environment baseline:** Python 3.12.3, Node 22.23.1, `relate` v1.3.0 at `~/.local/bin/relate`
  (invoked by full path), git 2.43.0. Observed on the repo, not mandated by the plan.

---

## 3. Sequencing

Calendar reality: **15 days 9 hours** at creation, from Thu 26 Nov 2026 17:47 CET to Sat 12 Dec 2026
03:00 CET. The last calendar day is cut in half by the deadline, so the plan works to a
**code freeze on Thu 10 Dec 18:00 CET**, a **submission target of Fri 11 Dec 12:00 CET**, and keeps
**15 hours of absolute buffer** before the hard close.

Milestone order is dependency-driven: nothing can be built before the trace format exists, nothing can
be queried before the store exists, and nothing can be documented before the demo runs.

### M0 — Foundations and hygiene
**Window:** Thu 26 Nov (rest of day) → Fri 27 Nov · **Branch:** standalone constitution commit on the
default branch, then `chore/m0-foundations` · **Depends on:** nothing.

Deliverables (state at close; each line names the commit that holds it):
- [x] `CONSTITUTION.md` committed **as its own standalone commit** with its rationale (§5). Requires the
      human's explicit go-ahead for the commit — `ceb6305`.
- [x] `constitution_template.md` removed from the repository (irreversible; authorised as D10).
- [x] `AGENTS.md`: commands, layout, style, test invocation, branch/commit policy — created in
      `f854fd1`, completed on `chore/m0-foundations`.
- [x] `pyproject.toml`, `.gitignore` review (`5d05fc0`), `README.md` skeleton (existing headings kept).
- [x] `.env.example` — delivered by the human author's hand on this branch: the harness denies that
      path to agent tools by name, so the agent wrote the content and the human placed and staged it.
      See §8 L6 for the mechanism and for what the split of duties was.
- [x] `.venv` created with `scikit-learn` and `pytest` installed **inside it**; **no `relate` Python
      package is installed** (D12). The seam that invokes the `relate` CLI lands in `src/autopsy/store.py`,
      and the commands it runs are recorded in `AGENTS.md` and `README.md`.
- [x] `src/autopsy/` skeleton: `__init__.py`, `__main__.py` with the three subcommand stubs, one sanity test.
- [x] `.github/workflows/tests.yml` running `pytest` (it cannot be observed green until the human pushes)
      — file committed, green run **unverified**.

**Definition of done (verifiable):**
1. In the project venv, `python -c "import autopsy"` exits 0, and the CLI integration answers:
   `~/.local/bin/relate clone <tmpdir> autopsy.rl` exits 0 and
   `~/.local/bin/relate info -d <tmpdir>/autopsy.rl --json` prints JSON — the commands `DESIGN.md` §0
   already verified. No `import relate` is expected or required (D12).
2. `python -m pytest` runs and exits 0.
3. `git log --oneline -1 -- CONSTITUTION.md` shows a commit touching only the constitution.
4. `git status --short` is clean except `PLAN.md` and untracked work-in-progress.
5. The install command for the Relate library is reproducible from `README.md` alone.

**Blocker risk closed:** the Relate Python library is absent and stays absent — the builder reaches
Relate through one seam, the CLI (D12), so nothing in M0 or M2 waits on an install. Residual risk
stays in §6 R1: every store read and write needs the `relate` binary.

**Status at close (2026-11-26): closed.** Every deliverable landed; one of them needed the human's
own hand because the agent harness denies that path. Per-item evidence, the one DoD correction and
everything left unverified are in §8 L6. In short: DoD 1 passes with a correction (item 1 as written
cannot pass: `relate clone` takes `SOURCE DEST` and needs an existing database, so the recorded
sequence creates a source store first), DoD 2–4 pass as written, and DoD 5 passes for the `.venv`,
the CLI invocation and the environment contract.

### M1 — Trace format, three curated traces, sanitizer
**Window:** Sat 28 Nov → Sun 29 Nov · **Branch:** `feat/m1-traces` · **Depends on:** M0, and the
`DESIGN.md` section on the trace format.

Deliverables: one JSON trace per session, each with `trace_version`; the sanitizer that scrubs the
traces; a sanitizer test.

**Definition of done:**
1. All three traces load and validate against the `trace_version` contract (a test fails if a field is
   missing or unknown).
2. The sanitizer test **fails first** on a planted token/email fixture and passes after the scrubber runs.
3. `grep -riE '(api[_-]?key|token|password|@[a-z0-9.-]+\.)' traces/` returns no real secret or personal
   datum — the check and its result are recorded in the log.
4. Session 3 contains a failed call, its error, and its retry, as distinct steps.

### M2 — Graph builder and structural invariants
**Window:** Mon 30 Nov → Tue 1 Dec · **Branch:** `feat/m2-graph-builder` · **Depends on:** M1.

Deliverables: `autopsy build` writing `store/autopsy.rl`; provenance edges per `DESIGN.md`;
structural-invariant tests.

**Definition of done:**
1. `python -m autopsy build --traces traces/ --out store/autopsy.rl` exits 0 and reports node/edge counts.
2. Structural-invariant tests pass: every step node reachable from its session; every `INFLUENCED` edge
   carries an observable marker (context inclusion or cited marker) and never an inferred rationale;
   no orphan nodes; shared document/policy/entity nodes are one node, not per-session copies (§III).
3. Two consecutive builds produce identical normalized query results (determinism check, per §2).
4. An `INFLUENCED` edge with no mechanical basis is rejected by the builder, with a test proving the rejection.

### M3 — The three demonstration queries
**Window:** Wed 2 Dec → Thu 3 Dec · **Branch:** `feat/m3-queries` · **Depends on:** M2.

Deliverables: the three queries in `queries/`, plus their tests against the committed store.

**Definition of done:**
1. **Causal path**: the query returns, for a named decision, the ordered chain of context → evidence →
   action that the trace supports; a test asserts the expected decision is present with its support.
2. **Contamination fan-out**: the query returns at least two sessions sharing the poisoned document, and
   a test asserts the cross-session reach that a span tree cannot show (§III).
3. **No valid policy**: the query returns the decisions whose supporting policy is absent or
   non-covering, and a test asserts the set is exactly the intended one (no false positives).
4. All three run with no network and no credentials.

### M4 — Demo command, report, regeneration check
**Window:** Fri 4 Dec · **Branch:** `feat/m4-demo` · **Depends on:** M3.

Deliverables: `python -m autopsy demo` (three report sections) and `python -m autopsy verify`.

**Definition of done:**
1. `python -m autopsy demo` exits 0 and prints the three sections from **the committed store**, not a
   freshly built one.
2. `python -m autopsy verify` rebuilds into a temporary directory and reports equality of normalized
   query results; a test wraps it and the §4 regeneration block is green.
3. `demo` run on a machine with `HTTP_PROXY` unset and no `.env` produces the same output.

### M5 — Judge-facing reproduction
**Window:** Sat 5 Dec · **Branch:** `docs/m5-readme` · **Depends on:** M4.

Deliverables: final `README.md` (use case, how it uses Relate, setup and run, where the data lives,
what is unverified), `.env.example`.

**Definition of done:** a cold walkthrough in a fresh clone with a fresh `.venv` reproduces the demo in
**≤ 5 commands**; the commands are copy-pasted from the README, not from memory, and the transcript is
recorded in the log. Any command that needed a correction is fixed in the README, not in the transcript.

### M6 — Buffer and stretch window
**Window:** Sun 6 Dec → Tue 8 Dec · **Branch:** one branch per started item · **Depends on:** M5.

This window has two jobs, in this order: absorb slippage from M0–M5, then take stretch items **only if
the window still has 2 full days**. Stretch items are taken in cut order (see §3.1) and any started item
must finish inside the window or be reverted before the freeze. Also the window where the human pushes
and the first GitHub Actions run is observed.

**Definition of done:** either every previous milestone's DoD re-verified with no open defect, or the
slippage is fixed and re-verified. Stretch items carry their own DoD written before they start; without
one they do not start.

### M7 — Submission
**Window:** Wed 9 Dec → Fri 11 Dec 12:00 CET · **Branch:** `docs/m7-submission` · **Depends on:** M6.

Deliverables: final store committed, README final, short video, Devpost submission filed,
`PLAN.md`/`DESIGN.md` log updated with what remains unverified.

**Definition of done:**
1. Code freeze Thu 10 Dec 18:00 CET: after that, no source change without the human's explicit approval.
2. The committed store is the one the committed traces regenerate (verified by `autopsy verify` on the
   exact commit being submitted).
3. Video shows the three queries live against the committed store, without editing out a failure.
4. Submission filed before Fri 11 Dec 12:00 CET — **15 hours before the hard close**.
5. Closure recorded as *implemented and verified* or *closed with gaps* (§4), never blurred.

### 3.1 What gets cut first, in order

When the calendar slips, cut from the top of this list, never from the milestones M1–M5 themselves:

1. **Viewer** (stretch, D3) — never started unless the window is clear.
2. **Live path** (stretch, D2) — this is the item with real cost and real secrets exposure.
3. **CI green run** — the workflow file stays; a red or unreachable CI run is reported as unverified
   evidence instead of being debugged on the closing day.
4. **Markdown report polish** — the report keeps its three sections, loses formatting.
5. **Session 3 richness** — fewer turns, same required retry evidence.
6. **Extra curated documents** — fewer chunks; queries still return their expected sets.

Never cut: the committed store, the three mandatory queries, the four §4 test blocks, the sanitizer,
the README reproduction path, the video, the submission. Below that line the outcome is
**closed with gaps** with the gap named, not a degraded claim of success.

---

## 4. Open work

| ID | Item | Status | Owner | Note |
| --- | --- | --- | --- | --- |
| OW1 | Commit `CONSTITUTION.md` as a standalone change | **done** | agent (go-ahead given) | `ceb6305`: one file changed, rationale in the commit body (§5). |
| OW2 | Remove `constitution_template.md` from the repo | **done** | agent (authorised, D10) | Irreversible and executed. The file governed a different project (BidCraft) and linked to `.ai/constitution.md`, so it was never an Agent Autopsy artefact. |
| OW3 | Create `AGENTS.md` | **done** | agent | Created in `f854fd1`; completed on `chore/m0-foundations` with layout, commands, environment, tests, style and branch/commit policy. |
| OW4 | Project `.venv` + Relate integration | **closed** | agent | Closed without installing `relate-db`: one seam over the `relate` CLI (D12, `DESIGN.md` §0). M2 is not blocked by it. |
| OW5 | Verify `relate` v1.3.0 store create/query/vector-index surface | **done** | agent | Satisfied by the probe table in `DESIGN.md` §0, where every row carries its command and its observed result. |
| OW6 | `DESIGN.md` | pending | human + agent | Next step after this plan. Everything in §7. |
| OW7 | Trace format, three traces, sanitizer | pending | agent | M1. |
| OW8 | Graph builder + structural invariants | pending | agent | M2. |
| OW9 | Three demonstration queries | pending | agent | M3. |
| OW10 | `demo` and `verify` subcommands | pending | agent | M4. |
| OW11 | Judge-facing `README.md` + `.env.example` | pending | agent | M5 for the README half. The contract file landed on `chore/m0-foundations`: content written by the agent, placed and staged by the human author because the harness guard denies that path to agent tools (§8 L6). |
| OW12 | GitHub Actions workflow, first green run | blocked | human push, then agent reads result | Workflow committed on `chore/m0-foundations` (`uv sync --frozen`, `uv run --frozen pytest`); the green run still needs a push decision; no `gh`, no token. |
| OW13 | First push to the public remote | blocked | human | §4: push is the human's decision. |
| OW14 | Video recording | pending | human | Needs the frozen store. |
| OW15 | Devpost submission | pending | human | Target Fri 11 Dec 12:00 CET. |
| OW16 | Stretch: viewer | pending | agent | Only inside M6 with a cleared window. |
| OW17 | Stretch: live path | pending | agent | Same rule; cut before the viewer only if secrets risk outweighs the value. |

---

## 5. Per-principle status

Status vocabulary is the constitution's: `implemented`, `pending`, `not applicable to the demo`.
Nothing below is currently `implemented`: no store exists yet.

| Principle | Status | Justification |
| --- | --- | --- |
| **I. The Graph Is the Deliverable** | pending | Becomes implemented at M2 + M4 + M5: every claim in README maps to one of the three queries against the committed `store/autopsy.rl`, and `autopsy verify` checks it. |
| **II. Mechanical Provenance, Never Inferred Intent** | pending | Becomes implemented at M2: `INFLUENCED` edges carry only the observed marker (chunk present in context, or cited marker); the builder rejects an edge with no mechanical basis and a test proves the rejection. |
| **III. One Store, Shared Identity** | pending | Becomes implemented at M2 and verified at M3: a single `store/autopsy.rl`, and the fan-out query crosses session boundaries on shared document nodes. |
| **IV. Replay Without Secrets or Network** | pending | Becomes implemented at M4/M5: the demo, the three queries and every check run from committed traces and the committed store, with no API key and no network. The optional live producer does not exist in this scope and is declared as a gap, not concealed (D2). |
| **V. Retry the Plumbing, Fail Fast on Logic** | pending | Partially reachable: the retry half is demonstrated as visible nodes in session 3 (M1). The logic-failure-aborts half is not demonstrated and will be recorded as unverified unless a session can carry it without extra curation cost. |
| **VI. No Secrets, No Personal Data** | pending | Becomes implemented at M1: sanitizer with a failing-then-passing test, `.env.example` as the only secrets artefact, no credential in traces or store. Token/step caps only become applicable if the live path is taken (stretch). |
| **VII. Verified, or Declared Unverified** | pending | Becomes implemented at M7: README and log state what was checked, on which commit and environment, and what stays unverified — including the viewer, the live path and the abort half of principle V. |

---

## 6. Risks

| ID | Risk | Mitigation | Alarm signal (act when this fires) |
| --- | --- | --- | --- |
| R1 | **Resolved 2026-11-26 (D12).** Residual: no `relate` Python binding exists, so every store read and write goes through the CLI binary, and a judge without it cannot run the demo. | Resolved by the CLI-behind-a-seam builder (`DESIGN.md` §0, §1); the CLI install link stays in `README.md` and `CONSTITUTION.md` §6. `relate-db` does resolve on PyPI for this platform (`relate_db-1.3.0-cp39-abi3-manylinux2014_x86_64`) but is deliberately not adopted. | `DESIGN.md` §0 stops matching what the builder actually runs, or a reproduction step needs a Python binding after all. |
| R2 | Builds are not deterministic: SVD signs, float drift, dict ordering, or vector index rebuild order. | Pin dependency versions; fixed seeds; sorted iteration everywhere; determinism checked by normalized query results (§2). | Two consecutive builds return different query results, or the same query changes across a dependency bump. |
| R3 | The committed `.rl` store bloats the public repository. | Build small, commit once, rebuild from traces instead of committing iterations; `/tmp` for working stores. | `store/autopsy.rl` above ~25 MB, or a second copy appears under version control. |
| R4 | Vector search on a ~20-chunk corpus returns nonsense, making the hybrid retrieval look decorative. | Lexical scoring dominates by design; the declared simplification says so; queries that must be sharp are anchored on graph structure, not on vector similarity. | A query whose expected answer depends on semantic similarity fails twice in a row. |
| R5 | CI (D8) needs a push and a network, and there is no `gh` and no token; a red workflow on the closing day costs hours. | CI is evidence, never a gate. Local `pytest` output is recorded as the acceptance evidence. | Workflow red or not triggered by Tue 8 Dec → report CI as unverified and keep the local evidence. |
| R6 | Stretch items (viewer, live path) eat the buffer and destabilise the store. | Hard rule in M6: only with 2 clear days, own DoD first, finish or revert inside the window. | A stretch branch open past Tue 8 Dec → revert it. |
| R7 | A secret or personal datum leaks into a committed trace or the store, on a public repo, permanently. | Sanitizer with a test, plus a grep check before each trace commit; no real personal data is ever used as input. | Any hit on the secrets/personal-data grep, or any live provider response pasted into a trace. |
| R8 | The deadline compresses: the last day ends at 03:00 CET, and a late defect lands with no buffer. | Freeze Thu 10 Dec 18:00, submit Fri 11 Dec 12:00, keep 15 hours. | Any milestone finishing later than its window's last day → apply the cut list (§3.1) immediately, not at the end. |
| R9 | The demo is declared done while the store does not regenerate from the committed traces (a hand-built store). | `autopsy verify` is part of the §4 suite and runs on the exact submitted commit. | `verify` reports a difference at freeze → the store is rebuilt from traces or the gap is declared. |
| R10 | The trace format drifts while traces are already curated, forcing rework. | The format lands in `DESIGN.md` **before** M1 writes traces; format changes are a `trace_version` bump. | A schema change after a trace is committed without a version bump. |

---

## 7. Not decided here — belongs to `DESIGN.md`

This plan deliberately says nothing about:

1. **Graph schema**: node labels and edge types, their cardinality, and which properties each carries.
2. **Node and edge semantics**: what a step, a decision, an action, a document, a policy and an entity
   mean, and the precise rule that makes an edge observable rather than inferred.
3. **Query catalogue**: the Cypher of the three demonstration queries, their expected result shapes, and
   any auxiliary queries used by the tests.
4. **Trace format**: the JSON layout, `trace_version` contract, step taxonomy, retry representation, and
   sanitization contract at the field level.
5. **Viewer design**: whether it exists, what it renders, and its WASM/Node architecture.
6. **Retrieval scoring**: exact lexical and vector weighting, the SVD dimension, thresholds, and the
   chunking strategy (the embedding *source* is decided here as D1; its formula is not).
7. **Report rendering**: the exact Markdown structure of `autopsy demo` output.

---

## 8. Log

- **L1 (2026-11-26)** — Human's request, verbatim: *"Escribir PLAN.md en la raíz del repo, en inglés. No
  escribas DESIGN.md, no escribas código, no instales nada."* Constitution read first and reported
  `read`; no conflict found between the request and the constitution.
- **L2 (2026-11-26)** — Measured calendar: `date` = Thu 26 Nov 2026 17:47 CET; deadline Sat 12 Dec 2026
  03:00 CET; **15 days 9 hours** remaining. Freeze, submission target and buffer derived from this
  measurement, not estimated.
- **L3 (2026-11-26)** — Decisions D1–D11 taken by the human in one batch. D8 (CI on push) was taken
  against the agent's recommendation and is accepted with R5 attached. D10 authorises the irreversible
  removal of `constitution_template.md`.
- **L4 (2026-11-26)** — `PLAN.md` written. Single next step: `DESIGN.md`, which unblocks M1.
- **L5 (2026-11-26)** — Human's instruction, verbatim: *"Vamos a afrontar esto: OW1/OW2 (commit
  standalone de CONSTITUTION.md y borrado de constitution_template.md, ambos sin trackear junto a
  DESIGN.md y PLAN.md), y R1/OW4 (relate-db no está instalado; el diseño lo esquiva con el seam
  store.py sobre el CLI, así que M2 no está bloqueado por eso)."* Closed OW1 in `ceb6305`, which
  touches only `CONSTITUTION.md`; executed OW2, after copying the template outside the repository for
  the session. Closed OW4 and R1 as D12: `relate-db` is neither installed nor a dependency, because
  the builder reaches Relate through one seam over the `relate` CLI. No constitutional amendment was
  needed: §3 still describes an embedded, serverless Relate, and the CLI satisfies it. `DESIGN.md` and
  `PLAN.md` stay untracked pending the human's commit decision.
- **L6 (2026-11-26, 23:30 CET)** — Human's instruction, verbatim (excerpt): *"Tarea de esta sesión:
  cerrar M0 (Foundation and hygiene), y nada más. Rama primero: `chore/m0-foundations` desde `main`."*
  plus the five deliverables and a definition of done. Reading protocol reported **`conflict`**, not
  `read`, for two reasons that the instruction itself did not know about:
  - The brief described a stale repository ("three documentation commits"). `main` was at `ce3a728`
    with six, including `f854fd1` (AGENTS.md already existed) and `5d05fc0` (`.gitignore` already
    reviewed). Two deliverables were therefore already partly delivered, and the `.gitignore`
    needed verification rather than rewriting: it already covers `.venv/`, `__pycache__/`,
    `.pytest_cache/`, the environment files with `!.env.example`, and keeps `*.rl` trackable while
    ignoring `*.tmp.rl`.
  - The brief said "no package manager beyond `pip`"; `CONSTITUTION.md` v1.1 §3 and `AGENTS.md`
    say `uv`. Resolved by the human's live instruction: *"Quiero usar uv. Si hay algo hecho con pip,
    deshazlo y rehazlo con uv."* Nothing had been installed with `pip` — only read-only probes — so
    nothing needed undoing, and `uv` 0.12.14 was already installed at `~/.local/bin/uv` (off `PATH`):
    no tool was installed outside `.venv`, and no constitutional exception was consumed.

  **What landed** on `chore/m0-foundations`, one reviewable unit per commit:
  - `bd9f3b4` — `pyproject.toml` (src layout, `scikit-learn==1.9.1`, dev group `pytest==9.2.0`,
    `[tool.uv] exclude-newer = "1 day"`, `testpaths`), `uv.lock` (14 packages locked), the package
    skeleton (`__init__.py`, `__main__.py` with the three stubs, `store.py`), and one sanity test.
  - `3bbed22` — `.github/workflows/tests.yml`: uv 0.12.14 pinned, `uv sync --frozen`,
    `uv run --frozen pytest -q`, no `relate` binary on the runner by design.
  - `ec77b68` — `AGENTS.md` completed: environment baseline corrected (the CLI seam replaces the
    "embedded library" line that contradicted D12), plus Layout, Commands, Environment, Tests,
    Style and Branches/commits.
  - `0e71b68` — `README.md` skeleton, five headings kept, with the reproducible setup path and an
    "exists today" column.
  - `afc654e` — M0 marked and this log appended.
  - the commit after `afc654e` — the environment contract, authored by the human author and committed
    by the agent; the mechanism, and why it was split that way, is in the paragraph below.

  **DoD 1–5, as observed.** All commands ran in the project venv on this machine (WSL2 Linux 6.6,
  Python 3.12.3, uv 0.12.14, `relate` v1.3.0):
  1. `python -c "import autopsy"` → `autopsy 0.0.0`, exit 0. The CLI integration answers, **with a
     correction to the item as written**: `relate clone` takes `SOURCE DEST` and copies an *existing*
     database, so the recorded form cannot pass — on an empty temporary directory it exits 1 with
     `storage error: read-only open requires an existing database`. The sequence that works, and its
     output: `relate -d $T/src --safe -c "CREATE (:Session {session_id:'m0-probe'})"` (exit 0) →
     `relate clone $T/src $T/autopsy.rl` (exit 0) → `relate info -d $T/autopsy.rl --json` (exit 0,
     `{"layout":"bundle",…,"node_count":1,"rel_count":0,…}`). `import relate` fails with
     `ModuleNotFoundError`, as intended (D12). As a by-product the seam answered end to end:
     `info()` returned that payload and `query()` returned `[{'id': 'm0-probe'}]`.
  2. `python -m pytest` → `1 passed`, exit 0. The test needs no `relate` binary.
  3. `git log --oneline -1 -- CONSTITUTION.md` → `ce3a728 docs(constitution): authorize uv as the
     Python dependency manager (v1.1)`, which changes only `CONSTITUTION.md` (1 file, +3/−1); the
     original ratification `ceb6305` likewise touches only `CONSTITUTION.md` (1 file, +137).
  4. `git status --short` clean after this commit; nothing pushed, no PR.
  5. The `.venv` command (`uv sync`), the test command, the CLI resolution (`~/.local/bin/relate`, the
     `$AUTOPSY_RELATE_BIN` override and PATH fallback) and the `clone`/`info` forms are reproducible
     from `README.md` + `AGENTS.md` alone; they are the commands that actually ran.

  **One deliverable needed the human's hand.** `.env.example` is in the tree, and how it got there is
  worth recording, because the constraint is the harness and not this project: the agent harness denies
  any tool call whose path matches `/(^|\/)\.env(?:$|[./_-])/` — a fixed list in
  `node_modules/gentle-pi/lib/sensitive-paths.ts`, with no allowlist and no configuration knob — and it
  refuses on the name, not on the content: the file holds placeholders and no value. Globbing the path
  past the guard, or patching the installed list, was refused as a guard bypass. So the agent wrote the
  content to `.atl/env-example.txt` (git-ignored), the human copied it into place and staged it, and the
  agent committed it; the staged blob is the one the agent prepared (`9f687cf8…`), so nothing drifted in
  unseen. The contract now agrees with `CONSTITUTION.md` §VI and §6 and with the resolution order the
  seam actually implements. M5 still owes the README half (OW11).

  **Left unverified, deliberately.** The CI run (the workflow is committed, but a green run needs a
  push, and a red one is not debugged on spec — §3.1 item 3); everything M1 and later; the `.venv` is a
  Linux environment inside a Windows-hosted repository and is git-ignored, so a clean clone recreates
  it with `uv sync` rather than inheriting it.

  **Operational note for the next worker.** From WSL, piping `git.exe` output into a Unix tool
  (`| tail`, `| head`) truncates it and can drop the rest of a chained command; `git.exe` writing
  directly to the captured stdout behaves the same way. Redirect to a file and read it, or run one
  `git.exe` invocation per call. This cost two silent non-commits before it was noticed.
