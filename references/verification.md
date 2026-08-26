# Verification

Read this for high-stakes work: code that will merge, analysis that will inform a decision, output the user cannot easily check. `SKILL.md` names the node; this file is the procedure.

Verification is a quality check, not authorization. Irreversible actions still stop for a human after this passes.

## Three stages

Run in this order. Skip a later stage only for low-stakes work, and say so in the phase plan.

### 1. Deterministic

Cheap, objective, no LLM required.

- expected ids vs received ids (from the ledger)
- duplicate ids
- item schema (`item_id`, `status`, `evidence` present; `status` in `ok | failed | blocked`)
- for code: tests, typecheck, lint — whichever the repo already runs — before any language-model verifier

If `scripts/validate-results.py` exists, use it here. A failed deterministic stage is a gap or a contract break, not a "looks off" judgment. Name the missing or invalid ids and stop the semantic stage until the set is honest.

### 2. Semantic

Re-derive claims from source, in a fresh context that did not produce the work. Give the verifier the claims and the sources, not the synthesis.

- every finding with Critical severity
- the highest-severity High findings, enough that a miss would change the recommendation (top N is a budget, not a substitute for Critical-all)
- at least one claim that is not in the first batch, so early-item bias is visible

A critique pass over a summary mostly agrees with the summary. That is not this stage.

### 3. Sampling

Top-N semantic checks miss a systematic error that lives in Low, Medium, or `ok`.

Draw a small random sample from items that were not in stage 2: `ok` items and Low/Medium findings. Re-derive those from source the same way. If the sample disagrees with the worker, treat it as a class of failure, not a one-off, and widen.

## Retry

Failures are data.

1. Redo only the affected nodes, not the whole graph.
2. Re-run deterministic checks on the new outputs.
3. Re-run semantic checks on the changed claims, plus a fresh sample.
4. Cap at about three attempts.
5. If the same class of failure returns twice, the rubric or the graph is wrong: stop and re-plan.
6. If it still cannot pass, give the user the failure report. Do not ship output you know is flawed.

## Who runs it

Prefer host commands and the validator scripts for stage 1. For stages 2 and 3, a fresh-context subagent if the host has one; otherwise a separate inline pass that is not looking at the synthesis. The strongest model tier belongs here, not on mechanical extraction.

## What this file is not

This does not approve sends, deploys, deletes, or production writes. Those are gates in `SKILL.md`.
