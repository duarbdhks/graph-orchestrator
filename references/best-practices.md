# Graph Engineering: Patterns and Failure Modes

Read this when a plan is unusually large, or when diagnosing why a previous run degraded.

## Contents

- [A worked example](#a-worked-example)
- [Failure modes](#failure-modes)
- [Sizing guidance](#sizing-guidance)
- [When the graph is the wrong tool](#when-the-graph-is-the-wrong-tool)

---

## A worked example

**Request:** "Audit our 60-endpoint API for auth issues and give me a prioritized remediation plan."

### Dependency audit

| Step | Reads prior output? | Verdict |
|---|---|---|
| Read each endpoint's handler | No, each is independent input | Parallel, 60 items |
| Identify the shared auth middleware | No, separate file, known upfront | Parallel with the above |
| Classify each endpoint's auth posture | Yes, needs handler + middleware behavior | Depends on both |
| Cluster findings by issue type | Yes, needs all classifications | Depends on classification |
| Prioritize remediation | Yes, needs clusters | Depends on clustering |

Hidden edges: the middleware read must complete before classification, because classification interprets each handler *relative* to middleware defaults. That's a real edge, easy to miss. It looks like independent reading.

### Phases

```
Phase 1 (parallel)     60 handler reads + 1 middleware read
Phase 2 (parallel)     60 classifications, batches of 20
Phase 3 (fan-in)       3 batch summaries → 1 clustering
Phase 4 (sequential)   prioritization
Phase 5 (verify)       re-check the 5 highest-severity findings against source
```

Note what phase 5 does: it re-reads the actual handler for the top findings rather than reviewing the summary. A critique pass over your own synthesis tends to ratify it.

### What the naive version looks like

"Go through the endpoints one by one and note auth issues, then write up a plan." Same nominal work. In practice endpoints 1 through 15 get careful treatment, 40 through 60 get a sentence each, and the write-up over-weights whatever was found early. The degradation is invisible in the output.

---

## Failure modes

**Fan-in flattening.** The single most common one. Symptom: the final output is detailed about early items and vague about later ones. Cause: one synthesis step over too many inputs. Fix: layer at 20 to 30, and require concrete specifics in each layer.

**Phantom parallelism.** Declaring items independent when they share mutable state. Symptom: conflicting edits, or later items contradicting earlier ones. Fix: run the hidden-edge check, especially for anything that writes.

**The completeness gap.** Fan-in over 38 of 40 items, silently. Symptom: nothing, and that's the problem. Fix: count expected vs. received at every fan-in and name what's missing.

**Plan drift.** By phase 4 you're working from a mental model that no longer matches the plan. Symptom: work that doesn't feed anything downstream. Fix: restate the phase's dependency in one line at each boundary.

**Over-planning.** A 12-node graph for a task that was four sequential steps. Symptom: the plan is longer than the work. Fix: apply the threshold. No fan-out and fewer than ~6 subtasks means no formal plan.

**Batch abandonment.** One item errors and the whole phase halts, discarding completed work. Fix: record the failure, continue, report it at consolidation.

---

## Sizing guidance

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
- **When the user asked a question.** Not everything is a workflow. A question wants an answer.
