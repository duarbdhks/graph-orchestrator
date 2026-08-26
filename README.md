<p align="center">
  <img src="assets/banner.png" alt="Graph Engineering" width="100%" />
</p>

**A skill that plans multi-step work as a dependency graph instead of a linear chain.**

No framework. No runner. No dependencies. Just instructions that change how the model plans: which work fans out to parallel subagents, which must wait, where results leave context and land in files, and which single node stops for a human.

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)

---

## The problem

Give an agent a big task ("audit these 60 files", "research these 30 companies") and it narrates a chain: first this, then this, then this. Two things go wrong.

1. **Context burns linearly.** By item 40, the context window is full of items 1 through 39. The first fifteen items get careful treatment, the last twenty get a sentence each. You won't notice, because the output still *looks* complete.
2. **Independent work runs sequentially.** Most "and then"s in a plan are narration, not dependency. The steps could have fanned out. Instead they queue.

The fix isn't a bigger context window. It's structure: a dependency graph, executed in phases, with results written to artifacts, a ledger that names gaps, and gates that catch problems before they ship.

The graph is the contract. Phases are a derived schedule. The skill designs topology; the host runs it.

## What a run looks like

Ask for something like *"audit all 60 endpoint handlers in src/api for auth issues and email me the critical findings"* and the skill reconnoiters just enough to name the items, then writes a graph and derives a schedule:

```
Recon     items, shared middleware, write locks, rubric, output shape     inline
Fan-out   60 handler audits, fresh context per batch                      subagents
          each worker writes an item file; parent keeps refs
Join      layered consolidation; completeness from the ledger             60 in, 60 out
Judge     prioritized remediation                                         inline
Verify    deterministic + semantic + sample; fail → node-local redo       strongest, fresh context
Draft     email                                                           inline
Gate      HUMAN APPROVAL                                                  exact action, scope, cost
```

Recon is bounded, the join is layered so detail survives, verification can't ratify its own synthesis, and the irreversible send waits for a human. The worked graph behind this picture is in [`references/best-practices.md`](references/best-practices.md). The agent procedure is [`SKILL.md`](SKILL.md).

## Install

With the [skills](https://github.com/vercel-labs/skills) CLI:

```bash
npx skills add https://github.com/duarbdhks/graph-orchestrator
```

Or copy the repo into your agent's skills directory as `graph-orchestrator`. The directory name must match the skill `name` in `SKILL.md`.

```bash
git clone https://github.com/duarbdhks/graph-orchestrator
cp -r graph-orchestrator <your-agent-skills-dir>/graph-orchestrator
```

For a single project instead of globally, use a project-local skills folder your host already loads.

Verify it loaded:

```bash
head <your-agent-skills-dir>/graph-orchestrator/SKILL.md
```

## When it triggers

See the `description` field in `SKILL.md`. That is the only trigger list.

It deliberately does not trigger on everything. A five-step task where each step genuinely feeds the next is a chain, and drawing it as a graph adds nothing.

## What it doesn't do

There's no scheduler underneath a skill. It's instructions the model reads. Parallelism comes from the host's subagent tool when one exists; the skill decides *what* fans out, the environment runs it.

`scripts/` are contract checkers, not a runner. They do not execute the graph. If you have your own runner, [`references/plan-schema.md`](references/plan-schema.md) defines a JSON plan format you can feed it — the same model as the markdown graph, for handoff only.

## Repo structure

```
graph-orchestrator/
├── SKILL.md                          # the skill, start here
├── references/
│   ├── execution-contract.md         # artifacts, worker shape, ledger
│   ├── verification.md               # three-stage verification
│   ├── best-practices.md             # worked graph, failure modes, sizing
│   └── plan-schema.md                # JSON plan format for external runners
├── evals/
│   ├── trigger-cases.json            # should / should-not trigger queries
│   └── behavior-cases.md             # expected agent behavior
├── scripts/
│   ├── validate-plan.py              # cycle, missing refs, duplicate ids
│   └── validate-results.py           # expected vs received ids, item schema
├── README.md
└── LICENSE
```

`SKILL.md` is intentionally short. It gets loaded into the model's context, so every line has to earn its place. The references load only when needed.

## License

[MIT](LICENSE)
