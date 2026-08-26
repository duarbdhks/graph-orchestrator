# Sizing and Failure Modes

Read this when a plan is unusually large, or when diagnosing why a previous run degraded.

Trigger conditions live in `SKILL.md`'s description. This file sizes a run after the skill has loaded. Triggering and drawing a formal graph are different questions: a four-module request can load the skill and still get a mental audit instead of a 12-node DAG.

## Contents

- [A worked example](#a-worked-example)
- [Failure modes](#failure-modes)
- [Sizing guidance](#sizing-guidance)
- [When the graph is the wrong tool](#when-the-graph-is-the-wrong-tool)

---

## A worked example

**Request:** "Audit our 60-endpoint API for auth issues and give me a prioritized remediation plan."

### Recon (stop here)

Shared auth middleware is a known file. The item list is the 60 handlers. Write locks: none yet. Rubric: "correct auth" means the handler uses the shared middleware or documents an exception. Worker shape: the item file in `references/execution-contract.md`. No per-handler analysis yet.

The middleware body can be pasted into each worker prompt. Then read and classify are one node, not two phases. Split them only when classification must wait on a result you do not have yet.

### Graph (write this first)

```
nodes
  recon                 inline
  classify_handler      cardinality 60, executor subagent, requires recon
  cluster               requires classify_handler.*
  prioritize            inline, requires cluster
  verify                gate, requires prioritize
  draft_plan            inline, requires verify

dependencies
  recon.output → classify_handler
  classify_handler.* → cluster
  cluster.output → prioritize
  prioritize.output → verify

constraints
  none
  (repo-host rate limit, if any: concurrency=5 on that API — width, not an edge)

gates
  verify before draft_plan
  approval: none
```

`none` on constraints is an inspected result, not a skipped heading.

Classification is relative to middleware defaults. If the middleware text is in the prompt, that is shared context, not a `requires` edge from a separate read node.

### Derived phases

```
Phase 1 (inline)       recon + rubric + artifact root
Phase 2 (parallel)     60 classify_handler; workers write item files
Phase 3 (fan-in)       cluster in layers; completeness from the ledger
Phase 4 (inline)       prioritize
Phase 5 (verify)       deterministic → semantic → sample; see references/verification.md
```

Layer fan-in at 20 to 30 items. A 60-item group is two layers (60 → 3 → 1), not one synthesis over sixty files.

### What the naive version looks like

"Go through the endpoints one by one and note auth issues, then write up a plan." Same nominal work. In practice endpoints 1 through 15 get careful treatment, 40 through 60 get a sentence each, and the write-up over-weights whatever was found early. The degradation is invisible in the output.

---

## Failure modes

**Phases without a graph.** Symptom: a Phase 1 / 2 / 3 essay and no node list, no typed coupling, no `none`. Cause: narration was copied into a schedule. Fix: write `## Graph` first; derive phases from it.

**Fan-in flattening.** The single most common quality failure. Symptom: the final output is detailed about early items and vague about later ones. Cause: one synthesis step over too many inputs. Fix: layer at 20 to 30, and require concrete specifics in each layer.

**Context stuffing.** Symptom: the orchestrator is summarizing 60 full worker essays. Cause: workers returned bodies instead of artifact refs. Fix: write the item file, return the parent shape in `references/execution-contract.md`.

**Phantom parallelism.** Declaring items independent when they share mutable state. Symptom: conflicting edits, or later items contradicting earlier ones. Fix: `write_lock` on the shared path, not a fake `A → B` edge.

**Constraint promoted to edge.** Symptom: twenty independent API calls run as a chain of twenty because the API allows five at a time. Fix: keep them parallel and set `concurrency` to 5.

**The completeness gap.** Fan-in over 38 of 40 items, silently. Symptom: nothing, and that's the problem. Fix: count expected vs received from the ledger and name what's missing.

**Top-N verification bias.** Symptom: Critical/High look solid; Low/Medium are systematically wrong. Cause: only the loudest findings were re-derived. Fix: three-stage verification in `references/verification.md`.

**Plan drift.** By phase 4 you're working from a mental model that no longer matches the graph. Symptom: work that doesn't feed anything downstream. Fix: restate the phase's `requires` in one line at each boundary.

**Over-planning.** A 12-node graph for a task that was four sequential steps. Symptom: the plan is longer than the work. Fix: no meaningful fan-out means no formal plan. Loading this skill is allowed; dressing a chain as a DAG is not.

**Batch abandonment.** One item errors and the whole phase halts, discarding completed work. Fix: record the failure, continue, report it at consolidation.

---

## Sizing guidance

These numbers size a run after the skill is already in context. They are not trigger thresholds.

| Scale | Approach |
|---|---|
| < 6 subtasks **and** no fan-out | No formal plan. Audit dependencies mentally. |
| A few independent items with real fan-out (e.g. 4 modules) | Short graph: one parallel phase plus join. Not a 12-node DAG. |
| 6-30 items | Single fan-out, single fan-in. Plan fits in a short block. |
| 30-100 items | Batch the fan-out (20-25 per batch). Two-layer fan-in. |
| 100+ items | Three-layer fan-in. Ask whether all items need individual treatment, or a sample plus a targeted sweep answers better. |

A request to "analyze all 400 files" is often better served by analyzing 40 representative ones, forming a hypothesis, and then checking the hypothesis across the rest. Propose this when the full sweep looks disproportionate. Say so. Do not quietly sample.

---

## When the graph is the wrong tool

- **Exploratory work.** When each step's result determines what the next step even *is*, you can't plan the graph upfront. Work adaptively and plan a graph once the shape is known.
- **Genuinely sequential pipelines.** Extract → transform → load is a chain. Drawing it as a DAG adds nothing.
- **Single-artifact work.** Writing one document, fixing one bug. The overhead exceeds the benefit.
- **Mechanical bulk edits.** Renaming a symbol across a dozen files is a search-and-replace, not a fan-out with a rubric.
- **When the user asked a question.** Not everything is a workflow. A question wants an answer.
