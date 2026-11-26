---
design: v1
project: Agent Autopsy
amended: 2026-11-26
status: proposed — implements nothing by itself
---

# DESIGN — Agent Autopsy

This document says *what to build*, not *that it is built*. It covers exactly the seven
open points of `PLAN.md` §7 and nothing else: graph schema, node and edge semantics, query
catalogue, trace format, viewer, retrieval scoring, report rendering. Working conventions
live in `AGENTS.md`; scope and sequencing live in `PLAN.md`; the rules live in
`CONSTITUTION.md` and win over anything written here.

Every claim about Relate's dialect in this document was executed against `relate` v1.3.0
and is listed with its command in section 0. Requirements compliance is not this
document's job: it designs, the suite checks.

Precedence (`CONSTITUTION.md` §4): platform safety and the human's live instruction →
constitution → `PLAN.md` / `AGENTS.md` / this document → recommendations.

---

## 0. Verified Relate surface

**Environment, observed:** `relate` v1.3.0 (Apache 2.0 binary), `~/.local/bin/relate`,
**not on `PATH`** (`env -i bash -lc 'command -v relate'` → `NOT_ON_PATH`). Python 3.12.3,
Node v22.23.1, git 2.43.0. `import relate` fails today (`ModuleNotFoundError`); the
distribution is named `relate-db`. All probes ran on throwaway stores under the OS temp
directory; nothing in this section was verified against `store/`.

Legend: **used** = this design depends on it; **avoided** = verified working but
deliberately unused; **absent** = not supported, worked around.

### 0.1 Supported, and what depends on it

| Capability | Verified command (abridged) | Observed result | Design dependency |
| --- | --- | --- | --- |
| Single-file `.rl` store | `relate clone <dir> autopsy.rl` then `relate info -d autopsy.rl --json` | `"layout":"bundle"`, `32768` bytes, `node_count:11` | §1.1 committed store |
| Directory store | `relate -d <dir> -c "..."` | `"layout":"native_dir"` | §1.1 build scratch |
| Create nodes with label + properties | `CREATE (:Document {doc_id:'doc-a', size_bytes:120})` | read back identical | §1.2 |
| Create relationships with properties | `CREATE (a)-[:INFLUENCED {witness:'context', score:0.4}]->(b)` | `properties(r)` → `{score:0.4, witness:"context"}` | §1.3, §2.3 |
| Variable-length path, type union | `MATCH p=(s:Session)-[:READ\|PART_OF\|INFLUENCED*1..3]->(d) RETURN length(p)` | `["Session","Chunk","Decision"]`, `hops:2` | Q1B, I1 |
| Path functions | `[n IN nodes(p) \| labels(n)[0]] AS chain`, `length(p)`, `relationships(p)` | list comprehensions return | Q1B, I1 |
| `shortestPath` / `allShortestPaths` | `MATCH p = allShortestPaths((a)-[*1..5]-(b))` | 2 rows, `hops:2` | avoided (Q1B is anchored, not shortest) |
| `MERGE` node + `ON CREATE/ON MATCH SET` | same `MERGE (d:Document {doc_id:'doc-a'})` twice | `count(Document) = 1`, second run sets `seen:true` | §1.1 idempotent builder |
| `MERGE` relationship | `MATCH (a),(b) MERGE (b)-[:PART_OF]->(a)` twice | `count(PART_OF) = 1`; second run notes *"write statement changed nothing"* | §1.1 |
| `UNIQUE` constraint | `CREATE CONSTRAINT document_hash_unique IF NOT EXISTS FOR (d:Document) REQUIRE d.content_hash IS UNIQUE` | created; `SHOW INDEXES` shows `owningConstraint` | §1.4 |
| Constraint violation | `CREATE (a:Document {doc_id:'dup'}) CREATE (b:Document {doc_id:'dup'})` | `semantic error: ConstraintValidationFailed` · exit **6** · **0 rows persisted** | §1.4, I5 |
| Range index | `CREATE INDEX chunk_doc_id IF NOT EXISTS FOR (c:Chunk) ON (c.doc_id)` | `type:"RANGE"` | §1.4, vector pre-filter |
| Vector index | `CREATE VECTOR INDEX chunk_embedding ... OPTIONS {indexConfig:{\`vector.dimensions\`:128, \`vector.similarity_function\`:'cosine'}}` | `type:"VECTOR"`, `indexProvider:"vector-2026.08"` | §6.3 |
| Vector search | `MATCH (c:Chunk) SEARCH c IN (VECTOR INDEX chunk_embedding FOR [1.0,0.0,...] LIMIT 3) SCORE AS score RETURN ...` | `1.0 / 0.8536 / 0.5`, ordered by score | §6.3 |
| Vector search `WHERE` filter | `... FOR [...] WHERE c.doc_id = 'd1' LIMIT 3` | 2 rows, filtered before ranking | §1.4 `WITH [c.doc_id]` |
| Plain list as a vector | `SET c.emb = [1.0,0.0,0.0]`, then index and search that property | scored `0.9969` | §6.3 storage form |
| Aggregation | `count`, `count(DISTINCT x)`, `collect(DISTINCT x)`, `sum`, `avg`, `CASE` | as specified | Q2, Q3 |
| `WITH ... ORDER BY ... LIMIT` | `WITH d, count(e) AS n, collect(e.effect_id) AS effects ORDER BY n DESC LIMIT 5` | sorted, limited | Q1A, Q2 |
| `EXISTS { }` / `NOT EXISTS { }` | `WHERE NOT EXISTS { MATCH (:Policy)-[:AUTHORIZES]->(d) }` | found exactly the decision without a policy | Q3, I4b |
| `OPTIONAL MATCH` + `IS NULL` | `OPTIONAL MATCH (p:Policy)-[:AUTHORIZES]->(d) WITH d,e,p WHERE p IS NULL` | same row set as `NOT EXISTS` | Q3 |
| Statement-level atomicity | failing statement inside a multi-statement script | `statement 2 of 2 failed; 1 completed and committed; 0 not run` · exit **6** | §1.1 build contract |
| Explicit transaction | `.begin` / `.commit` / `.rollback` dot commands in a piped script | rollback leaves no rows; exit with an open tx warns and rolls back | §1.1 (not used: autocommit suffices) |
| `--safe` policy | `relate --safe -c "CREATE (x {a:1})"` | `SafeModeViolation: ... without a label` · exit **6** | §1.5 write guard |
| Determinism | two independent builds of the same graph, rows compared as parsed JSON | `EQUAL`, identical `node_count`/`rel_count` | §1.1, §6.5 |
| `elementId()` | `RETURN elementId(s)` | `"4:rl-id:n3"` | I1 |
| `--mode json` / `--mode envelope` | `relate -d <db> --mode json -c "..."` | `{"data":[...],"timings":{...},"planCache":"miss"}` / `{"columns":[...],"rows":[...],"truncated":false}` | §7, tests |
| `relate info --json` | `relate info -d <db> --json` | `layout`, `node_count`, `rel_count`, `indexes`, `constraints` | I-checks, §7 provenance |

Fulltext search (`CREATE FULLTEXT INDEX` + `SEARCH ... FULLTEXT INDEX ... SCORE AS`) also
works (BM25 scores observed) and is **avoided**: the lexical half of retrieval is computed in
Python so it is identical on every machine and testable without the store (§6.2).

### 0.2 Absent or constrained

| Not available | Evidence | Consequence |
| --- | --- | --- |
| Variable-length pattern in a write clause | `MERGE (a)-[:X*1..2]->(b)` → `syntax error: CreatingVarLength` · exit 6 | The builder emits one edge per statement with its endpoints re-`MATCH`ed. |
| `MERGE` with a `null` property | `... {marker: null}` → `MergeReadOwnWrites: cannot MERGE with null properties` · exit 1 | Optional properties are omitted from the `MERGE` map and set by a separate statement. |
| Pre-created store directory | `mkdir db && relate -d db ...` → `storage error: ambiguous legacy storage role` | The builder must let Relate create the store path; it never `mkdir`s it. |
| `properties(x)` on an unbound-looking name | naming a relationship variable `inf` → `properties() ... got FLOAT` | `inf`, `infinity`, `nan` are reserved literals (`RETURN inf` → `"Inf"`). No identifier may be one. |
| `vector([...], 3, 'float32')` with a string type | `syntax error: ... third argument must be a coordinate type keyword` | Store embeddings as plain JSON lists (§6.3). |
| `SEARCH` without `LIMIT` | `... FOR [...] )` → `syntax error: parse error: expected LIMIT` · exit 6 | k is always explicit. |
| `id()` as a stable identity | `id(s)` → `3`, `elementId(s)` → `"4:rl-id:n3"`; internal, unstable across rebuilds | Never an identity key; identity is a domain property with a `UNIQUE` constraint. |
| Explicit `BEGIN`/`COMMIT` as Cypher | not accepted; the shell dot commands exist instead | Autocommit per statement is the builder's contract. |
| Quoted strings in `--param` | `--param decision_id='d2'` → matches nothing (quotes become part of the value); `--param decision_id=d2` or `"d2"` works | The builder binds bare words or JSON strings, never shell-quoted Cypher literals. |
| Unlimited row output by default | under a detected agent harness stdout is capped at 100 rows per statement | Every machine read passes `--max-rows 0` and/or an explicit `LIMIT`. |

Two further observed behaviours the builder relies on: a write that changes nothing prints
`note: write statement changed nothing; the graph is unchanged` (harmless, and proof of
idempotence), and `--safe` accepts `MATCH ... MERGE ...` writes while refusing a node without
a label, which is exactly the guard wanted for a generated script.

---

## 1. Graph schema

### 1.1 Store layout and build contract

- **Committed artefact:** `store/autopsy.rl`, a single-file bundle. Chosen because it travels
  as one file (`relate docs: "Choose a .rl file when the store travels: one file to copy,
  attach, or check in"`) and `relate info` reads it without opening it.
- **Build:** `autopsy build` creates a *native directory* store in the OS temp directory, runs
  the DDL and graph scripts against it, then `relate clone <tmp> store/autopsy.rl`. The store
  directory is never pre-created; `clone` refuses an existing destination, so a stale bundle is
  an error, not an overwrite.
- **Autocommit per statement is the build contract.** Each statement is atomic (verified: a
  constraint violation leaves zero rows). The builder therefore emits, in order: all DDL, then
  all nodes, then all edges, then embeddings. A failure stops the build at a known statement
  index and the temp store is discarded; the committed bundle is never left half-written.
- **Idempotence:** every node and edge uses `MERGE`, so a rerun over the same traces is a
  no-op. Two independent builds must produce equal normalized query results (§6.5), not equal
  bytes: the binary layout belongs to Relate.
- **Write guard:** node/edge statements run under `--safe`. Reads (queries, the demo, verification)
  run without it, always with an explicit `LIMIT` or a reducing aggregate.
- **Statement shape rule (non-negotiable):** a variable does not survive the `;`. Every statement
  re-`MATCH`es its endpoints by identity property. A statement whose endpoint cannot be matched
  must fail the build; the naive form `CREATE (c)-[:PART_OF]->(d)` with unbound variables
  silently creates two label-less nodes and exits 0 (observed), which is why I2 exists.

### 1.2 Node labels

Ten labels, no more. Each has exactly one identity property with a `UNIQUE` constraint.

| Label | Identity (UNIQUE) | Cardinality in the demo | Properties |
| --- | --- | --- | --- |
| `Session` | `session_id` | 3 (one per trace, D4) | `session_id`, `title`, `started_at` (ISO-8601 string), `model`, `trace_path`, `trace_version` (int), `step_count` |
| `Task` | `task_id` | 1 per session | `task_id`, `prompt` (sanitized), `created_at` |
| `Document` | `content_hash` | shared across sessions | `doc_id`, `content_hash` (`sha256:<hex>`), `path`, `title`, `size_bytes` |
| `Chunk` | `chunk_id` | shared across sessions | `chunk_id`, `doc_id` (denormalized, indexable), `ordinal`, `text`, `char_start`, `char_end`, `embedding` (list of 128 floats) |
| `Retrieval` | `retrieval_id` | 1 per search event | `retrieval_id`, `query`, `k`, `strategy`, `at_step` |
| `ToolCall` | `call_id` | 1 per attempt | `call_id`, `tool`, `attempt` (int), `status` (`ok`/`error`), `error_kind`, `error_message`, `args_json` (sanitized), `result_summary` |
| `Decision` | `decision_id` | 1..n per task | `decision_id`, `action`, `rationale_summary`, `at_step` |
| `Effect` | `effect_id` | exactly 1 per decision | `effect_id`, `kind`, `amount` (int, may be absent), `currency`, `target_ref`, `irreversible` (bool) |
| `Policy` | `policy_id` | shared across sessions | `policy_id`, `title`, `effect_kind`, `max_amount` (int), `status` (`active`/`retired`) |
| `Entity` | `entity_key` | shared across sessions | `entity_key` (`<kind>:<normalized name>`), `kind`, `name` |

Identity rationale, in one line each:

- `Document.content_hash` — identity is the text the agent read, so the same corpus reached via two
  paths is one node (§III is a property of the graph, not a convention). `doc_id` is
  `content_hash[:12] + '-' + slug` for readability only, and is not a key.
- `Chunk.chunk_id` — derived as `<doc_id>#<ordinal>`, so chunk identity is a pure function of the
  document identity and the chunker (§6.1). Two sessions that saw the same window share one node.
- `Entity.entity_key` — `<kind>:<lowercased collapsed name>`, so an entity is shared rather than
  copied per session.
- Everything else carries the identifier the trace records; the builder never invents one.

`Document` and `Chunk` are materialized **only when a step references them**. A corpus document
that no session ever read stays out of the store: it would be an orphan, and an orphan is a
failing invariant (I3).

### 1.3 Edge types

| Type | Direction | Cardinality | Properties |
| --- | --- | --- | --- |
| `PURSUES` | `Session → Task` | exactly 1 | — |
| `DECIDED` | `Task → Decision` | 1..n | — |
| `PRODUCED` | `Decision → Effect` | exactly 1 | — |
| `AUTHORIZES` | `Policy → Decision` | 0..n | — |
| `STATED_IN` | `Policy → Chunk` | exactly 1 | — |
| `READ` | `Session → Chunk` | 1..n | `ordinal` (first step index that put the chunk in context) |
| `INFLUENCED` | `Chunk → Decision` | 0..n | `witness`, `marker`, `session_id` |
| `PART_OF` | `Chunk → Document` | exactly 1 | — |
| `PERFORMED` | `Task → Retrieval` | 1..n | — |
| `RETURNED` | `Retrieval → Chunk` | 1..k | `rank`, `score`, `lexical`, `vector` |
| `CALLED` | `Task → ToolCall` | 0..n | — |
| `RETRIED_AS` | `ToolCall → ToolCall` | 0..1 | `backoff_ms` |
| `MENTIONS` | `Decision → Entity` | 0..n | `role` |

Direction rule: an edge points **from evidence to the claim it supports** (`Chunk → Decision`,
`Policy → Decision`, `Chunk → Document`) and **from container to contained** (`Session → Task`,
`Task → Decision`). `READ` and `PERFORMED` point forward in time. Because directions are fixed,
every query in §3 can be written with an explicit type set instead of an undirected walk; an
undirected traversal from a `Decision` returns sibling decisions as noise (observed).

### 1.4 Constraints and indexes

The exact DDL block, executed as-is against a fresh store (12/12 statements, exit 0 under
`--safe`):

```cypher
CREATE CONSTRAINT session_id_unique        IF NOT EXISTS FOR (s:Session)   REQUIRE s.session_id   IS UNIQUE
CREATE CONSTRAINT task_id_unique           IF NOT EXISTS FOR (t:Task)      REQUIRE t.task_id      IS UNIQUE
CREATE CONSTRAINT document_hash_unique     IF NOT EXISTS FOR (d:Document)  REQUIRE d.content_hash IS UNIQUE
CREATE CONSTRAINT chunk_id_unique          IF NOT EXISTS FOR (c:Chunk)     REQUIRE c.chunk_id     IS UNIQUE
CREATE CONSTRAINT retrieval_id_unique      IF NOT EXISTS FOR (r:Retrieval) REQUIRE r.retrieval_id IS UNIQUE
CREATE CONSTRAINT toolcall_id_unique       IF NOT EXISTS FOR (t:ToolCall)  REQUIRE t.call_id      IS UNIQUE
CREATE CONSTRAINT decision_id_unique       IF NOT EXISTS FOR (d:Decision)  REQUIRE d.decision_id  IS UNIQUE
CREATE CONSTRAINT effect_id_unique         IF NOT EXISTS FOR (e:Effect)    REQUIRE e.effect_id    IS UNIQUE
CREATE CONSTRAINT policy_id_unique         IF NOT EXISTS FOR (p:Policy)    REQUIRE p.policy_id    IS UNIQUE
CREATE CONSTRAINT entity_key_unique        IF NOT EXISTS FOR (e:Entity)    REQUIRE e.entity_key   IS UNIQUE
CREATE INDEX chunk_doc_id                  IF NOT EXISTS FOR (c:Chunk)     ON (c.doc_id)
CREATE VECTOR INDEX chunk_embedding        IF NOT EXISTS FOR (c:Chunk)     ON (c.embedding)
  WITH [c.doc_id]
  OPTIONS {indexConfig: {`vector.dimensions`: 128, `vector.similarity_function`: 'cosine'}}
```

Notes that matter:

- Uniqueness is **enforced**, and a violation aborts the statement with exit 6 and no partial
  write. This is what makes "two builds agree" and "one node per document" (`§III`) fail loudly
  instead of quietly duplicating.
- A `UNIQUE` constraint owns a same-named `RANGE` index; it cannot be dropped alone. Nothing in
  this project drops an index.
- Uniqueness **exempts** nodes that lack the property, so the constraint alone does not forbid a
  missing identity. I5 checks the count, not the absence.
- `chunk_doc_id` exists because the vector index is declared `WITH [c.doc_id]`; the filter is only
  legal on declared filter properties (verified: `WHERE c.doc_id = 'd1'` filtered the ranking).
- `chunk.embedding` is a plain list of floats, not a `vector()` value: a list is JSON-serializable,
  rebuilds bit-identically from the same corpus, and indexes and searches correctly (verified).

### 1.5 Naming and value rules

- Identifiers: `lower_snake_case` for properties, `PascalCase` for labels, `SCREAMING_SNAKE` for
  edge types. Edge types are a single name; `:A&B` never matches (`one relationship, one type`).
- Forbidden identifiers: `inf`, `infinity`, `nan` (reserved float literals), plus the clause
  keywords (`match`, `merge`, `count`, `case`, `exists`, `search`, `score`, `where`, `return`).
- `null` means "absent". It is never written into a `MERGE` property map, and `SET x.p = null`
  removes the property. Queries therefore use `coalesce()` rather than testing for a stored null.
- Timestamps are ISO-8601 **strings** with an explicit `Z`, not `datetime()` values: the demo
  compares and sorts them lexically, and a temporal type would add a conversion surface for no
  gain.
- `amount` is an integer in minor units of `currency`; it may be absent, and `coalesce(e.amount, 0)`
  is used wherever an amount participates in a comparison.

---

## 2. Node and edge semantics

### 2.1 Nodes

- **Session** — one instrumented run of the agent, one committed trace. It owns a task, the chunks
  it ever put in front of the model, its retrievals, its tool calls and its decisions. Three
  sessions exist, one per mandatory query (D4).
- **Task** — the goal statement the session pursues, taken verbatim (sanitized) from the trace. It
  is the only place a natural-language intent is stored, and it is never used to infer an edge.
- **Document** — a corpus artefact with an immutable content hash. It is the unit of contamination:
  if the text is wrong, every chunk of it is wrong, in every session that read it.
- **Chunk** — a fixed-size window of a document, the unit that is retrieved, cited and influenced.
  It is the granularity of provenance because it is the granularity the model actually saw.
- **Retrieval** — one instrumented search: the query string, `k`, the strategy identifier, and the
  ranked chunks it returned with their component scores. It is a node rather than a property so
  that "what the retriever offered" is separable from "what the model used".
- **ToolCall** — one *attempt* to call a tool. Attempts are distinct nodes: a retry does not
  overwrite the failure that caused it (§V). `status`, `error_kind` and `error_message` live on the
  failed attempt.
- **Decision** — the moment the agent chose an action. It carries the action string and a short
  rationale summary quoted from the trace, and it is the anchor of every provenance question.
- **Effect** — what the action changed in the world, as recorded by the trace: kind, amount,
  currency, target, and whether it is irreversible. It exists so that "the policy covered the
  decision" can be checked against a concrete effect rather than against prose.
- **Policy** — a rule stated by a document, with an `effect_kind`, a ceiling and a status. It is a
  shared node (§III): one policy, however many sessions lean on it. `STATED_IN` points at the chunk
  that states it, so a poisoned policy is traceable to the poisoned text.
- **Entity** — a thing a decision names or acts upon (customer, order, account), keyed so that two
  sessions touching the same thing share one node. It carries no personal data by construction
  (§VI); the demo uses invented names and the sanitizer rejects anything shaped like a real one.

### 2.2 Edges

- **PURSUES** — the session adopts the task. Always exactly one; a session without a task is a
  malformed trace.
- **DECIDED** — the task produced this decision. The multiplicity is real: one task can decide
  several times, and that is what makes Q3 a set rather than a row.
- **PRODUCED** — the decision had exactly this effect. Exactly one, enforced by I6, because policy
  coverage is meaningless if a decision has zero or two effects.
- **AUTHORIZES** — this policy was offered as the support of this decision. Absent means no policy
  was cited; present and non-covering is a separate verdict (§2.4).
- **STATED_IN** — the policy is stated by this chunk. Exactly one, so a policy always has a textual
  origin, which is what makes a contaminated policy explainable.
- **READ** — this chunk appeared in the session's context at step `ordinal`. Mechanical: derived
  from the trace's retrieval results and recorded context lists, never from prose.
- **INFLUENCED** — see §2.3.
- **PART_OF** — the chunk is a window of the document. Exactly one.
- **PERFORMED** — the task ran this retrieval.
- **RETURNED** — the retrieval returned this chunk at `rank` with `score`, and its two components
  `lexical` and `vector`. The components are stored, not recomputed, so the report can show why a
  chunk ranked where it did.
- **CALLED** — the task made this tool attempt.
- **RETRIED_AS** — this failed attempt was followed by that attempt after `backoff_ms`. Exactly one
  per retried failure; the pair is the visible shape of §V.
- **MENTIONS** — the decision named this entity in a `role`.

### 2.3 The `INFLUENCED` rule

An `INFLUENCED` edge records mechanics only (§II). It exists if and only if the trace contains
**one of exactly two observations**, and the builder writes the observation into `witness`:

| `witness` | Observation in the trace | Checkable by the builder |
| --- | --- | --- |
| `context` | the chunk's `chunk_id` appears in the `context_chunk_ids` array of the `model_call` step whose output is that decision | set membership in a recorded array; no interpretation |
| `cited` | the model's output for that step contains the literal marker `[[<chunk_id>]]`, and the trace records it in `cited_markers` | substring presence, recorded by the producer |

Nothing else creates the edge. In particular:

- A chunk may be `READ` and never `INFLUENCED`. Retrieval is an offer; influence is a fact about a
  prompt. The report relies on this asymmetry: it is what makes Q1 an answer.
- `witness` is a **closed enum**. The builder rejects a trace that declares `influenced` with any
  other value, with a missing `witness`, or with a `witness` that references a step that is not a
  `model_call`.
- The edge carries `session_id`, the session whose trace recorded the observation. Without it the
  edge is ambiguous whenever two sessions read the same chunk (observed: an un-anchored path query
  returned one row per reading session for the same decision). I4c asserts
  `witness.session_id` equals the decision's own session.
- No edge is ever created from similarity, from co-occurrence, from a heuristic, or from a model's
  own claim about what it used. If the observation is not in the trace, the edge is absent and the
  report says so.
- Rejection is a build failure, not a warning: a trace that would produce an unjustifiable edge
  cannot be materialized at all.

### 2.4 Policy coverage verdicts

Coverage is computed by one `CASE` over the decision's effect and its authorizing policies, in this
fixed order of precedence. The first matching branch wins.

| Verdict | Condition | Category |
| --- | --- | --- |
| `UNSUPPORTED:no_policy` | no `Policy` `AUTHORIZES` the decision | unsupported |
| `UNSUPPORTED:policy_inactive` | the cited policy has `status <> 'active'` | unsupported |
| `UNSUPPORTED:kind_mismatch` | `p.effect_kind <> e.kind` | unsupported |
| `VIOLATES:amount_exceeds` | `coalesce(e.amount, 0) > p.max_amount` | violation |
| `covered` | none of the above | — |

`UNSUPPORTED` means *nothing authorized this*; `VIOLATES` means *something authorized it and the
effect exceeded what it allowed*. They are different findings and the report never merges them.
`VIOLATES` outranks a status problem on purpose: an inactive policy that is nonetheless exceeded is
reported as an excess, because that is the sharper fact, and the precedence is fixed here so the
query is deterministic. Q3 returns every decision whose verdict is not `covered`, with the reason
attached, and its test fixes the exact expected set (no false positives, per M3.3).

---

## 3. Query catalogue

All queries are written in the verified subset (section 0) and were executed against a probe store
built with the schema of §1. Parameters are bound, never interpolated; the builder/demo passes them
as bare words or JSON strings (`--param decision_id=d2`), never as shell-quoted Cypher literals.
Reads use `--max-rows 0`.

### Q1A — evidence behind one decision

```cypher
MATCH (d:Decision {decision_id: $decision_id})-[:PRODUCED]->(e:Effect)
MATCH (c:Chunk)-[w:INFLUENCED]->(d)
MATCH (c)-[:PART_OF]->(doc:Document)
OPTIONAL MATCH (s:Session)-[:READ]->(c)
RETURN d.decision_id AS decision_id, d.action AS action,
       e.effect_id AS effect_id, e.kind AS effect_kind, e.amount AS effect_amount,
       w.witness AS witness, w.marker AS marker, w.session_id AS witness_session,
       c.chunk_id AS chunk_id, c.ordinal AS chunk_ordinal,
       doc.doc_id AS document_id, doc.path AS document_path,
       collect(DISTINCT s.session_id) AS read_in_sessions
ORDER BY document_path, chunk_ordinal
```

Expected shape — one row per influencing chunk, ordered by document then chunk; the effect columns
repeat. Observed for `decision_id=d2`:

```json
[{"decision_id":"d2","action":"refund","effect_id":"e2","effect_kind":"refund",
  "effect_amount":4200,"witness":"context","marker":null,"witness_session":"s2",
  "chunk_id":"doc-poison#0","chunk_ordinal":0,"document_id":"doc-poison",
  "document_path":"corpus/refunds.md","read_in_sessions":["s2","s1"]}]
```

`read_in_sessions` deliberately lists every session that read the chunk, including sessions other
than the influenced one: that column is the visible trace of §III, and Q2 is its aggregate.

### Q1B — the causal chain, as a path

```cypher
MATCH (t:Task)-[:DECIDED]->(d:Decision {decision_id: $decision_id})
MATCH (s:Session)-[:PURSUES]->(t)
MATCH p = (s)-[:READ|PART_OF|INFLUENCED*1..3]->(d)
RETURN DISTINCT s.session_id AS session_id,
       [n IN nodes(p) | labels(n)[0]] AS chain,
       [r IN relationships(p) | type(r)] AS edges,
       length(p) AS hops
ORDER BY hops
```

Expected shape — the chain is `Session → (Chunk) → (Document…) → Decision`, scoped to the decision's
own session so a chunk read by a second session cannot produce a phantom path. Observed for
`decision_id=d1`:

```json
[{"session_id":"s1","chain":["Session","Chunk","Decision"],
  "edges":["READ","INFLUENCED"],"hops":2}]
```

The hop bound is `1..3` on purpose: `Session -READ-> Chunk -INFLUENCED-> Decision` is 2, and the
`Document` detour (`Chunk -PART_OF-> Document`) needs a third. The bound is explicit, so it cannot
trip the `TraversalDepthExceeded` safety limit, and the pattern is anchored rather than undirected,
so sibling decisions are excluded.

### Q2 — contamination fan-out

```cypher
MATCH (doc:Document {doc_id: $document_id})<-[:PART_OF]-(c:Chunk)
MATCH (s:Session)-[:READ]->(c)
OPTIONAL MATCH (c)-[:INFLUENCED]->(d:Decision)
RETURN doc.doc_id AS document_id, doc.path AS document_path,
       collect(DISTINCT s.session_id) AS sessions, count(DISTINCT s) AS session_count,
       count(DISTINCT c) AS chunk_count, count(DISTINCT d) AS influenced_decisions
ORDER BY session_count DESC, document_id
```

Expected shape — one row per document, with the sessions that read any of its chunks. Observed for
`document_id=doc-poison`:

```json
[{"document_id":"doc-poison","document_path":"corpus/refunds.md",
  "sessions":["s2","s1"],"session_count":2,"chunk_count":1,"influenced_decisions":2}]
```

The `collect(DISTINCT ...)` order is whatever the engine produces (`["s2","s1"]`, not sorted), so the
report layer sorts list members before rendering. The test asserts the *set* and `session_count >= 2`,
which is the cross-session reach a span tree cannot show (§III).

### Q3 — decisions with no valid policy

```cypher
MATCH (d:Decision)-[:PRODUCED]->(e:Effect)
OPTIONAL MATCH (p:Policy)-[:AUTHORIZES]->(d)
WITH d, e, p,
     CASE WHEN p IS NULL                          THEN 'UNSUPPORTED:no_policy'
          WHEN p.status <> 'active'               THEN 'UNSUPPORTED:policy_inactive'
          WHEN p.effect_kind <> e.kind            THEN 'UNSUPPORTED:kind_mismatch'
          WHEN coalesce(e.amount, 0) > p.max_amount THEN 'VIOLATES:amount_exceeds'
          ELSE 'covered' END AS verdict
WHERE verdict <> 'covered'
RETURN d.decision_id AS decision_id, d.action AS action,
       e.kind AS effect_kind, e.amount AS effect_amount,
       p.policy_id AS policy_id, verdict
ORDER BY verdict, decision_id
```

Expected shape — one row per non-covered decision, with the reason. Observed against the probe
store (4 decisions, 2 returned):

```json
[{"decision_id":"d4","action":"delete_account","effect_kind":"delete_account",
  "effect_amount":null,"policy_id":null,"verdict":"UNSUPPORTED:no_policy"},
 {"decision_id":"d2","action":"refund","effect_kind":"refund","effect_amount":4200,
  "policy_id":"p-strict","verdict":"VIOLATES:amount_exceeds"}]
```

The two covered decisions (`d1` within its ceiling, `d3` within its ceiling) are absent, which is
the whole point of the assertion: the test pins the exact set, so a false positive fails.

### Auxiliary queries (tests)

Structural invariants. Each returns **zero rows** on a correct store, which is what makes them
assertions rather than reports. Every one of them was run green against the probe store; I4b was
run red first (the probe lacked `READ` edges) and then green, which is the failing-then-passing
evidence M2.2 asks for.

```cypher
-- I1  every node is reachable from some Session
MATCH (s:Session) MATCH (s)-[*1..8]-(n) WITH DISTINCT n
WITH collect(elementId(n)) AS reachable
MATCH (m) WHERE NOT elementId(m) IN reachable
RETURN labels(m)[0] AS label, properties(m) AS props

-- I2  no label-less node (the unbound-variable trap of §1.1)
MATCH (n) WHERE size(labels(n)) = 0 RETURN count(n) AS label_less

-- I3  no orphan node
MATCH (n) WHERE NOT (n)--() RETURN count(n) AS orphans

-- I4a every INFLUENCED witness is in the closed enum
MATCH (c:Chunk)-[w:INFLUENCED]->(d:Decision)
WHERE NOT w.witness IN ['context','cited'] RETURN count(*) AS bad_witness

-- I4b a 'context' witness implies the witnessing session actually read that chunk
MATCH (c:Chunk)-[w:INFLUENCED]->(d:Decision)
MATCH (t:Task)-[:DECIDED]->(d) MATCH (s:Session {session_id: w.session_id})-[:PURSUES]->(t)
WHERE NOT EXISTS { MATCH (s)-[:READ]->(c) }
RETURN d.decision_id AS decision, c.chunk_id AS chunk, w.session_id AS session

-- I4c the witness session is the decision's own session
MATCH (c:Chunk)-[w:INFLUENCED]->(d:Decision)
MATCH (t:Task)-[:DECIDED]->(d) MATCH (s:Session)-[:PURSUES]->(t)
WHERE s.session_id <> w.session_id
RETURN d.decision_id AS decision, w.session_id AS witness_session, s.session_id AS decision_session

-- I5  one node per identity key, per shared label
MATCH (d:Document) WITH d.content_hash AS k, count(*) AS n WHERE n > 1 RETURN k, n
MATCH (p:Policy)   WITH p.policy_id  AS k, count(*) AS n WHERE n > 1 RETURN k, n
MATCH (e:Entity)   WITH e.entity_key AS k, count(*) AS n WHERE n > 1 RETURN k, n

-- I6  every decision produced exactly one effect
MATCH (d:Decision) OPTIONAL MATCH (d)-[:PRODUCED]->(e:Effect)
WITH d, count(e) AS n WHERE n <> 1 RETURN d.decision_id AS id, n
```

Two further auxiliary queries belong to the demo, not to the invariants:

```cypher
-- D1  the retry is visible, in order, with its error (principle V)
MATCH (t:Task)-[:CALLED]->(c:ToolCall)
OPTIONAL MATCH (c)-[:RETRIED_AS]->(next:ToolCall)
RETURN t.task_id AS task, c.call_id AS call_id, c.attempt AS attempt,
       c.status AS status, c.error_kind AS error_kind,
       next.call_id AS retried_as, c.backoff_ms AS backoff_ms
ORDER BY task, attempt

-- D2  a shared node is one node, whatever the session count (§III)
MATCH (doc:Document) RETURN count(doc) AS documents, collect(DISTINCT doc.content_hash) AS hashes
```

The suite's four blocks (§4 of the constitution) map onto these: the builder block asserts the
rejection rules of §2.3; the demo-query block asserts the expected sets of Q1A/Q1B/Q2/Q3; the
structural block asserts I1–I6; the regeneration block rebuilds into a temp store and compares
normalized Q1A/Q1B/Q2/Q3 results with the committed bundle.

---

## 4. Trace format

### 4.1 Layout

One file per session: `traces/s1.json`, `traces/s2.json`, `traces/s3.json`. The corpus itself lives
in `corpus/` as plain Markdown; the trace references it by `chunk_id` and asserts its
`text_sha256`, so the text has exactly one home and the trace cannot drift from it.

```json
{
  "trace_version": 1,
  "sanitizer": {"version": 1, "sanitized": true},
  "session": {
    "session_id": "s1",
    "title": "Refund approvals",
    "started_at": "2026-11-26T10:00:00Z",
    "model": "replay:fixture-1",
    "task": {"task_id": "t1", "prompt": "Should we honour the refund request?", "created_at": "..."}
  },
  "steps": [
    {"step_id": "s1-01", "step_type": "retrieve", "at": "...",
     "retrieval_id": "r1", "query": "refund approval limit", "k": 5,
     "strategy": "hybrid:0.7lex+0.3vec",
     "returns": [{"chunk_id": "doc-poison#0", "doc_id": "doc-poison",
                  "text_sha256": "sha256:...", "rank": 1,
                  "score": 0.82, "lexical": 0.79, "vector": 0.89}]},

    {"step_id": "s1-02", "step_type": "tool_call", "at": "...",
     "call_id": "s1-tc1", "tool": "read_document", "attempt": 1,
     "args": {"doc_id": "doc-poison"}, "status": "error",
     "error_kind": "timeout", "error_message": "provider timeout after 30s"},

    {"step_id": "s1-03", "step_type": "error", "at": "...",
     "of": "s1-02", "error_kind": "timeout",
     "error_message": "provider timeout after 30s"},

    {"step_id": "s1-04", "step_type": "retry", "at": "...",
     "retry_of": "s1-tc1", "call_id": "s1-tc2", "attempt": 2, "backoff_ms": 2000},

    {"step_id": "s1-05", "step_type": "tool_call", "at": "...",
     "call_id": "s1-tc2", "tool": "read_document", "attempt": 2,
     "args": {"doc_id": "doc-poison"}, "status": "ok",
     "result_summary": "1800 bytes"},

    {"step_id": "s1-06", "step_type": "model_call", "at": "...", "turn": 3,
     "context_chunk_ids": ["doc-poison#0"],
     "cited_markers": [],
     "output_ref": "s1-06.out"},

    {"step_id": "s1-07", "step_type": "decision", "at": "...",
     "decision_id": "d1", "action": "refund",
     "rationale_summary": "runbook pre-approves up to 5000"},

    {"step_id": "s1-08", "step_type": "effect", "at": "...",
     "decision_id": "d1", "effect_id": "e1", "kind": "refund",
     "amount": 4800, "currency": "EUR", "target_ref": "customer:acme",
     "irreversible": false}
  ]
}
```

`output_ref` points at a sidecar file under `traces/<session>/`; long model output is never inlined.
The sidecar is subject to the same sanitizer.

### 4.2 `trace_version` contract

- `trace_version` is an integer, required, and the first field the loader reads. `1` is the only
  accepted value; anything else fails with `unsupported trace_version: <n>` and the build stops.
- Required at the top level: `trace_version`, `sanitizer`, `session`, `steps`. Required in
  `sanitizer`: `version`, `sanitized`. Required in `session`: `session_id`, `title`, `started_at`,
  `model`, `task`. Required in `task`: `task_id`, `prompt`.
- Required per step: `step_id`, `step_type`, `at`. `step_id` is unique within the file and matches
  `^s[0-9]+-[0-9]{2,}$`.
- **Unknown fields: strict reject.** Any key not named by the contract, at any level, is a
  validation error naming the path (`steps[2].foo: unknown field`). The single exception is a key
  whose name starts with `x_`, which is ignored and preserved verbatim, so a producer can add a
  diagnostic without a version bump.
- Adding, removing or retyping a field is a `trace_version` bump and its own commit (R10). A
  version bump is never a side effect of curating a trace.
- The loader returns the list of unknown-field paths in its error, because a bare "invalid trace"
  costs more debugging time than it saves.

### 4.3 Step taxonomy

| `step_type` | Required fields | Becomes in the store |
| --- | --- | --- |
| `retrieve` | `retrieval_id`, `query`, `k`, `strategy`, `returns[]` | `Retrieval` node, `PERFORMED` from the task, `RETURNED` per chunk, and `READ` for every returned chunk |
| `tool_call` | `call_id`, `tool`, `attempt`, `status`; `args` when `status=ok`; `error_kind` + `error_message` when `status=error` | `ToolCall` node, `CALLED` from the task |
| `tool_result` | `of` (a `call_id`), `result_summary` | No node: folded into that `ToolCall`'s `result_summary` |
| `model_call` | `turn`, `context_chunk_ids[]`, `cited_markers[]`, `output_ref` | No node: it is the **observable** that produces `READ` and `INFLUENCED` edges |
| `decision` | `decision_id`, `action`, `rationale_summary` | `Decision` node, `DECIDED` from the task |
| `effect` | `decision_id`, `effect_id`, `kind`, `irreversible`; `amount`/`currency` when the kind has one | `Effect` node, `PRODUCED` from the decision |
| `error` | `of`, `error_kind`, `error_message` | No node: folded into the owning `ToolCall`'s error fields |
| `retry` | `retry_of` (a `call_id`), `call_id`, `attempt`, `backoff_ms` | No node of its own: the retried `ToolCall` plus the `RETRIED_AS` edge |

The triad `tool_call` / `error` / `retry` is the evidence for §V: the failed attempt is its own node
with its own error, and the retry is a second node joined by `RETRIED_AS`. `error` and `retry` are
steps without their own label because the sanctioned label set has ten nodes and an `Error` label is
not one of them; the observability §V demands is preserved at node granularity — one node per
attempt, the error attached to the attempt that failed, the retry as a distinct node and an explicit
edge. I4-style checks assert that every `ToolCall` with `status='error'` has a non-empty
`error_kind` and is the source of exactly one `RETRIED_AS`.

A step type outside this table is a validation error, not an ignored step: a trace cannot smuggle
an unmodelled step into the store.

### 4.4 Retry and error representation

- The retry is **its own step** in the trace and **its own node** in the store. It never mutates the
  failed attempt.
- `attempt` starts at 1 and increments per retry of the same `(tool, args)` pair.
- The failed attempt keeps `status:"error"`, `error_kind` (closed set: `timeout`, `rate_limit`,
  `network`, `provider_error`) and `error_message` (sanitized, truncated to 200 characters, and the
  untruncated text stays in the sidecar).
- `backoff_ms` is recorded on the `RETRIED_AS` edge, so the delay is visible in the graph.
- **Logic failures are not retried** (§V). A `step_type` violation, an unknown tool, or an
  impossible state aborts the session; the trace records the abort and the build records it as the
  session's terminal step. The demo exercises only the retry half, and `README.md` must say so.

### 4.5 Sanitization contract (field level)

Applied to every string value in the trace and its sidecars **before the file is written**. The
sanitizer is a pure function of the input string and a key path, and it is idempotent.

| Class | Rule | Action |
| --- | --- | --- |
| Secret-shaped key | key matches `(?i)(api[_-]?key\|token\|secret\|password\|passwd\|bearer\|credential\|authorization)` | value replaced by `[REDACTED]`; the key is kept |
| Secret-shaped value | value matches `sk-[A-Za-z0-9]{16,}`, `ghp_[A-Za-z0-9]{20,}`, `AKIA[0-9A-Z]{16}`, `xox[baprs]-[A-Za-z0-9-]{10,}` | **build fails**; the trace is not written |
| Personal data | value matches an email, a 13–19 digit card-shaped run, or a `+`-prefixed phone-shaped run | **build fails**; the trace is not written |
| Everything else | — | unchanged |

Why redact one class and reject the other: a redacted API key is still a faithful record of *where a
key was used*, so redaction preserves forensics. A personal datum has no forensic value here and
cannot be un-leaked on a public repository, so the only safe outcome is to refuse it. Refusal is per
file: the build reports the offending path and writes nothing.

The contract is enforced twice: the sanitizer test plants a token and an email in a fixture and must
fail first, pass after the scrubber, and reject the email; and `grep -riE
'(api[_-]?key|token|password|@[a-z0-9.-]+\.)' traces/` is run and recorded before each trace commit
(M1.3). `.env.example` is the only secrets artefact in the repository (§VI).

---

## 5. Viewer

**Status: out of scope for this cycle.** The committed store plus the CLI and the Markdown report
*are* the interface (§I, D3). The cut order in §3.1 of the plan puts the viewer first, and a viewer
that half-works is worse than no viewer, because it invites the claim that the graph is inspectable
in a browser when it is not.

What a judge does instead, with no extra artefact:

```
python -m autopsy demo                     # the three queries, as Markdown
relate -d store/autopsy.rl --read-only --mode json -c "<any query in §3>"
```

**Fallback, already designed.** The report of §7 is the fallback: it prints the three answers, the
exact Cypher that produced each, and the provenance of the store. It needs no server, no build step
and no network.

**Minimal stretch design**, to be attempted only if M6 still has two full days after absorbing
slippage, with its own definition of done written before it starts:

- One static directory `viewer/`, no bundler, no framework, no dependency beyond the Relate
  WebAssembly package. Node 22 is used only as the local static server.
- The page opens the committed `store/autopsy.rl` **read-only in the browser** through the WASM
  build and runs the same three queries, embedded verbatim from `queries/` so the viewer cannot
  drift from the catalogue.
- Three presets, each rendering a table and, for Q1B and Q2, a force-directed subgraph laid out
  from the query's own result rows. Layout is deterministic: fixed initial positions from the node
  hash, no physics randomness, no time-based animation.
- No server-side component, no write path, no authentication, nothing that needs a network at run
  time. If it cannot open the bundle offline, it is not shipped.
- Abandonment rule: if M6 is not clean, the directory is deleted before the freeze; a broken viewer
  under version control is a claim we cannot defend.

---

## 6. Retrieval

Retrieval is the mechanism that puts a chunk in front of the model, and its result is what the
`INFLUENCED` rule (§2.3) then observes. It is scored locally, deterministically, with no network
call (§IV, D1).

### 6.1 Corpus, chunking, identity

- Input: every file under `corpus/`, read as UTF-8 text, ordered by path.
- **Window:** 400 characters, stride 320, i.e. 80-character overlap. The last window of a document
  is shorter and is still kept; an empty document produces no chunk.
- `ordinal` is 0-based within the document. `chunk_id = "<doc_id>#<ordinal>"`, `char_start`,
  `char_end` recorded.
- **Chunks are shared nodes** (§III). The chunker is a pure function of `(document bytes, window,
  stride)`, so the same document produces the same chunk identifiers in every build, in every
  session. There is no per-session chunk.
- No tokenizer, no sentence splitter, no locale-dependent behaviour: the window is in characters so
  the boundary cannot move between a machine with a different Unicode table and the judge's.
- A trace that references a chunk records `text_sha256`; the builder recomputes it from `corpus/` and
  fails the build on a mismatch. This keeps the corpus the single source of text while letting the
  trace assert what the model actually saw.

Declared limitation: 400/80 is a demo choice, not a tuned value. On a real corpus the overlap would
be evaluated; here it exists so a fact spanning a boundary is still retrievable, and it is stated in
`README.md` as a simplification (§1.3 of the plan).

### 6.2 Lexical half

Computed in Python, not in the store (fulltext indexing exists and is deliberately unused, so the
lexical score is identical on every machine and testable without opening a store):

- Vocabulary: whitespace-and-punctuation tokenizer, lowercased, no stemming, no stop-word list
  beyond a fixed 20-word English list checked into the repository.
- `tf(t, c)` = raw count in the chunk; `idf(t)` = `ln((1 + N) / (1 + df(t))) + 1` with `N` chunks and
  `df` document frequency over chunks.
- `lex(c) = sum over query terms of tf(t,c) * idf(t)`, then divided by the maximum `lex` in the same
  query so it lands in `[0, 1]`. A query whose terms match nothing yields all-zero lexical scores
  rather than an error.

### 6.3 Vector half (D1)

- `TfidfVectorizer` over the same chunks and vocabulary, then
  `TruncatedSVD(n_components=128, algorithm="randomized", random_state=1729)`.
- The chunk matrix and the query vector are projected through the **same fitted model**, so a sign
  flip in the SVD basis affects both sides equally and the cosine is unaffected.
- Vectors are L2-normalized before storage; `chunk.embedding` holds 128 floats as a plain JSON list.
- Similarity: cosine, declared in the index (`vector.similarity_function: 'cosine'`).
- The vector half is read from the store, not recomputed at query time:

  ```cypher
  MATCH (c:Chunk)
  SEARCH c IN (VECTOR INDEX chunk_embedding FOR $query_vector LIMIT 20)
  SCORE AS score
  RETURN c.chunk_id AS chunk_id, score ORDER BY score DESC
  ```

  `20` is `min(20, chunk_count)`: it is enough to cover the demo corpus without truncating, and it is
  a named constant so a larger corpus would need a real candidate-merge strategy (declared, not
  hidden). Chunks outside that set contribute `vector = 0.0`.
- The dimension is 128 and is asserted at build time against the index declaration; a mismatch is a
  build failure, not a runtime surprise (`VectorIndexDimensionalityMismatch` is verified to be
  fatal).

### 6.4 Hybrid score, thresholds, k

```
score(c) = 0.7 * lex(c) + 0.3 * cos(c)
```

- Weights `0.7 / 0.3`, top `k = 5`, and **no score threshold**. On a ~20-chunk corpus a cutoff would
  be an arbitrary number masquerading as a tuned one (R4); what the demo asserts is the returned set,
  not a cutoff.
- The lexical half dominates by design, so a plausible-looking answer never depends on the vector
  half alone.
- Both components and the fused score are written onto the `RETURNED` edge, so the report and the
  tests can explain a rank without recomputing anything.
- The strategy identifier `hybrid:0.7lex+0.3vec` is stored on the `Retrieval` node, so a change of
  weights is visible in the graph rather than inferred from a changelog.

### 6.5 Determinism

Ordering is fixed everywhere it can be: chunks by `(path, ordinal)`, tokens by `(df desc, token)`,
fused results by `(score desc, chunk_id)`, and list columns sorted at render time (the engine does
not guarantee `collect()` order — observed). Dependency versions are pinned (`scikit-learn`, the
`relate` CLI, Python minor), and the seed is fixed.

Determinism is checked by **normalized query results**, never by byte equality of the `.rl` bundle:
the comparison drops the `timings` and `planCache` keys from `--mode json` output and sorts rows,
then compares. Two independent builds of the probe graph were compared this way and were `EQUAL`
with identical node and edge counts.

Declared limitation: the embedding *values* are reproducible only for a fixed `scikit-learn` version.
A minor-version bump can move the last decimals of a similarity score; the determinism check is
therefore run with the pinned version, and a bump is its own change with the check re-run.

### 6.6 What this retrieval cannot establish

On three sessions and a handful of documents, retrieval quality is not measured: no recall number,
no NDCG, no comparison against a baseline. The vector index is exercised — it returns ranked
neighbours and the report shows the cosine component — but nothing here claims that the ranking is
*good*. The demo's answers are anchored on graph structure, not on similarity, precisely so a weak
retriever cannot make a correct answer look wrong.

---

## 7. Report rendering

`python -m autopsy demo` opens `store/autopsy.rl` **read-only**, runs the four statements of §3,
and prints Markdown to stdout. It never rebuilds the store, never writes, and never needs a network
or a credential (§IV). `python -m autopsy verify` is the one that rebuilds, into a temp directory.

Exact structure, byte-for-byte shape:

````markdown
# Agent Autopsy — demo report

- store: `store/autopsy.rl` (bundle)
- store sha256: `0f3c...` — nodes 26, relationships 34
- relate: v1.3.0 · generated by autopsy 0.x
- sessions: `traces/s1.json`, `traces/s2.json`, `traces/s3.json`
- retrieval: hybrid:0.7lex+0.3vec · k=5 · svd=128

## Query 1 — Why did this decision happen?

`decision d1 (refund)` — the chunks that were in context, and where they came from.

| hop | node | label | evidence |
| --- | --- | --- | --- |
| 1 | s1 | Session | READ doc-poison#0 at step 1 |
| 2 | doc-poison#0 | Chunk | witness: context |
| 3 | doc-poison | Document | corpus/refunds.md |
| 4 | d1 | Decision | action: refund |
| 5 | e1 | Effect | refund 4800 EUR |

```cypher
MATCH (t:Task)-[:DECIDED]->(d:Decision {decision_id: $decision_id}) … (Q1B, as in section 3)
```

Reading: the decision leaned on one chunk of one document, which no policy of that document
authorized on its own.

## Query 2 — Which sessions share the poisoned document?

| document | path | sessions | chunks | influenced decisions |
| --- | --- | --- | --- | --- |
| doc-poison | corpus/refunds.md | s1, s2 | 1 | 2 |

```cypher
MATCH (doc:Document {doc_id: $document_id})<-[:PART_OF]-(c:Chunk) … (Q2)
```

Reading: two sessions, one document — reach a span tree cannot show.

## Query 3 — Which decisions have no valid policy?

| decision | action | effect | amount | policy | verdict |
| --- | --- | --- | --- | --- | --- |
| d2 | refund | refund | 4200 | p-strict | VIOLATES:amount_exceeds |
| d4 | delete_account | delete_account | — | — | UNSUPPORTED:no_policy |

```cypher
MATCH (d:Decision)-[:PRODUCED]->(e:Effect) … (Q3)
```

Reading: one effect exceeded its policy, one had no policy at all.

## Unverified

- Principle V: the retry half is demonstrated in the store; logic-failure-aborts is not.
- Viewer: out of scope; this report is the fallback.
- Retrieval quality: not measured on this corpus.
- Live path: does not exist in this scope (D2).
````

Rules that make the report checkable rather than decorative:

- **Every section prints the Cypher that produced it, verbatim from `queries/`.** The report and the
  catalogue cannot drift, and a judge can paste the query into `relate` and get the same table
  (§I, §VII).
- Section order is fixed. An empty result prints `_no rows_` rather than dropping the section: an
  empty answer is a result.
- Provenance comes from `relate info --json` and a hash of the bundle, not from running anything.
- Numbers are formatted with no thousands separator and amounts print as `—` when absent, so the
  table is stable and diffable.
- Reading lines are one sentence each, and each one states only what the table shows.
- The `## Unverified` section is mandatory and its lines come from a fixed list in the code, so a
  gap cannot disappear because someone tidied the output.
- Exit code is 0 on success, including empty sections; a failure prints the error to stderr and
  exits non-zero. Write failures, missing store and version mismatch are three distinct messages.

---

## Traceability

| Section | Source |
| --- | --- |
| 0 | probes against `relate` v1.3.0 on throwaway stores; commands quoted inline |
| 1 | `PLAN.md` §7.1; D9 layout; §III |
| 2 | `PLAN.md` §7.2; `CONSTITUTION.md` §II, §V |
| 3 | `PLAN.md` §7.3, M2.2, M3; `CONSTITUTION.md` §I, §III |
| 4 | `PLAN.md` §7.4, M1, R10; `CONSTITUTION.md` §V, §VI |
| 5 | `PLAN.md` §7.5, D3, §3.1 |
| 6 | `PLAN.md` §7.6, D1, R2, R4; `CONSTITUTION.md` §3 |
| 7 | `PLAN.md` §7.7, M4; `CONSTITUTION.md` §I, §VII |

Decisions taken by the human on 2026-11-26 for this document: content-hash document identity;
fixed-window shared chunks; `INFLUENCED` as `Chunk → Decision` with a closed witness enum and a
`session_id`; the four policy verdicts with `VIOLATES` as its own category; the CLI-behind-a-seam
builder; the eight-step trace taxonomy with the retry as its own step; redact-by-key plus
reject-personal-data; `0.7/0.3` hybrid with `k=5` and no threshold; the report structure with inline
Cypher; the viewer declared out of scope with a minimal stretch design; the six structural
invariants. They are recorded here so a later reader can judge whether they still hold.
