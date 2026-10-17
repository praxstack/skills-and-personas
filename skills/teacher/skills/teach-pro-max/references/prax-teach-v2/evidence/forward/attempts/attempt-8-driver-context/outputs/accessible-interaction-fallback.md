# Hash-table load-factor lab

This practice runs through host chat with no custom controls or scripts. Use the message field as the keyboard input. The activity has no animation, timer, flashing, or auto-advance; every round appears as a complete static text state. Host-UI keyboard navigation, focus, reduced-motion behavior, and assistive-technology behavior remain unverified.

**Action 1 — Read the rule**

For separate chaining:

\[
\text{load factor } \alpha=\frac{\text{stored key-value pairs}}{\text{buckets}}
\]

Every item in a chain counts. This table resizes before an insertion only when the projected load factor is **greater than 0.75**; equality is allowed.

**Action 2 — Inspect Round 1**

- Bucket count: 8
- Bucket 0: Ada, Linus
- Bucket 1: empty
- Bucket 2: Grace
- Bucket 3: empty
- Bucket 4: empty
- Bucket 5: Edsger, Barbara
- Bucket 6: empty
- Bucket 7: empty
- Pending insertion: Ken hashes to bucket 5

**Action 3 — Choose support if needed**

Type `HINT` for one cue, `RESET R1` to repeat the state, or `ANSWER NOW` for the solution.

**Action 4 — Submit your attempt**

Reply:

`R1 | current α = ___ | projected α = ___ | resize = yes/no | reason = ___`
