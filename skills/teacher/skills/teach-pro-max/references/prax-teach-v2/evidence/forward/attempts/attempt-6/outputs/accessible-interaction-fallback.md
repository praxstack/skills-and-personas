# Accessible interaction fallback

Hash-table load-factor practice — Round 1

This practice works entirely by keyboard. Nothing moves, auto-advances, or requires color, a pointer, or JavaScript. The text below is also the complete static fallback.

Reference: load factor \( \alpha = \frac{\text{entries}}{\text{capacity}} \)

Current state:

- Capacity: 8 slots
- Entries: 5
- Resize rule: resize when \( \alpha \ge 0.75 \)
- Operation: insert one new key into an empty slot

Reply with:

`alpha = ___; resize = yes/no; because ___`

You can also type `hint`, `I don’t know`, or `Answer now`.

After the insertion, what is the load factor, and should the table resize?
