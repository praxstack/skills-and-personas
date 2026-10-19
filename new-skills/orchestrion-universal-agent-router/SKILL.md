---
name: orchestrion-universal-agent-router
description: >
  Universal host-neutral agent orchestration skill. Use this at the start of any non-trivial task to discover the current agent host, load the right installed skills, route ambiguous human requests through planning/TDD/debugging/review/QA/council gates, create TODOs, and prevent false completion. Designed to coordinate Superpowers, gstack, Matt Pocock skills, and llm-council-plus without assuming Claude, Codex, OpenCode, Hermes, OpenClaw, Cline, KiloCode, Antigravity, or any other specific agent.
---

# Orchestrion: Universal Agent Skill Router

> A host-neutral skill for agents that must coordinate many other skills without pretending every agent is the same machine.

## 0. Activation

Use Orchestrion whenever the human asks for any of the following:

- Build, modify, debug, refactor, review, test, document, ship, or deploy software.
- Turn vague human intent into a plan or implementation.
- Use or combine skills from Superpowers, gstack, Matt Pocock skills, or llm-council-plus.
- Work in an unfamiliar repository.
- Make a decision with architecture, security, product, data, deployment, or long-term maintenance risk.
- Continue work after another agent/session.
- Create TODOs for agent execution.

If the task is trivial, still perform a lightweight host/capability check, but do not run the full orchestration ceremony.

---

## 1. Prime directive

The human may provide vague, messy, contradictory, incomplete, emotional, or misspelled tasks.

Do not jump straight into implementation.

Route the task through the strongest available workflow:

```text
INTAKE
→ HOST DISCOVERY
→ SKILL DISCOVERY
→ AMBIGUITY REDUCTION
→ PLAN
→ COUNCIL CHECK WHEN HIGH-RISK
→ TODO CREATION
→ ISOLATED EXECUTION
→ TDD / DEBUG / IMPLEMENT
→ REVIEW
→ QA / SECURITY / PERFORMANCE
→ VERIFICATION
→ DOCS
→ SHIP / HANDOFF / RETRO
```

### Non-negotiable contract

```text
1. Do not pretend a skill, MCP tool, plugin, browser, or CLI exists.
2. Do not claim a skill was loaded unless it was actually invoked, read, imported, or applied through a declared fallback.
3. Do not implement through ambiguity when clarification/planning skills are available.
4. Do not patch bugs without reproduction and root-cause evidence.
5. Do not claim completion without verification evidence.
6. Do not ship without review and QA when those skills/tools exist.
7. Do not deploy without post-deploy observation when deployment/canary tools exist.
8. TODOs are the execution spine, not decoration.
```

---

## 2. Host-neutral vocabulary

Different agents expose skills differently. Use these abstract operations and map them to the current host.

| Abstract operation | Meaning |
|---|---|
| `DISCOVER_HOST()` | Identify current agent/runtime and available capability surfaces. |
| `DISCOVER_SKILLS()` | Find installed skills, slash commands, MCP tools, plugins, rule files, and project docs. |
| `LOAD_SKILL(name)` | Invoke/read/import the real skill through the host's native mechanism. |
| `RUN_SKILL(name, input)` | Execute the skill if the host supports executable skills or slash commands. |
| `FALLBACK_METHOD(name)` | Apply the documented method manually, clearly labeled as fallback. |
| `CREATE_TODO_LEDGER()` | Create a living task list with states, evidence, blockers, and skill gates. |
| `COUNCIL_QUERY()` | Use llm-council-plus through MCP, REST/API skill, CLI/web UI, or fallback prompt handoff. |

Never expose these names as fake tool calls. They are implementation-independent mental handles.

---

## 3. Host discovery

Before choosing paths, identify where you are running.

### 3.1 Detect host identity

Inspect what is available, in this order:

```text
1. System/developer/runtime metadata.
2. Built-in tool names.
3. Agent-specific command palette/slash command list.
4. Environment variables.
5. Project instruction files.
6. Local skill/plugin directories.
7. Process names or CLI help output, if terminal access exists.
```

### 3.2 Known host hints

Use these as hints, not truth. Verify locally.

| Host / agent family | Common clues | Likely skill surfaces |
|---|---|---|
| Claude Code | `CLAUDE.md`, `~/.claude/skills`, `/plugin`, `claude mcp` | Skills, slash commands, MCP |
| OpenAI Codex CLI | `AGENTS.md`, `~/.codex`, `codex` CLI | Instructions, skills/plugins where supported, terminal |
| OpenCode | `~/.config/opencode`, `opencode` CLI | Skills/config, terminal |
| Cursor | `.cursor`, Cursor rules, IDE agent context | Rules, commands, MCP/tool integrations |
| Cline / Roo / KiloCode style agents | VS Code extension context, MCP config, task plan UI | MCP, project rules, edit/terminal/browser tools |
| Antigravity-style IDE agents | IDE workspace context, task/run panels | Project docs, tool use, terminal/browser if exposed |
| Hermes | `~/.hermes`, Hermes memory/skills, handoff/delegation patterns | Skills, memory, CLI delegation |
| OpenClaw | OpenClaw/ClawHub context, ACP/agent sessions | Native skills, spawned coding sessions |
| Gemini CLI | `GEMINI.md`, Gemini CLI, MCP config | Instructions, MCP, terminal |
| GitHub Copilot coding agent | GitHub issue/PR context, Copilot agent environment | Repository instructions, PR workflows |
| Pi | `~/.pi/agent/skills`, `~/.pi/agent/AGENTS.md`, `pi` CLI | Skills, extensions, MCP |
| Unknown agent | No reliable host signal | Markdown method fallback + available tools only |

If the host is unknown, proceed with the portable fallback protocol. Do not block unless the task requires unavailable tools.

---

## 4. Capability discovery

Create a capability matrix before running a serious workflow.

```markdown
## Capability Matrix

- Host:
- Skill mechanism available: yes/no/unknown
- Slash commands available: yes/no/unknown
- MCP available: yes/no/unknown
- Terminal available: yes/no/unknown
- File editing available: yes/no/unknown
- Browser available: yes/no/unknown
- Git available: yes/no/unknown
- Issue tracker available: yes/no/unknown
- LLM Council Plus available: yes/no/unknown
- Existing project instructions: [AGENTS.md / CLAUDE.md / GEMINI.md / .cursor rules / other]
- Missing critical capabilities:
```

### 4.1 Generic local search commands

Use only if terminal/filesystem access exists.

```bash
# Common skill and instruction locations
for d in \
  "$HOME/.claude/skills" \
  "$HOME/.codex/skills" \
  "$HOME/.config/opencode/skills" \
  "$HOME/.cursor/skills" \
  "$HOME/.hermes/skills" \
  "$HOME/.gbrain/skills" \
  "$HOME/.kiro/skills" \
  "$HOME/.slate/skills" \
  "$HOME/.factory/skills" \
  "$HOME/.pi/agent/skills" \
  "$HOME/.agents/skills" \
  ".claude" ".cursor" ".codex" ".opencode" ".hermes" ".roo" ".clinerules" ".kilocode"
do
  [ -e "$d" ] && echo "FOUND $d"
done

# Find skill files without assuming host
find "$HOME" "$(pwd)" \
  -maxdepth 5 \( -iname "SKILL.md" -o -iname "AGENTS.md" -o -iname "CLAUDE.md" -o -iname "GEMINI.md" -o -iname "*rules*" \) \
  2>/dev/null | sort | head -200
```

---

## 5. Skill loading precedence

When multiple mechanisms exist, prefer the one with the strongest native semantics.

```text
1. Native executable skill/slash command/plugin.
2. MCP tool that performs the intended action.
3. Local SKILL.md read/import.
4. Project instruction file, such as AGENTS.md, CLAUDE.md, GEMINI.md, rules files.
5. Official repo docs.
6. Manual fallback method, clearly labeled.
```

### 5.1 Missing skill rule

If a required skill is missing:

```markdown
## Missing Skill Handling

- [ ] Name the missing skill.
- [ ] State which host/capability was checked.
- [ ] Search likely locations.
- [ ] If install is safe and permitted, install or print exact install steps.
- [ ] If install is not possible, use `FALLBACK_METHOD(skill-name)` and label it.
- [ ] Continue with best-effort only if correctness and safety are not compromised.
```

Never say "loaded X" if the agent only copied the idea of X.

---

## 6. Always-start skill gate

For non-trivial software work, first try to load:

```text
using-superpowers
```

`using-superpowers` is the dispatcher/constitution layer. If present, obey it first.

If unavailable, apply this fallback:

```markdown
## Fallback: using-superpowers

- [ ] Search for applicable skills before acting.
- [ ] Prefer process skills before implementation skills.
- [ ] If any skill has even a small chance of applying, inspect/load it before proceeding.
- [ ] Treat debugging/TDD/verification skills as rigid workflows.
- [ ] Treat product/design/planning skills as adaptable workflows.
```

---

## 7. Core skill families

### 7.1 Superpowers: discipline and workflow gates

Use as the constitutional workflow.

| Skill | Use when |
|---|---|
| `using-superpowers` | Start every non-trivial task; route to skills. |
| `brainstorming` | Human request is rough, ambiguous, product/design-heavy, or underspecified. |
| `using-git-worktrees` | Work should be isolated before implementation. |
| `writing-plans` | Convert accepted direction into small executable tasks. |
| `executing-plans` | Execute a plan with checkpoints. |
| `dispatching-parallel-agents` | Independent tasks can run in parallel without shared mutable conflict. |
| `subagent-driven-development` | Use fresh agents per task/slice. |
| `test-driven-development` | Build or fix via red/green/refactor. |
| `systematic-debugging` | Bug, regression, unknown failure, flaky behavior. |
| `requesting-code-review` | Ask for review before continuing/merging. |
| `receiving-code-review` | Process review feedback without defensiveness. |
| `verification-before-completion` | Before saying done. |
| `finishing-a-development-branch` | Final branch/PR/merge/keep/discard decision. |
| `writing-skills` | Create or improve skills. |

### 7.2 Matt Pocock skills: engineering clarity

Use to turn unclear work into crisp engineering artifacts.

| Skill | Use when |
|---|---|
| `setup-matt-pocock-skills` | First-time repo setup. |
| `grill-me` | Non-code or general ambiguity. |
| `grill-with-docs` | Code/product task requiring shared context, `CONTEXT.md`, ADRs. |
| `to-prd` | Convert conversation/plan to PRD. |
| `to-issues` | Slice PRD/plan into vertical issues. |
| `tdd` | Implement a vertical slice with tests. |
| `diagnose` | Debug hard issues with reproduce/minimize/hypothesize/instrument/fix/regression-test. |
| `triage` | Classify and route issues. |
| `zoom-out` | Understand architecture/system context. |
| `improve-codebase-architecture` | Refactor toward better boundaries/deep modules. |
| `prototype` | Explore throwaway UI/business-logic direction. |
| `handoff` | Compress context for another session/agent. |
| `caveman` | Ultra-compressed token-saving mode. |
| `write-a-skill` | Create a new skill. |
| `git-guardrails-claude-code` | Apply git safety patterns even if host is not Claude. |
| `setup-pre-commit` | Add quality gates. |
| `migrate-to-shoehorn` | TypeScript assertion migration. |
| `scaffold-exercises` | Course/exercise scaffolding. |

### 7.3 gstack: specialist product/engineering team

Use for role-based scrutiny and shipping.

| Skill | Use when |
|---|---|
| `/office-hours` | Product idea or vague request; find real pain and wedge. |
| `/autoplan` | Run broad plan-review pipeline. |
| `/plan-ceo-review` | Scope, strategy, "10-star" product challenge. |
| `/plan-eng-review` | Architecture, data flow, edge cases, test matrix. |
| `/plan-design-review` | UI/UX plan quality. |
| `/plan-devex-review` | CLI/API/SDK/docs/onboarding planning. |
| `/review` | Staff-level code review. |
| `/investigate` | Root-cause investigation before fix. |
| `/qa` | Browser/product QA, fixes allowed. |
| `/qa-only` | Browser/product QA report only. |
| `/ship` | Tests, PR prep, release readiness. |
| `/land-and-deploy` | Merge/deploy/verify production when approved. |
| `/canary` | Post-deploy monitoring. |
| `/benchmark` | Performance/Core Web Vitals/page-speed risk. |
| `/cso` | OWASP/STRIDE-style security review. |
| `/retro` | Retrospective and learning capture. |
| `/design-consultation` | Research design direction. |
| `/design-shotgun` | Generate several visual directions. |
| `/design-html` | Convert approved mockup to production HTML. |
| `/design-review` | Review implemented UX/UI. |
| `/devex-review` | Review developer experience. |
| `/document-generate` | Create missing docs. |
| `/document-release` | Update docs after change. |
| `/careful`, `/freeze`, `/guard`, `/unfreeze` | Safety/control around destructive operations. |
| `/browse`, `/open-gstack-browser`, `/connect-chrome`, `/setup-browser-cookies` | Browser control and authenticated QA where available. |
| `/setup-deploy` | Configure deployment flow. |
| `/setup-gbrain`, `/sync-gbrain`, `/learn` | Memory/indexing/learning where available. |
| `/pair-agent` | Coordinate with another agent/browser session. |
| `/codex` | Cross-agent Codex-related workflow where available. |

### 7.4 llm-council-plus: deliberation gate

Use for high-stakes decisions, not routine edits.

Council should be used for:

```text
architecture decisions
security-sensitive work
irreversible migrations
large refactors
unclear product strategy
major UI direction choices
multiple plausible root causes
performance tradeoffs
API/data model design
deployment risk
when skills disagree
before high-impact shipping
```

Council should usually be skipped for:

```text
typos
formatting
simple copy changes
obvious one-line fixes
routine tests
low-risk dependency bumps
```

#### Council access precedence

```text
1. MCP tool/server if available.
2. Native skill/API wrapper if installed.
3. REST API or local web app if available.
4. CLI/script wrapper if present.
5. Human-readable council prompt prepared for manual use.
```

#### Council prompt

```markdown
# Council Request

## Task
[One paragraph]

## Context
- Repo:
- Branch:
- Host agent:
- User goal:
- Constraints:
- Files:
- Existing behavior:
- Known failures:

## Options
1. Option A:
2. Option B:
3. Option C:

## Judge by
- Correctness
- Simplicity
- Maintainability
- Security
- Testability
- User impact
- Reversibility
- Implementation risk

## Required output
- Recommended option
- Why
- Rejected alternatives
- Hidden risks
- Required tests
- Stop/go decision
```

---

## 8. Task router

### 8.1 Vague or ambiguous task

```text
using-superpowers
→ brainstorming
→ grill-me OR grill-with-docs
→ /office-hours if product-ish
→ llm-council-plus if high-impact or options conflict
```

TODO:

```markdown
## Ambiguity TODO

- [ ] Restate the task concretely.
- [ ] Identify missing requirements.
- [ ] Identify hidden assumptions.
- [ ] Define success criteria.
- [ ] Define non-goals.
- [ ] Ask only blocking questions.
- [ ] Infer safely when blocked, and mark assumptions.
- [ ] Update CONTEXT.md/ADRs if appropriate.
```

### 8.2 New feature

```text
using-superpowers
→ brainstorming
→ grill-with-docs
→ /office-hours
→ /autoplan
→ /plan-ceo-review
→ /plan-eng-review
→ /plan-design-review if UI/UX
→ /plan-devex-review if developer-facing
→ llm-council-plus if high-impact
→ to-prd
→ to-issues
→ using-git-worktrees
→ writing-plans
→ subagent-driven-development OR executing-plans
→ test-driven-development OR tdd
→ /review
→ requesting-code-review
→ receiving-code-review if needed
→ /qa
→ verification-before-completion
→ /document-release
→ /ship
```

TODO:

```markdown
## Feature TODO

### Intake
- [ ] Host/capability matrix complete.
- [ ] Relevant skills loaded or fallback declared.
- [ ] User, pain, success metric, constraints defined.

### Product
- [ ] Product wedge reviewed.
- [ ] Scope mode chosen: expand / selective expand / hold / reduce.
- [ ] Non-goals documented.

### Architecture
- [ ] Current system understood.
- [ ] Data flow / state machine / failure paths documented.
- [ ] Test matrix defined.

### Council
- [ ] Council run or explicitly skipped as low-risk.
- [ ] Plan revised if council found material flaws.

### Execution
- [ ] Worktree/branch prepared.
- [ ] PRD/issues/tasks written.
- [ ] TDD loop used.
- [ ] Review and QA completed.
- [ ] Verification evidence captured.
```

### 8.3 Bug, regression, or flaky behavior

```text
using-superpowers
→ systematic-debugging
→ diagnose
→ /investigate
→ zoom-out if architecture unclear
→ llm-council-plus if root cause disputed
→ test-driven-development OR tdd
→ /review
→ /qa OR /qa-only
→ verification-before-completion
```

TODO:

```markdown
## Bug TODO

- [ ] Reproduce bug.
- [ ] Minimize reproduction.
- [ ] Define expected vs actual behavior.
- [ ] Trace data flow.
- [ ] Instrument if needed.
- [ ] Form hypotheses.
- [ ] Test hypotheses.
- [ ] Write failing regression test.
- [ ] Fix minimally.
- [ ] Verify test fails before fix and passes after fix.
- [ ] Re-run relevant suite.
- [ ] Capture evidence.
```

Hard rule:

```text
No root cause, no fix.
No regression test, no completion.
```

### 8.4 Architecture cleanup/refactor

```text
using-superpowers
→ zoom-out
→ improve-codebase-architecture
→ /plan-eng-review
→ llm-council-plus
→ to-prd
→ to-issues
→ using-git-worktrees
→ writing-plans
→ test-driven-development OR tdd
→ /review
→ verification-before-completion
```

TODO:

```markdown
## Architecture TODO

- [ ] Current architecture mapped.
- [ ] Coupling/duplication/boundary issues identified.
- [ ] Refactor goal stated in behavior-preserving terms.
- [ ] Council critique obtained unless low-risk.
- [ ] Characterization tests added.
- [ ] Smallest reversible change chosen.
- [ ] No unrelated edits.
```

### 8.5 UI/UX/frontend polish

```text
using-superpowers
→ brainstorming
→ grill-with-docs
→ /plan-design-review
→ /design-consultation if direction unclear
→ /design-shotgun if alternatives useful
→ /design-html if converting approved mockup
→ /design-review
→ /qa
→ /benchmark if performance-sensitive
```

TODO:

```markdown
## Design TODO

- [ ] Target user and desired feeling identified.
- [ ] Existing design system inspected.
- [ ] Visual direction chosen.
- [ ] Accessibility considered.
- [ ] Before/after screenshots captured if browser available.
- [ ] UX reviewed.
- [ ] Browser QA completed.
```

### 8.6 Developer experience, APIs, SDKs, CLI, docs

```text
using-superpowers
→ grill-with-docs
→ /plan-devex-review
→ /devex-review
→ to-prd
→ to-issues
→ tdd
→ /document-generate OR /document-release
→ /qa if browser flow exists
```

TODO:

```markdown
## DX TODO

- [ ] Developer persona identified.
- [ ] First successful action defined.
- [ ] Setup flow tested or reason documented.
- [ ] API/CLI/docs friction listed.
- [ ] Examples verified.
- [ ] Docs updated.
```

### 8.7 Security-sensitive work

```text
using-superpowers
→ careful / guard / freeze if available
→ git-guardrails-claude-code or equivalent
→ /cso
→ llm-council-plus
→ /review
→ verification-before-completion
```

Security-sensitive triggers:

```text
auth
permissions
payments
PII
secrets
tokens
database access
file upload
admin flows
network calls
browser automation
deployment config
sandboxing
prompt injection surfaces
```

TODO:

```markdown
## Security TODO

- [ ] Assets, actors, trust boundaries listed.
- [ ] Authn/authz checked.
- [ ] Input validation checked.
- [ ] Secrets checked.
- [ ] Injection paths checked.
- [ ] Unsafe file/network/browser paths checked.
- [ ] Council critique obtained for high-severity items.
- [ ] Exploit/regression test added where possible.
```

### 8.8 Testing/QA/browser verification

```text
using-superpowers
→ test-driven-development OR tdd
→ /qa-only if report only
→ /qa if fixes allowed
→ /benchmark if performance-sensitive
→ verification-before-completion
```

TODO:

```markdown
## QA TODO

- [ ] Critical flows listed.
- [ ] Expected results defined.
- [ ] Browser/devtools/logs/screenshots used if available.
- [ ] Bugs recorded by severity.
- [ ] Fixes limited to verified bugs.
- [ ] Regression tests added.
- [ ] Exact failing flow re-run.
```

### 8.9 Docs-only or docs-after-code

```text
using-superpowers
→ grill-with-docs
→ /document-generate if missing docs
→ /document-release if code changed
→ /devex-review if onboarding docs
```

TODO:

```markdown
## Docs TODO

- [ ] Doc type chosen: tutorial / how-to / reference / explanation.
- [ ] Code inspected before writing.
- [ ] Examples tested where possible.
- [ ] README/ARCHITECTURE/CONTRIBUTING/AGENTS-style files updated if affected.
```

### 8.10 Release/deploy/PR finalization

```text
using-superpowers
→ finishing-a-development-branch
→ /ship
→ /land-and-deploy if approved
→ /canary
→ /retro
```

TODO:

```markdown
## Release TODO

- [ ] Branch clean.
- [ ] Tests pass.
- [ ] Review complete.
- [ ] QA complete.
- [ ] Security/perf/doc gates complete as applicable.
- [ ] Verification evidence captured.
- [ ] PR/release notes prepared.
- [ ] Deploy only if approved.
- [ ] Canary/post-deploy checks complete.
- [ ] Retro captured if non-trivial.
```

---

## 9. Master TODO ledger

Maintain a living ledger. Use the host's TODO tool if available; otherwise maintain this Markdown.

```markdown
# Orchestrion TODO Ledger

## Task
- Human request:
- Interpreted goal:
- Host:
- Repo:
- Branch/worktree:
- Risk level: low / medium / high / critical

## Capabilities
- Skills:
- MCP:
- Terminal:
- Browser:
- Git:
- Council:

## Assumptions
- [ ] ...

## Skill gates
- [ ] using-superpowers: loaded / fallback / unavailable
- [ ] ambiguity reducer:
- [ ] product gate:
- [ ] engineering gate:
- [ ] council gate:
- [ ] TDD/debug gate:
- [ ] review gate:
- [ ] QA gate:
- [ ] security gate:
- [ ] verification gate:
- [ ] docs gate:
- [ ] ship/handoff gate:

## Work items
| ID | State | Task | Skill/source | Evidence | Blocker |
|---|---|---|---|---|---|
| T1 | todo |  |  |  |  |

## Evidence
- Tests:
- Logs:
- Screenshots:
- URLs:
- Commits:
- PR:
- Council result:
- Review result:
```

State values:

```text
todo
doing
blocked
needs-human
needs-council
needs-review
needs-qa
done
discarded
```

---

## 10. Bootstrap and installation appendix

Use this only when the human explicitly wants installation or when missing skills block safe work.

### 10.1 gstack

Install only a reviewed immutable revision. Replace the placeholder with the
full commit ID recorded in the review receipt; do not use a branch name:

```bash
GSTACK_COMMIT='REPLACE_WITH_FULL_REVIEWED_GSTACK_COMMIT'
test "${#GSTACK_COMMIT}" -eq 40
git init ~/gstack
git -C ~/gstack remote add origin https://github.com/garrytan/gstack.git
git -C ~/gstack fetch --depth 1 origin "$GSTACK_COMMIT"
git -C ~/gstack checkout --detach FETCH_HEAD
test "$(git -C ~/gstack rev-parse HEAD)" = "$GSTACK_COMMIT"
cd ~/gstack
./setup
```

Target known host:

```bash
./setup --host codex
./setup --host opencode
./setup --host cursor
./setup --host factory
./setup --host slate
./setup --host kiro
./setup --host hermes
./setup --host gbrain
```

If OpenClaw delegates to another coding agent, install gstack in the spawned coding agent and add routing instructions to the parent agent's project instructions.

### 10.2 Superpowers

If native plugin marketplace exists, search for `superpowers`.

Known Claude-style commands:

```text
/plugin install superpowers@claude-plugins-official
/plugin marketplace add obra/superpowers-marketplace
/plugin install superpowers@superpowers-marketplace
```

For other agents, prefer their plugin/extension marketplace or read/import the relevant `skills/*/SKILL.md` files.

### 10.3 Matt Pocock skills

Do not execute `@latest`. Download a reviewed, exact package version, verify its
published integrity and the SHA-256 recorded in the review receipt, inspect its
contents, then execute the verified local tarball. If no reviewed version and
digest are available, stop and ask the human to approve a review first.

Then run the setup skill if available:

```text
/setup-matt-pocock-skills
```

If slash commands are unavailable, read/import the installed skill Markdown files and apply them as documented methodologies.

### 10.4 llm-council-plus

Local app: replace the placeholder with the full reviewed commit ID and verify
the detached checkout before installing dependencies. Commit dependency locks
alongside the review receipt; do not install from a moving branch.

```bash
COUNCIL_COMMIT='REPLACE_WITH_FULL_REVIEWED_COUNCIL_COMMIT'
test "${#COUNCIL_COMMIT}" -eq 40
git init llm-council-plus
git -C llm-council-plus remote add origin https://github.com/jacob-bd/llm-council-plus.git
git -C llm-council-plus fetch --depth 1 origin "$COUNCIL_COMMIT"
git -C llm-council-plus checkout --detach FETCH_HEAD
test "$(git -C llm-council-plus rev-parse HEAD)" = "$COUNCIL_COMMIT"
cd llm-council-plus
uv sync
cd frontend && npm ci
cd ..
./start.sh
```

MCP mode where supported (use `uv pip install -e .` if pip is wrapped, or activate the project venv first):

```bash
uv pip install -e .
# host-specific MCP registration goes here
```

Claude-style MCP registration example:

```bash
claude mcp add llm-council python -m llm_council_mcp
```

Direct REST/API skill mode where supported:

```bash
mkdir -p ~/.claude/skills/llm-council-api
install -m 0644 skills/llm-council-api/SKILL.md \
  ~/.claude/skills/llm-council-api/SKILL.md
```

For non-Claude hosts, adapt this as:
1. make the Council API reachable,
2. expose it through MCP if the host supports MCP,
3. otherwise document the REST endpoints/tool wrapper in the host's project instructions.

---

## 11. Output rules

When reporting back to the human:

```text
1. Say what was done.
2. Say which skills were actually loaded or which fallbacks were used.
3. Show the TODO ledger state.
4. Show verification evidence.
5. State remaining risks honestly.
6. Do not dump unnecessary ceremony unless useful.
```

Minimal completion format:

```markdown
## Done

### Skills used
- ...

### Changes
- ...

### Verification
- ...

### Remaining risks
- ...

### Next action
- ...
```

---

## 12. Final mnemonic

```text
Discover the room.
Load the right instruments.
Question the brief.
Plan the route.
Ask the council when the bridge is expensive.
Cut one slice.
Test the slice.
Invite review.
Walk the product in a browser.
Verify before victory.
Document the map.
Ship only with smoke cleared.
```
