---
constitution: v1
project: Agent Autopsy
amended: 2026-11-26
---

# Agent Autopsy Constitution

This document governs the Agent Autopsy project. It records principles and technical constraints approved by a human. It is **not** proof that the code satisfies them: a rule written here has been ratified, not implemented. It is the rule, not the certificate.

Nothing in this document grants authority to any tool, agent, model or harness — including the author acting as an agent. Each tool keeps its own consent model and its own rules, and they are respected as they are.

## 1. Purpose and Scope

Agent Autopsy is a forensics tool for agent decisions. A small, instrumented agent — it searches, reads, decides, acts — records every step as nodes and edges in an embedded [Relate by Neo4j](https://relatedb.ai/docs/get-started/install) graph. The deliverable is that store, committed to the repository, readable as a navigable forensic report: what the agent had in front of it, what it decided, what it did, and which policy — if any — supported the decision.

What the project is not: a general observability platform, a multi-agent framework, a prompt-injection detector, a product with real users, nor an "intelligent" agent. The agent is deliberately simple and its reasoning is deliberately shallow. The value lives in the graph, not in the model.

This is a hackathon entry with a hard closing date — 2026-12-11, 18:00 PST. There are no real users, no production commitments and no obligation to reach production readiness. Demo simplifications are valid **provided they are declared**: what was simplified, what was omitted, and what the demonstration cannot establish. A simplification is invalid when it hides a gap behind a plausible-looking result.

Explicitly out of scope: real personal data, general-purpose tracing for third-party agents, autonomous decision quality, and any claim that the recorded agent is safe, correct or representative.

## 2. Core Principles

### I. The Graph Is the Deliverable

If a claim about the demo cannot be answered by a query against the committed store, it is not part of the submission. Prose, slides and summaries explain the graph; they never substitute for it.

> **Why:** the artefact the judges inspect is a `.rl` store, and a store they can query is worth more than any narration of what it contains.

### II. Mechanical Provenance, Never Inferred Intent

An `INFLUENCED` edge records mechanics only: the chunk was in the prompt context, or the model cited its marker. It never records a guess about *why* the model leaned on it. Provenance is observed or it is absent.

> **Why:** an inferred edge is a fabricated fact, and a forensic report that fabricates one fact loses authority over all the others.

### III. One Store, Shared Identity

All demo sessions write to the same store. Documents, policies and entities are shared nodes, not per-session copies. A design that isolates sessions in separate stores or separate subtrees is rejected even when it is easier to build.

> **Why:** cross-session contamination is precisely the question a span tree cannot answer, and it is the reason this project needs a graph database.

### IV. Replay Without Secrets or Network

The demonstration, its three queries and every check run from committed traces and the committed store: no API key, no network, no live model. The live path is an optional producer of traces, never a prerequisite for inspecting them.

> **Why:** reproducibility is scored and judged by a stranger on a clean clone; an artefact that only runs with the author's credentials is not reproducible.

### V. Retry the Plumbing, Fail Fast on Logic

Transient failures — network, rate limits, provider timeouts — may be retried with backoff, and **each attempt is a visible node**: the failed call, its error, and the retry. Logic failures (invalid tool, malformed step, impossible state) are recorded and abort rather than being retried into agreement. Partial results are never filled in to look complete.

> **Why:** the record must say what actually happened; a silent retry or a silent degradation turns the forensic report into a tidy fiction.

### VI. No Secrets, No Personal Data

No credential, API key, token or personal datum appears in code, logs, evidence, committed traces, the `.rl` store or memory. Credentials are read from the environment, and the repository commits only `.env.example`. Every live run carries a hard cap on steps and tokens.

> **Why:** a leaked secret cannot be un-leaked and this repository stays public until judging; an uncapped loop spends real money on someone else's card.

### VII. Verified, or Declared Unverified

A claim carries a check that could fail. Green tests, agreement between agents and tidy completion summaries are not human acceptance, and evidence produced for a different candidate or a different environment does not certify this one.

> **Why:** a test proves what someone thought to test; the rest of the claim stays a claim until it is checked or explicitly marked as unverified.

## 3. Technical Constraints (Observed, Not Mandated)

The following describes what is available today. It is observed, not a mandate to add infrastructure or to preserve every choice forever.

- **Runtime:** Node 22 and Python 3.12 are installed. No `cargo`, no `go`. Exact versions and dependencies belong to the project's dependency manifests, not to this document.
- **Relate:** used as an embedded library, in a project-local virtual environment, with no server. The `relate` CLI is already installed by the human (`~/.local/bin/relate`, not on `PATH` by default) and no other installer, package manager or tool may be added without explicit authorization.
- **Recorder and query tooling:** Python, because that is the language in which the store is written today. Node is reserved for the browser viewer.
- **Python dependencies: `uv`.** Authorized by the human author as the dependency manager for the project-local virtual environment. `uv.lock` is committed, versions are exact, and a 24-hour cooldown (`[tool.uv] exclude-newer`) mirrors the Node-side `minimumReleaseAge`. It replaces `pip`; it does not replace the `relate` CLI and adds no server. Every other installer, package manager or tool still needs explicit authorization.
- **Retrieval:** lexical scoring plus vectors computed locally without network calls, indexed with Relate's vector search. The hybrid shape is a constraint; scoring formulas and thresholds belong to the specifications.
- **Agent loop:** an owned loop with a single seam — `next_step(messages, tools)` — and two implementations, live and replay. No provider SDK owns the loop.
- **Traces:** one sanitized JSON document per session, committed, versioned by an explicit `trace_version` field. Provider selection is an environment decision, not a constitutional one.

Relate's store modes, Cypher support, transaction behaviour and API surface are documented by the project upstream; this document links to them instead of restating them.

Conventions that change often — exact messages, node and edge schemas, file layouts, scoring thresholds, judge criteria — belong to the specifications and the plan, not here. When in doubt whether something is a foundation or a detail: it is a detail.

## 4. Development Workflow and Acceptance

### Precedence

When instructions disagree, the first applicable item wins:

1. Platform safety and the human's explicit instruction of the moment.
2. The mandatory rules of this constitution.
3. The rest of the project's instructions — `AGENTS.md`, `CLAUDE.md`, `PLAN.md`, `DESIGN.md`, skills — which say how work is done here and change often.
4. Recommendations, which override nothing.

### Reading protocol

Before planning, the agent reads this document and reports one of three states:

- `read` — rules loaded, proceeding.
- `not_available` — missing or unreadable: do not guess, show the gap.
- `conflict` — the request collides with a rule: stop and name the rule.

A conflict is resolved by changing the work or by amending this constitution. It is never resolved by doing it anyway "because it made sense". No agent reinterprets or bypasses a rule in silence.

### Delegation and acceptance

Execution is delegated; product judgement and acceptance are not. The human retains the final decision. Local adjustments needed to meet the agreed scope are permitted. Independent improvements, dependency changes outside that scope and architectural changes are proposed before they are implemented.

A plan is not permission to publish. Commit, push, pull request, merge and release are the human's decisions, and a review outcome never authorizes delivery.

### Evidence

Acceptance rests on evidence proportional to the claim and the risk: observed behaviour, failing-then-passing checks, and a store that can be queried. Record what was checked, on which candidate and environment, and what remains unverified. A test suite is required for the graph builder, the demo queries, the store's structural invariants and regeneration of the store from committed traces; the live path and the viewer are exercised manually and their limits declared.

### Closure

Two outcomes are distinguished and never confused:

- **Implemented and verified** — agreed scope met, applicable checks run, and the human accepted the evidence.
- **Closed with gaps** — the work stops for the deadline, with remaining defects or unverified claims recorded as such, never presented as a verified result.

## 5. Governance

This constitution is approved, and only approved, by the project's human author. Agents and tools never ratify it.

Amendments are their own change: a dedicated commit with its own rationale recorded in the corresponding task or issue. An amendment never travels inside the commit or pull request of a feature, and it is never a side effect of another task. An agent that finds a rule inconvenient reports it; it does not edit the rule.

Rules are retired explicitly, never ignored. Every rule carries its reason so a later reader can judge whether it still holds. Remembered decisions are revisable, not eternal.

**Version**: v1.1 | **Ratified**: 2026-11-26 | **Last Amended**: 2026-11-26
**Amendments**: v1.1 — `uv` authorized as the Python dependency manager (§3).

## 6. Where Things Live

- Working conventions, commands, layout and code style: `AGENTS.md`.
- Scope, sequencing, open work and per-principle status — implemented, pending, or not applicable to the demo: `PLAN.md`.
- Graph schema, node and edge semantics, query catalogue, trace format and viewer design: `DESIGN.md` and the specifications.
- Reproduction steps for a judge: `README.md`.
- Secrets contract: `.env.example`.
- Relate itself: <https://relatedb.ai/docs/get-started/install>.
