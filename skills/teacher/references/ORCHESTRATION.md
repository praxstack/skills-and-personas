# Coordinating other agents

Bring in other agents when the host supports it and it makes the teaching better. The learner always talks to one teacher: you.

## When it helps

| Situation | Hand off | Keep |
| --- | --- | --- |
| a heavy visual or video takes minutes to build | building, rendering, QA | the conversation with the learner |
| the lesson's facts or model need an independent check | a checker that sees the model and claims, not your reasoning | the decision on what to fix |
| the explanation isn't landing and you want real alternatives | two drafts from different angles | choosing and teaching |
| a subject needs sources you haven't read | research with citations | judging the sources |
| practice needs fresh problems | an examiner who hasn't seen the lesson's examples | checking the answers |

## When it doesn't

- A quick question, a short lesson, or a simple still: do it yourself.
- When the host would ask the learner to approve every agent: the interruptions cost more than they save.
- Never to look busy, never to split one explanation across voices.

## Find out what the host offers

Look at your own tool list, in this order:

1. **A delegation tool** (an agent, task, subagent or delegate tool). Use it, in the background if it can run there.
2. **A shell plus a host CLI with a non-interactive mode.** Start a helper as a separate process with its own working folder, write its output to a file, and read the file.
3. **Neither.** Do the work yourself, one piece at a time, and tell the learner what's happening while they wait.

Host notes (check `--help`; these change):

| Host | Delegation | Non-interactive helper |
| --- | --- | --- |
| Claude Code | Agent tool with subagent types, background runs, worktree isolation; multi-agent workflows only when the user explicitly opts in | `claude -p "..."`; in claude.ai cloud sessions, sibling sessions can be created with the remote session tools |
| Codex | use a delegation tool if your build exposes one | `codex exec "..."` |
| OpenCode | subagents (agents configured with `mode: subagent`), called through its task tool | `opencode run "..."` |
| Gemini CLI | use a delegation tool if present | `gemini -p "..."` |
| Pi | none built in; extensions may add one | its print mode, if `pi --help` lists one |
| Hermes | its delegation tool, if present | check `--help` |
| anything else | look for a tool that starts an agent | look for a CLI with a prompt flag |

## Role cards

Give every helper a card. A helper knows nothing but the card and the files you point it to.

```
ROLE: builder (concept animation)
OUTCOME: neuron.mp4 + neuron.vtt + contact sheet, 1280x720, about 28 s, showing weigh, add, squash
INPUTS: skills/concept-animation/assets/examples/neuron.anim.js, skills/concept-animation/SKILL.md
DONE WHEN: check_video.py passes and you've looked at the contact sheet; report what you checked
DON'T: change the model or the captions' claims; publish anything; message the learner
RETURN: paths, the check output, and anything you couldn't do
```

Other cards worth keeping:

- **checker**: given the lesson file and its claims, re-derive every number from the model or a source, run the lesson test, list disagreements. Gets the claims and the model, not your explanation, so it can't just agree.
- **explainer**: given the concept, the learner's level, and the explanations already tried (from the journal), draft one explanation that changes one thing (example, representation, granularity, analogy or direction). Two explainers with different angles give you a real choice.
- **examiner**: given only the concept and the depth rung, write fresh-case questions with worked answers. Never sees the lesson's examples.
- **researcher**: find two or three reliable sources for a claim, with links and the exact passages.

## When a helper vanishes

Containers restart and background helpers die with them, silently. Ask helpers to write each finished piece to disk as soon as it passes its checks, so a restart loses at most one piece. If one stops reporting, look at what it left on disk, run its checks on that, and start a fresh helper with a card that says what's already done. Don't wait on a helper that can't answer.

## Verify what comes back

Treat a helper's report as a claim. Open the file it says it made, re-run its check, look at the picture. If it says a test passed, run the test. Then teach from what you verified, and tell the learner about anything you couldn't check.
