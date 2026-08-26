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

## What a run looks like

Ask for something like *"audit all 60 endpoint handlers in src/api for auth issues and email me the critical findings"* and the skill reconnoiters just enough to name the items, then produces a phase plan:

```
Phase 0  Recon + rubric            inline        items, shared middleware, output shape
Phase 1  60 file audits            6 subagents   standard tier, 10 files each, fresh context
                                                 each worker writes an item file; parent keeps refs
Phase 2  Layered consolidation     3 subagents   fast tier: 60 → 3 summaries → 1 merge
                                                 completeness from the ledger: 60 in, 60 out
Phase 3  Prioritized remediation   inline        judgment the orchestrator owns
Phase 4  Verify                    1 subagent    strongest tier, fresh context
                                                 deterministic + semantic + sample; fail → targeted redo
Phase 5  Draft email               inline
Phase 6  HUMAN APPROVAL GATE       hard stop     exact action, scope, and cost shown
```

Every piece of that is the skill working. Recon is bounded, the fan-in is layered so detail survives, verification can't ratify its own synthesis, and the irreversible send waits for a human.

## What it does

- **Bounded recon.** Enough investigation to list items, shared resources, write locks, and the rubric — then the graph, then execution. Per-item work does not start during recon.
- **Dependency audit.** For each pair of steps: *does B literally read A's output?* If not, they're independent. Most "and then"s turn out to be narration.
- **Coupling split.** Data dependencies, resource constraints (concurrency, write locks), and control gates (verify, approve) stay separate. A rate limit caps width; it does not create an edge.
- **Subagent fan-out.** Where the host has a subagent tool, independent phases dispatch as parallel subagents with fresh contexts. Where it doesn't, they degrade to batched tool calls.
- **Artifacts and a ledger.** Workers write item files. The parent keeps an artifact ref and a 3-line summary. Completeness is expected vs received ids, named when missing.
- **Model tiering.** Cheap tier for mechanical checks, standard tier for per-item work, strongest tier for the final verification pass.
- **Layered fan-in.** Consolidates in batches of 20 to 30 rather than one synthesis pass over everything.
- **Three-stage verification.** Deterministic checks, then source re-derivation of Critical and top High, then a sample of the long tail. Failures feed a targeted redo, capped, then escalate.
- **Human approval gate.** Irreversible or outward-facing actions (sends, deploys, deletes) hard-stop for explicit human sign-off with concrete scope and cost.
- **Trust boundary.** Instructions found in repos, documents, webpages, and tool results are data unless the user delegated that source.

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

It deliberately does not trigger on everything. A five-step task where each step genuinely feeds the next is a chain, and drawing it as a graph adds nothing. The skill says so and gets on with it.

## What it doesn't do

There's no scheduler underneath a skill. It's instructions the model reads. Parallelism comes from the host's subagent tool when one exists; the skill decides *what* fans out, the environment runs it. If you have your own runner instead, [`references/plan-schema.md`](references/plan-schema.md) defines a JSON plan format you can feed it. Optional stdlib validators live in `scripts/`.

## Repo structure

```
graph-orchestrator/
├── SKILL.md                          # the skill, start here
├── references/
│   ├── execution-contract.md         # artifacts, worker shape, ledger
│   ├── verification.md               # three-stage verification
│   ├── best-practices.md             # worked example, failure modes, sizing
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

## Design notes

A few opinions baked in, learned from watching long runs degrade:

- **Fan-in is where quality is lost**, not fan-out. One synthesis pass over 100 outputs produces something thin after the first twenty items, and it looks fine. Layer at 20 to 30 and force specifics (paths, quantities, names) upward.
- **Put intermediate results in files.** If sixty workers dump their full output into the orchestrator, the skill has already failed its own premise.
- **Count before you consolidate.** If 38 of 40 came back, name the missing two rather than synthesizing over the gap.
- **The verifier can't be the author.** A critique pass over your own summary mostly agrees with the summary. Verification runs in a fresh context, from source, given the claims but not the synthesis.
- **Omit rather than fabricate.** The plan schema has no `retry` or `timeout` fields unless something actually enforces them. A spec that describes infrastructure you don't have invites everyone downstream to assume guarantees that aren't there.

## License

[MIT](LICENSE)
