# Graph Engineering: Patterns and Failure Modes

Read this when a plan is unusually large, or when diagnosing why a previous run degraded.

Trigger conditions live in `SKILL.md`'s description. This file is sizing, a worked example, and failure modes — not a second trigger list.

## Contents

- [A worked example](#a-worked-example)
- [Failure modes](#failure-modes)
- [Sizing guidance](#sizing-guidance)
- [When the graph is the wrong tool](#when-the-graph-is-the-wrong-tool)

---

## A worked example

**Request:** "Audit our 60-endpoint API for auth issues and give me a prioritized remediation plan."

### Recon (stop here)

Shared auth middleware is a known file. The item list is the 60 handlers. Rubric: "correct auth" means the handler uses the shared middleware or documents an exception. Worker shape: the item file in `references/execution-contract.md`. No per-handler analysis yet.

### Dependency audit

| Step | Reads prior output? | Kind | Verdict |
|---|---|---|---|
| List handlers + read middleware | No | recon | Inline, then stop recon |
| Read each endpoint's handler | No, each is independent input | dependency: none | Parallel, 60 items |
| Classify each endpoint's auth posture | Yes, needs handler + middleware | dependency | Depends on both |
| Cluster findings by issue type | Yes, needs all classifications | dependency | Depends on classification |
| Prioritize remediation | Yes, needs clusters | dependency | Depends on clustering |
| Verify | Yes, needs claims + sources | gate | After consolidation |
| API client, 5 concurrent | No | constraint | Width cap, not an edge |

The middleware read is a real dependency for classification, because classification interprets each handler *relative* to middleware defaults. Rate limits on the repo host, if any, are a concurrency constraint — they do not order handler A before handler B.

### Phases

```
Phase 0 (inline)       recon + rubric + artifact root
Phase 1 (parallel)     60 handler reads + 1 middleware read
                       workers write item files; parent keeps refs + 3-line summaries
Phase 2 (parallel)     60 classifications, batches of 20
Phase 3 (fan-in)       3 batch summaries → 1 clustering; completeness from the ledger
Phase 4 (sequential)   prioritization
Phase 5 (verify)       deterministic (60 in / 60 out, schema)
                       semantic: all Critical + top High, re-derived from source
                       sampling: a few ok / Low / Medium items
```

Note what phase 5 does not do: it does not only re-read the five loudest findings, and it does not critique the synthesis. A systematic miss in Medium would survive a top-5 pass.

### What the naive version looks like

"Go through the endpoints one by one and note auth issues, then write up a plan." Same nominal work. In practice endpoints 1 through 15 get careful treatment, 40 through 60 get a sentence each, and the write-up over-weights whatever was found early. The degradation is invisible in the output.

---

## Failure modes

**Fan-in flattening.** The single most common one. Symptom: the final output is detailed about early items and vague about later ones. Cause: one synthesis step over too many inputs. Fix: layer at 20 to 30, and require concrete specifics in each layer.

**Context stuffing.** Symptom: the orchestrator is summarizing 60 full worker essays. Cause: workers returned bodies instead of artifact refs. Fix: write the item file, return ref + 3-line summary. See `references/execution-contract.md`.

**Phantom parallelism.** Declaring items independent when they share mutable state. Symptom: conflicting edits, or later items contradicting earlier ones. Fix: classify coupling; put a `write_lock` on the shared path.

**Constraint promoted to edge.** Symptom: twenty independent API calls run as a chain of twenty because the API allows five at a time. Fix: keep them parallel and set `concurrency` to 5.

**The completeness gap.** Fan-in over 38 of 40 items, silently. Symptom: nothing, and that's the problem. Fix: count expected vs. received from the ledger and name what's missing.

**Top-N verification bias.** Symptom: Critical/High look solid; Low/Medium are systematically wrong. Cause: only the loudest findings were re-derived. Fix: three-stage verification in `references/verification.md`.

**Plan drift.** By phase 4 you're working from a mental model that no longer matches the plan. Symptom: work that doesn't feed anything downstream. Fix: restate the phase's dependency in one line at each boundary.

**Over-planning.** A 12-node graph for a task that was four sequential steps. Symptom: the plan is longer than the work. Fix: no meaningful fan-out means no formal plan.

**Batch abandonment.** One item errors and the whole phase halts, discarding completed work. Fix: record the failure, continue, report it at consolidation.

---

## Sizing guidance

These numbers size a run. They are not trigger thresholds. Whether to invoke the skill is the description in `SKILL.md`.

| Scale | Approach |
|---|---|
| < 6 subtasks, no fan-out | No formal plan. Audit dependencies mentally. |
| 6-30 items | Single fan-out, single fan-in. Plan fits in a short block. |
| 30-100 items | Batch the fan-out (20-25 per batch). Two-layer fan-in. |
| 100+ items | Three-layer fan-in. Consider whether the task should be narrowed or sampled first. At this scale, ask whether all items genuinely need individual treatment, or whether a sample plus a targeted sweep answers the question better. |

That last row matters more than it looks. A request to "analyze all 400 files" is often better served by analyzing 40 representative ones, forming a hypothesis, and then checking the hypothesis across the rest. Propose this when the full sweep looks disproportionate, but say so explicitly rather than quietly sampling.

---

## When the graph is the wrong tool

- **Exploratory work.** When each step's result determines what the next step even *is*, you can't plan the graph upfront. Work adaptively and plan a graph once the shape is known.
- **Genuinely sequential pipelines.** Extract → transform → load is a chain. Drawing it as a DAG adds nothing.
- **Single-artifact work.** Writing one document, fixing one bug. The overhead exceeds the benefit.
- **Mechanical bulk edits.** Renaming a symbol across a dozen files is a search-and-replace, not a fan-out with a rubric.
- **When the user asked a question.** Not everything is a workflow. A question wants an answer.
