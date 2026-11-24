# Verification

Read this for high-stakes work: code that will merge, analysis that will inform a decision, output the user cannot easily check. `SKILL.md` names the node; this file is the procedure.

Verification is a quality check, not authorization. Irreversible actions still stop for a human after this passes.

Item file schema is `references/execution-contract.md`. This file does not restate those keys.

## Three stages

Run in this order. Skip a later stage only when `SKILL.md` tells you to omit Verification, and say that in the reply the user sees. If there is no phase plan, say the skipped stage in that same reply.

### 1. Deterministic

Cheap, objective, no LLM required.

- planned IDs, ledger rows, and current item files reconciled per `references/execution-contract.md`
- duplicate ids
- item schema: the required keys in `references/execution-contract.md`
- for code: tests, typecheck, lint — whichever the repo already runs — before any language-model verifier

For a gate that requires every item to succeed, run `scripts/validate-results.py --require-ok <expected-ids> <item-results.jsonl>` with the required IDs and current item files for that gate. Where the script is unavailable, require a valid `ok` result for each required ID. Keep the gate closed when a required item is missing, invalid, failed, or blocked. Report the affected IDs and start the semantic stage only after the deterministic checks pass.

### 2. Semantic

Re-derive claims from source in a fresh context. Give the verifier the claims and the sources. The verifier reads the scoped inputs and writes its verification findings. The parent assigns fixes to the affected producers.

- every finding with Critical severity
- every High finding that would change the recommendation

Stage 3 independently samples the remaining Low/Medium/ok items; do not count those as stage 2 checks.

A critique pass over a summary mostly agrees with the summary. That is not this stage.

### 3. Sampling

Stage 2 can miss a systematic error that lives in Low, Medium, or `ok`.

Re-derive at least one `ok`, Low, or Medium item that stage 2 did not re-derive. Use the same source check. If that item disagrees with the worker, call it a class of failure in the failure report.

## Recovery

Two modes. Pick by what failed, not by preference.

**Node-local redo.** When a result fails verification, follow `input_refs` and `requires` to find every consumer of the invalidated output. Clear stale output refs and gate verdicts before scheduling more work. Block consumers until their required inputs are ready again. When the graph still fits, retry affected producers and recompute their consumers. Reuse successful items whose inputs and rubric still match. Recheck gates on the current results, including any approval tied to replaced results. Count at most three dispatches per item in the same run.

If a retry changes a route, re-derive the affected phases and expected IDs. Reconcile any prior writes before dispatching the new path. Keep the affected path blocked while a prior effect is uncertain. Re-run deterministic checks on new outputs, semantic checks for changed claims, and a fresh sample.

**Re-plan.** The rubric or the graph is wrong: the same class of failure returns twice, or two "independent" items actually conflict. Stop. Say what changed. Build a new graph. Do not quietly work around it.

If it still cannot pass, give the user the failure report. Do not ship output you know is flawed.

## Who runs it

Prefer host commands and the validator scripts for stage 1. For stages 2 and 3, a fresh-context subagent if the host has one; otherwise a separate inline pass that is not looking at the synthesis. Use `fast` for independent verification and sampling. Keep `strongest` for a separate final judge after verification.

On Codex, spawn both roles with `agent_type="default"` and explicit model and
effort from `references/codex-spawn.md`.

## What this file is not

This does not approve sends, deploys, deletes, or production writes. Those are gates in `SKILL.md`.
