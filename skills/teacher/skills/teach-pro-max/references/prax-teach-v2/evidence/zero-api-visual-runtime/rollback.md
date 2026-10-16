# Rollback: zero-api visual runtime

The reviewed archive is bound to commit `acb46a33008935743b8811485d554f8b3ca915d1` and is preserved at `outputs/prax-teach-v2-candidate.zip` with SHA-256 `0d35bcd98e11091ab00f13bee94fb4463e7357793f5830dcb3b72ac3a3a6ce3b`.

## Restore the previous candidate

1. Preserve the current evidence and archive receipt before changing the checkout.
2. From the candidate repository, create a recovery branch or tag at the current commit.
3. Restore the prior reviewed candidate with `git switch --detach 8c26440a0402c88c366d68d680aef2b3fe20fc7c` or create a named branch from that commit.
4. Re-run the validator and review-payload check before treating the old candidate as usable.

## Remove only the runtime from a working tree

1. Create a recovery branch or copy of the current working tree.
2. Remove `runtime/prax-visual-lab/`, the four `examples/visual-lab/` lesson fixtures, and `integrations/formal/lean/adapter.py` only if the owner has explicitly approved that scope.
3. Revert the corresponding OpenSpec change or leave it archived as historical evidence; do not delete `.agent/` or `openspec/` records as part of runtime rollback.
4. Run the full verifier and update the tracker; a rollback is not complete while receipts still claim the runtime is present.

Rollback is a controlled change, not an automatic cleanup command. No destructive command is executed by this receipt.
