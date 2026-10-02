# Codex spawn mapping

Read this before a Codex fan-out. `SKILL.md` keeps `tier` as a plan field.
This file is the host mapping. Other hosts ignore it.

Codex `spawn_agent` has no `tier` argument. Do not translate a tier into a
semantic `agent_type`. Those profiles pin their own model and effort.

## Contract

Every Codex subagent uses:

```text
agent_type = default
fork_turns = none
model = <resolved below>
reasoning_effort = <resolved below>
```

Put the graph role in `task_name` and the prompt, not in `agent_type`.

A spawn that omits `model` or `reasoning_effort` is invalid on Codex. Record that spawn on the ledger as `failed` with `error` set, and do not leave the row `running`. The row is in `references/execution-contract.md`.

## Mapping

Before every Codex fan-out, read `~/.codex/AGENTS.md` and the YAML in
`~/.codex/pstack-models.md`. Resolve both model and effort through that global
policy. This mapping chooses a selection, not a separate model rule:

| Graph tier | Use | YAML selection |
|---|---|---|
| `fast` | mechanical checks, exploration, blast-radius, test writing, independent verification | `defaults.evidence` |
| `standard` | per-item work | `roles["feature, refactoring"]` |
| `strongest` | architecture, final judgment after verification | `defaults.judgment` |

All three tiers follow the active OpenCodex model and effort unchanged.
When OpenCodex is unavailable, each selection uses its own configured
fallback pair. The global policy owns status reads, timeouts, supported
pairs, explicit user overrides and fallback reporting. If either policy
file is missing or invalid, stop dispatch and report the missing policy.

Unlisted per-item work uses `standard`; unlisted verification uses `fast`.
Reserve `strongest` for a separate final judge. Tiers and independent roles
remain distinct even when their resolved models are identical.

The parent owns integration, irreversible actions, and the final answer.

## Forbidden

Use `agent_type=default`. Semantic types such as `reviewer`,
`sol_advisor_sol_reviewer`, `explorer`, and `worker` may override this mapping
with their own model and effort.
