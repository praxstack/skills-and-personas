# Accessible interaction fallback

## Hash-table load-factor practice — Round 1

This interaction runs entirely through host chat, with no custom artifact controls or scripts. It uses typed responses only; there is no animation, timed change, hover-only information, or color-only meaning. The host UI’s keyboard navigation, focus behavior, reduced-motion behavior, and assistive-technology behavior remain unverified.

### Complete static fallback

Load factor is:

`load factor = stored entries ÷ bucket count`

Resize rule: immediately after a successful insertion, resize when the load factor is greater than or equal to `0.75`.

- Starting state: 5 entries, 8 buckets
- After insertion 1: 6 entries, 8 buckets
- After insertion 2: 7 entries, 8 buckets
- Both insertions succeed; there are no deletions.
- Stop at the first resize trigger. You do not need to predict the resized capacity.

| State | Entries | Buckets | Load factor | Resize triggered? |
|---|---:|---:|---|---|
| Start | 5 | 8 | Your calculation | Yes or no |
| After insertion 1 | 6 | 8 | Your calculation | Yes or no |
| After insertion 2 | 7 | 8 | Your calculation | Yes or no |

### Keyboard actions

1. **Action 1 — Calculate:** Work out each load factor as a fraction or decimal.
2. **Action 2 — Submit:** Type `Attempt: start = …; insertion 1 = …; insertion 2 = …; first resize = … because …`
3. **Action 3 — Request help:** Type `Hint 1`.
4. **Action 4 — Say you are unsure:** Type `I don’t know`.
5. **Action 5 — Request the solution:** Type `Answer now`.
6. **Action 6 — Reset:** Type `Restart`.

What are the three load factors, and which insertion first triggers resizing?
