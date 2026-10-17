# Lost update — direct answer

A **lost update** happens when two concurrent operations read the same old value, then both write changes; the later write overwrites the earlier one.

Example: both read a balance of $100. One adds $10 and writes $110; the other subtracts $20 and writes $80. The first update is lost.
