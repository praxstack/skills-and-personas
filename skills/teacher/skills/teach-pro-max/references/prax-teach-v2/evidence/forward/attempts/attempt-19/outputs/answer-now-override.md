# Lost-update answer

A **lost update** happens when two operations read the same old value, then write back their changes; the later write overwrites the earlier one.

Example:

- Both read balance = 10.
- A adds 5 and writes 15.
- B subtracts 3 and writes 7.
- Final balance is 7, so A’s update was lost.

Transactions, row locks, or version checks prevent this.
