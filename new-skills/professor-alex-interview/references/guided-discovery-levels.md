# Guided Discovery: 5-Level Progression

Advance one level only when the candidate demonstrates understanding at the current level.

---

## Level 1 — Clarifying Questions (about the candidate's approach)

Goal: make the candidate articulate what they currently think.

**Example prompts:**
- "What's your current approach to this problem?"
- "What inputs and outputs have you identified?"
- "Walk me through your first instinct."
- "What does the problem seem to be asking for, in your own words?"
- "Have you seen a similar problem before? What pattern does this feel like?"

**Advance when:** candidate articulates a concrete attempt, even if wrong.
**Stay when:** candidate says "I don't know" or gives a vague answer.

---

## Level 2 — Questions That Reveal the Solution Direction

Goal: nudge toward the right category of solution without naming it.

**Example prompts:**
- "What happens if the array were sorted? What does that unlock?"
- "You have n elements and need to find pairs — what's the brute force? What's the issue with brute force here?"
- "Is there any ordering we can exploit?"
- "What if we processed the input in one pass — what state would we need to carry?"
- "Does the structure of the data suggest any specific algorithm family?"

**Advance when:** candidate identifies the solution direction (sort + two pointers, hash map, BFS, DP, etc.).
**Stay when:** candidate is still guessing without constraint analysis.

---

## Level 3 — Methodological Hints about Data Structures / Algorithms

Goal: name the data structure or algorithm family without giving the solution.

**Example prompts:**
- "Think about what data structure gives you O(1) lookup and ordered iteration."
- "This looks like a sliding-window problem — does that ring a bell?"
- "Consider a priority queue here. What would the keys be?"
- "This has overlapping subproblems — what technique does that point to?"
- "You're asking 'is there a pair that sums to X' — what data structure makes that O(n) instead of O(n²)?"

**Advance when:** candidate names the structure/algorithm and describes how to apply it.
**Stay when:** candidate names the structure but can't explain how it applies here.

---

## Level 4 — Implementation Guidance with Pseudocode

Goal: scaffold the implementation without writing the final code.

**Example prompts:**
- "Let's sketch the algorithm step by step. Start with: initialize what?"
- "The main loop processes each element — what do you do with it on each iteration?"
- "Pseudocode it. Don't worry about Java/Python syntax yet."
- "Your outer loop iterates through X. Your inner condition is Y. What's the update step?"
- "Walk me through one iteration on this small example input."

**Advance when:** candidate implements correctly or makes a localized mistake.
**Stay when:** candidate is stuck on the overall structure.

---

## Level 5 — Complete Solution with Explanation

Goal: provide the complete answer, but contextualize it so learning still happens.

**Format:**
1. Complete implementation with clean code
2. Approach explanation — 2-3 key insights that made this solution work
3. Time / space complexity with derivation
4. Two follow-up variations ("What if the input were streaming? What if k were very large?")
5. One focused resource recommendation (not a reading list)

**After Level 5:** ask the candidate to walk through the solution on a new example input, to verify understanding.

---

## Transition Signals

### Moving up a level (genuine progress)
- Candidate answers the current prompt thoughtfully
- Candidate's next question is more specific than their last
- Candidate self-corrects when you point out an edge case

### Staying at current level (not ready)
- Guessing without reasoning
- Can't articulate what's confusing
- Repeats the same wrong approach without analysis

### Dropping a level (lost them)
- Candidate is clearly overwhelmed
- Answers show fundamental confusion about the previous level's concept
- Return to the simpler level and re-establish

---

## When to switch to Solution Mode from guided discovery

- Candidate explicitly triggers `SOLUTION:`
- Candidate explicitly states time pressure with a date (interview in 1-2 days)
- Candidate has made genuine attempts at Level 4 but is still blocked → Level 5 (which is Solution Mode for this problem)
- Session time is limited and you want to cover more problems → switch with the candidate's agreement

Never skip guided discovery unless the candidate has demonstrated they already understand the prerequisites.

---

## Example Session Progression

```
Candidate: "How do I solve two sum?"

L1: "What's your current approach?"
Candidate: "Two nested loops, check every pair."

L2: "That works — O(n²). What if I told you we can do it in O(n)?
     What does the input structure suggest?"
Candidate: "Maybe sorting first? Or some kind of lookup?"

L3: "Lookup is the right instinct. What data structure gives you
     O(1) lookup by key?"
Candidate: "Hash map. So I'd store numbers as I go?"

L4: "Yes. Walk me through one pass. What do you look up, and what
     do you insert?"
Candidate: "For each num, check if (target - num) is in the map.
           If yes, return. Else, insert num."

L5 (not needed — candidate has the solution):
"Perfect. Implement it. Then tell me the time and space complexity,
 and what happens if there are duplicate values."
```

The candidate solved it themselves. That's the goal.
