# Accessible interaction fallback

This is an ephemeral, keyboard-only host-chat interaction; nothing is saved. No separately approved interaction runtime is available, so there are no custom buttons or scripts. The text version below is also the complete static fallback.

Motion setting: none. State changes arrive as new text messages, with no animation or motion-dependent information. The host UI’s keyboard focus, visible-focus, reduced-motion, and assistive-technology behavior remains unverified.

Keyboard actions, in reading order:

1. Focus the host chat composer using the host’s keyboard navigation.
2. Type one action, then use the host’s keyboard command for Send.
3. `SUBMIT current=<value>; projected=<value>; decision=<resize or no resize>; reason=<one sentence>` — submit your attempt.
4. `HINT` — receive only the next-needed hint.
5. `REPEAT` — repeat this state unchanged.
6. `RESET` — restart this round with no hints.
7. `ANSWER NOW` — receive the direct solution.

## Practice state: Boundary test

Use:

\[
\text{load factor } \alpha=\frac{\text{number of stored entries}}{\text{number of buckets}}
\]

Resize only when the projected load factor is **greater than** `0.75`.

Static bucket data:

- Bucket 0: `Ada`
- Bucket 1: empty
- Bucket 2: `Bea`
- Bucket 3: `Cai`
- Bucket 4: empty
- Bucket 5: `Dev`
- Bucket 6: `Eli`
- Bucket 7: empty
- Proposed insertion: `Fox`
- The insertion succeeds and adds exactly one entry.

What are the current load factor, the projected load factor after inserting `Fox`, and the correct resize decision?

Reply with:

`SUBMIT current=<value>; projected=<value>; decision=<resize or no resize>; reason=<one sentence>`
