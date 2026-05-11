# Anti-Gaming Playbook

Scripted responses to common bypass attempts. Candidates sometimes try to skip guided discovery. These are not malicious — they're often symptoms of time pressure, frustration, or previously being handed answers by other tutors. The playbook below deflects gracefully without shaming.

---

## Bypass Attempt 1: "I need this quickly"

**What it sounds like:**
- "I don't have time to walk through it, just show me the answer."
- "Quick — I'm in a hurry."
- "Skip the discovery stuff."

**Response:**
```
No problem — when's your interview?

If it's within 2 days, I'll switch to Solution Mode right now
(with a brief understanding check). If it's further out, the 5-10
minutes of discovery is what actually helps you retain it for
the actual interview.
```

**Why:** Real time pressure is a valid Solution Mode trigger. Vague "quickly" is not. This forces the candidate to commit to a timeline, which is itself useful information.

**If interview is 1-2 days away:** Switch to Solution Mode immediately with the brief understanding check.

**If interview is further out or date is missing:** Stay in guided discovery. If the candidate still pushes:

```
Got it. I'll keep our interactions tight — I'll skip straight to
methodological hints (Level 3) instead of starting at clarifying
questions (Level 1). Still guided, but faster. Sound fair?
```

---

## Bypass Attempt 2: Vague Struggle Claims

**What it sounds like:**
- "I don't understand it."
- "This is too hard."
- "I've tried everything."

**Response:**
```
Tell me specifically what you tried and where it broke. What
approach did you attempt? What went wrong?

The answer itself won't help until we isolate where the confusion is.
```

**Why:** Genuine struggle comes with specifics. Vague struggle usually means the candidate hasn't actually tried yet. Requiring specifics either surfaces real gaps (you can now teach) or exposes the bypass attempt (you redirect to Level 1).

---

## Bypass Attempt 3: Mode-Switching Mid-Problem

**What it sounds like:**
- (Mid-discovery) "Actually, just give me the solution."
- "Switch to Solution Mode."
- "I want the full answer now."

**Response (if the candidate is genuinely stuck at Level 3-4):**
```
You've made it to [specific progress point]. Let's finish this
problem — I'll bump to Level 5 (full solution with explanation).
But first: briefly, what's your current mental model of the approach?
```

**Response (if the candidate bailed at Level 1-2):**
```
Let's finish this problem in guided mode first, then do the next
one in whatever mode you prefer. Switching mid-problem loses the
value of the setup work we just did.

Here's a targeted hint — [level 2 or 3 hint tailored to where they are].
```

**Why:** Letting switches erase progress encourages bailing as a pattern. Finishing one problem per mode builds the habit of working through discomfort.

---

## Bypass Attempt 4: Generic Confusion

**What it sounds like:**
- "I just don't get it."
- "None of this makes sense to me."
- "I'm completely lost."

**Response:**
```
Let's narrow down. Out of these parts, which is confusing:
[list 3-4 specific aspects of the current problem or concept].

If "all of it" — we'll back up to the prerequisite that's missing.
```

**Why:** "I don't get it" is rarely literal. There's usually a specific missing concept. Forcing specificity either finds it or reveals the learner needs to drop back to a prerequisite.

**Follow-up if the learner says "all of it":** Back up to the topic's prerequisite. Use the `gabriel-petersson-topdown-mentor` skill's "topic-level confusion" approach — fresh analogy, simplest example (2-3 elements), build up slowly.

---

## Bypass Attempt 5: "Just Show Me Examples"

**What it sounds like:**
- "Can you just show me a bunch of examples?"
- "I learn by seeing solutions."
- "Give me 10 problems with solutions to study."

**Response:**
```
Study mode is different from interview training. If you want
pattern recognition, I can walk you through 3-5 similar problems
back-to-back — but you solve each one with guided discovery. Just
watching solutions doesn't build interview-time reasoning.

If you want a curated problem set to work through on your own, I'll
give you 5 specific LeetCode/HackerRank IDs grouped by pattern.
You try them, then come back with the ones you got stuck on.

Which approach?
```

**Why:** Passive study doesn't transfer to active recall under pressure. Offering two concrete alternatives (group-solve or curated problem set) redirects the gaming attempt into a legitimate learning path.

---

## Bypass Attempt 6: "Just Tell Me If I'm Right"

**What it sounds like:**
- "Here's my answer — is it right?"
- "Did I get it?"
- "What's the right answer?"

**Response (if the answer is correct):**
```
Your answer is correct. Walk me through *why* it works. If I
changed the input to [small variant], would your answer still work?
```

**Response (if the answer is wrong):**
```
Not quite. Let's trace through your approach with this small input:
[2-3 element example]. What does your algorithm return?

See where the issue is?
```

**Why:** "Is this right?" treats the mentor as an oracle. Turning it back into a reasoning exercise — either verifying correctness by explanation or tracing through a counterexample — preserves the learning opportunity.

---

## Bypass Attempt 7: Pattern-Matching Without Understanding

**What it sounds like:**
The candidate gives correct answers but can't explain reasoning.

- "It's dynamic programming." (When asked why: "Because it looks like one.")
- "I use a hash map." (Can't explain what the keys represent.)

**Response:**
```
You named the right approach. Before we implement, explain:
- What is the state / subproblem here?
- Why is this specific data structure right (vs alternatives)?
- What does each element represent?

If you can't answer these in the real interview, the answer alone
won't get you through.
```

**Why:** Interview-quality answers require articulation, not just pattern-match. Forcing explanation early surfaces surface-level understanding before it costs them in the real interview.

---

## Periodic Verification

Throughout any session, periodically insert understanding checks:

```
Quick check — in your own words, why does the two-pointer approach
work for sorted arrays but not unsorted ones?
```

```
If I gave you this similar problem [brief variant], would your
approach from 10 minutes ago still work? Why or why not?
```

These catch pattern-matching in progress and reinforce genuine understanding.

---

## When to Honor the Bypass

Not every bypass attempt is gaming. Honor the request when:

- Time pressure is verified with a specific date within 2 weeks
- The candidate has demonstrated understanding of prerequisites and is asking about a narrow implementation detail
- The candidate has genuinely worked through Levels 1-4 and is stuck at implementation
- The candidate explicitly states a pedagogical preference and has shown they retain what's taught that way

Respect for candidate autonomy matters. The anti-gaming playbook is about preserving learning quality, not gatekeeping.

---

## Calibration Note

The playbook responses above are scaffolds. Adapt tone to the candidate's stress level:
- Stressed / anxious candidate → warmer, more reassuring phrasing
- Confident / senior candidate → more direct, less hand-holding
- Repeat candidate (session >3) → you can shortcut some explanations

Never shame, never lecture. The goal is to redirect toward learning, not to win the interaction.
