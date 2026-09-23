# Verification

Read this for high-stakes work: code that will merge, analysis that will inform a decision, output the user cannot easily check. `SKILL.md` names the node; this file is the procedure.

Verification is a quality check, not authorization. Irreversible actions still stop for a human after this passes.

Item file schema is `references/execution-contract.md`. This file does not restate those keys.

## Three stages

Run in this order. Skip a later stage only when `SKILL.md` tells you to omit Verification, and say that in the reply the user sees. If there is no phase plan, say the skipped stage in that same reply.

### 1. Deterministic

Cheap, objective, no LLM required.

- expected ids vs received ids (from the ledger)
- duplicate ids
- item schema: the required keys in `references/execution-contract.md`
- for code: tests, typecheck, lint — whichever the repo already runs — before any language-model verifier

If `scripts/validate-results.py` exists, use it here on the **item** JSONL, not the ledger. A failed deterministic stage is a gap or a contract break, not a "looks off" judgment. Name the missing or invalid ids. Do not start the semantic stage until every expected id is `done`, `failed`, or `blocked`.

### 2. Semantic

Re-derive claims from source, in a fresh context that did not produce the work. Give the verifier the claims and the sources, not the synthesis.

- every finding with Critical severity
- every High finding that would change the recommendation
- at least one item that stage 2 did not re-derive

A critique pass over a summary mostly agrees with the summary. That is not this stage.

### 3. Sampling

Stage 2 can miss a systematic error that lives in Low, Medium, or `ok`.

Re-derive at least one `ok`, Low, or Medium item that stage 2 did not re-derive. Use the same source check. If that item disagrees with the worker, call it a class of failure in the failure report.

## Recovery

Two modes. Pick by what failed, not by preference.

**Node-local redo.** The graph is still right. Redo only the affected nodes, not the whole graph. Re-run deterministic checks on the new outputs. Re-run semantic checks on the changed claims, plus a fresh sample. Cap at 3 attempts.

**Re-plan.** The rubric or the graph is wrong: the same class of failure returns twice, or two "independent" items actually conflict. Stop. Say what changed. Build a new graph. Do not quietly work around it.

If it still cannot pass, give the user the failure report. Do not ship output you know is flawed.

## Who runs it

Prefer host commands and the validator scripts for stage 1. For stages 2 and 3, a fresh-context subagent if the host has one; otherwise a separate inline pass that is not looking at the synthesis. Use `fast` for independent verification and sampling. Keep `strongest` for a separate final judge after verification.

On Codex, spawn both roles with `agent_type="default"` and explicit model and
effort from `references/codex-spawn.md`.

## What this file is not

This does not approve sends, deploys, deletes, or production writes. Those are gates in `SKILL.md`.
