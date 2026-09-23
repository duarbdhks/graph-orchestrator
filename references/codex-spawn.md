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

| Graph tier | Use | model | reasoning_effort |
|---|---|---|---|
| `fast` | mechanical checks, exploration, blast-radius, test writing, independent verification | `gpt-6-luna` | `max` |
| `standard` | per-item work | canonical external seat; fallback `gpt-6-sol` | seat-specific; fallback `max` |
| `strongest` | architecture, final judgment after verification | `gpt-6-astra` | `xhigh` |

Before a `standard` fan-out, run `ocx agent status --json` and read the nested
`.injection.model`. When `.injection.multiAgentGuidanceEnabled` is true, use
that model with the effort below, rather than copying `.injection.effort`:

| `.injection.model` | `reasoning_effort` |
|---|---|
| `xai/grok-4.7` | `xhigh` |
| `xai/grok-4.7-build-fast` | `xhigh` |
| `deepseek/deepseek-flash` | `max` |

If status fails, `.injection` is missing or disabled, or the model is unlisted,
use `gpt-6-sol` / `max`. Do not change OpenCodex settings. Unlisted per-item work
uses `standard`; unlisted verification uses `fast`. Reserve `strongest` for a
separate final judge.

The parent owns integration, irreversible actions, and the final answer.

## Forbidden

Use `agent_type=default`. Semantic types such as `reviewer`,
`sol_advisor_sol_reviewer`, `explorer`, and `worker` may override this mapping
with their own model and effort.
