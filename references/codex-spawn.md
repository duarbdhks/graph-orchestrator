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
model = <from the table>
reasoning_effort = <from the table>
```

Put the graph role in `task_name` and the prompt. Never encode the role as
`reviewer`, `sol_advisor_sol_reviewer`, `sol_advisor_terra_implementer`,
`explorer`, `worker`, `poteto-agent`, or another installed profile.

A spawn that omits `model` or `reasoning_effort` is invalid on Codex.

## Mapping

| Graph tier | Use | model | reasoning_effort |
|---|---|---|---|
| `fast` | mechanical checks, listing, volume investigation | `gpt-5.6-luna` | `max` |
| `standard` | per-item implementation, bug fix, refactoring, synthesis | `xai/grok-4.6` | `xhigh` |
| `strongest` | fresh-context verification, judgment, final review | `gpt-5.6-sol` | `xhigh` |

Unlisted per-item work uses `standard`. Unlisted verification uses `strongest`.

The parent owns integration, irreversible actions, and the final answer.

## Forbidden

Do not spawn Codex children as:

```text
agent_type = sol_advisor_sol_reviewer
agent_type = reviewer
agent_type = explorer
agent_type = worker
```

Those types ignore this mapping. `reviewer` pins `gpt-5.4 / high`.
`sol_advisor_sol_reviewer` pins `gpt-5.6-sol / high`.
