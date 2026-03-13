# AI-Orchestrated Parallel Development

**Run multiple Claude Code agents in parallel. Ship faster without merge conflicts.**

A battle-tested methodology + CLI tool for orchestrating parallel AI development using Claude Chat (planning) and Claude Code terminals (execution).

---

## The Problem

You have a big feature to build. One Claude Code session takes too long. Running multiple sessions causes merge conflicts, duplicated work, and chaos.

## The Solution

**Separate planning from execution. Give each agent an exclusive file path.**

```
You (Strategy) → Claude Chat (Planning) → Claude Code Agents (Execution)
                                           ├── Terminal 1: src/auth/
                                           ├── Terminal 2: src/api/
                                           ├── Terminal 3: src/models/
                                           └── Terminal 4: src/tests/
```

No merge conflicts. No context pollution. Agents work in parallel, each in their own directory.

---

## Quick Start (10 minutes)

### 1. Clone this repo

```bash
git clone https://github.com/osaka2077/ai-parallel-dev.git
cd ai-parallel-dev
```

### 2. Install dependencies

```bash
pip install pyyaml  # Only required dependency
```

### 3. Copy into your project

```bash
cp orchestrate.py /path/to/your/project/
cp -r templates/ /path/to/your/project/prompts/templates/
mkdir -p /path/to/your/project/.ai
```

### 4. Your first round

```bash
# 1. Define shared interfaces (the contract between agents)
#    → See examples/shared_interfaces.py

# 2. Write prompts (use a template)
#    → See templates/ and examples/round1/

# 3. Create manifest
#    → See examples/round1/manifest.yaml

# 4. Validate & start
python orchestrate.py validate prompts/round1
python orchestrate.py start 1 --budget MEDIUM

# 5. Open terminals, start agents
git checkout agent-r1-auth
claude --prompt-file prompts/round1/agent_auth.md

# 6. Monitor, merge, report
python orchestrate.py status
python orchestrate.py health
python orchestrate.py merge --batch --bisect-on-failure
python orchestrate.py test --full
python orchestrate.py report
```

---

## How It Works

### Three Roles, Conscious Separation

| Role | Tool | Purpose |
|------|------|---------|
| **You (Strategist)** | Your brain | Decides WHAT and WHY. Sets priorities, reviews results. |
| **Chat (Brain)** | Claude Web/App | Plans waves, writes prompts, analyzes results. Protected context. |
| **Agents (Hands)** | Claude Code terminals | Execute ONE prompt each. Focused context. Disposable. |

**Why separate Chat from Agents?** Context management. Chat stays clean for strategic thinking. Agents stay focused on implementation. If you mix both, the context fills up with code details and strategic thinking degrades.

### The Cycle (per Round)

```
Phase 0: Code-Intelligence  → Chat gathers facts (grep, find, git)
Phase 1: Planning & Prompts → Chat writes focused prompts per agent
Phase 2: Execution           → Agents work in parallel (1 terminal each)
Phase 3: Integration & Merge → Validate paths, merge, run tests
Phase 4: Analysis & Review   → Chat analyzes what worked, updates learnings
Phase 5: Next Round          → You decide direction, Chat plans next round
```

### Key Concepts

- **Exclusive File Paths**: Each agent writes ONLY to assigned directories. Zero merge conflicts.
- **shared_interfaces.py**: Contract file committed before agents start. No agent may modify it.
- **Waves**: Groups of agents that run in parallel. Wave 2 depends on Wave 1 being merged.
- **Prompt Templates**: Reusable prompt structures. 80% of every prompt is the same.
- **Health Monitoring**: Heartbeat, path-compliance, output-plausibility, budget checks.
- **Tiered Merge**: Agent validation → batch merge + affected tests → full suite once.

---

## CLI Reference

```
orchestrate start <round> [--mode A|B|C] [--budget SMALL|MEDIUM|LARGE|XL]
orchestrate status                         # Dashboard
orchestrate health                         # Health-checks all agents
orchestrate merge [--batch] [--bisect-on-failure] [--dry-run]
orchestrate next                           # Dispatch next wave
orchestrate validate <prompt-dir>          # Validate prompts before start
orchestrate preflight [prompt-dir]            # GitNexus dependency analysis
orchestrate report                         # Generate round report
orchestrate retry <agent-id> [--with-context "hint"]
orchestrate skip <agent-id>
orchestrate done <agent-id>                # Mark agent as finished
orchestrate test --full                    # Run full test suite
orchestrate reset [--hard]                 # Reset current round
orchestrate abort                          # Abort current round
```

### Modes

| Mode | Description | Use Case |
|------|-------------|----------|
| A | Maximum parallelism, all waves at once | Large teams, independent modules |
| B | Wave-by-wave, merge between waves | **Default.** Most projects. |
| C | Conservative, single agent at a time | Critical systems, learning the method |

### Budget Caps

| Label | Cap | Typical Use |
|-------|-----|-------------|
| SMALL | $50 | 2-3 agents, simple features |
| MEDIUM | $100 | 4-6 agents, standard development |
| LARGE | $200 | 8+ agents, complex features |
| XL | $300 | Full parallel development |

---

## GitNexus Integration (Optional)

If your project is indexed by GitNexus, `orchestrate.py` can automatically detect cross-path dependencies before agents start and analyze merge impact afterwards.

### Setup

```bash
# Index your codebase (one-time)
gitnexus analyze .
```

### Pre-flight: Dependency Analysis

```bash
# After validate, before start — checks for cross-path dependencies
orchestrate preflight prompts/round1/
```

This queries GitNexus for execution flows crossing exclusive path boundaries. If Agent A's path depends on files in Agent B's path, you'll see a warning with recommendations.

### Post-Merge Impact

After `orchestrate merge`, GitNexus automatically runs `detect_changes` to show:
- Risk level (low/medium/high/critical)
- Number of changed symbols and affected execution flows
- Recommendation for full test suite on critical changes

### Configuration

In `.ai/config.yaml`:

```yaml
gitnexus:
  enabled: true           # false to disable
  cli_path: null          # auto-detect, or explicit path
  impact_depth: 2         # blast radius depth
  post_merge_impact: true # detect_changes after merge
```

**No GitNexus? No problem.** All features gracefully skip with an info message. Fallback: `grep -r "from MODULE import" src/`

## Project Structure

```
your-project/
├── orchestrate.py              # CLI tool
├── shared_interfaces.py        # Contract between agents (per round)
├── prompts/
│   ├── templates/              # Reusable prompt templates
│   │   ├── new_module.md
│   │   ├── extend_module.md
│   │   ├── refactor.md
│   │   ├── write_tests.md
│   │   ├── integration_tests.md
│   │   └── fix_bug.md
│   └── round1/
│       ├── manifest.yaml       # Wave/agent definitions
│       ├── agent_auth.md       # Prompt for auth agent
│       ├── agent_api.md        # Prompt for API agent
│       └── agent_models.md     # Prompt for models agent
└── .ai/
    ├── config.yaml             # Test runner, cost calibration
    ├── context_bootstrap.md    # Quick-start context for Chat
    ├── learnings.md            # What worked, what didn't
    ├── decisions_log.md        # Architecture decisions
    ├── errors.md               # Error catalog
    ├── orchestrator_state.json # Auto-managed by CLI
    └── round_reports/
        ├── round01.md
        └── round02.md
```

---

## Configuration

Optional `.ai/config.yaml`:

```yaml
# Test runner (default: pytest)
test_runner: pytest
# Or for JS/TS:
# test_runner: ["npm", "test"]
# Or custom:
# test_runner: ["python", "-m", "pytest", "--tb=short"]

# Cost calibration (adjust after 2-3 rounds with real billing data)
tier_costs:
  opus: 8.0      # $/prompt for complex tasks
  sonnet: 3.0    # $/prompt for standard tasks
  haiku: 0.5     # $/prompt for routine tasks
```

---

## Scaling Guide

| Project Size | Mode | Agents | What You Need |
|-------------|------|--------|---------------|
| **LITE** | Start here | 1-3 | Just prompts + manual merge. No tooling needed. |
| **STANDARD** | After 2-3 rounds | 4-8 | orchestrate.py + templates + health checks |
| **FULL** | Large projects | 8+ | Everything + CI/CD integration + ast-grep |

---

## Full Methodology

The complete methodology document with all details, examples, and checklists:

**[methodology.md](methodology.md)**

Covers: Role model, 6-phase cycle, prompt templates, merge strategies, health monitoring, cost management, shared files handling, rollback strategy, CI/CD integration, persistence system, and quality pillars.

---

## License

MIT

---

*Built by [osaka2077](https://github.com/osaka2077) — battle-tested across multiple real projects.*
