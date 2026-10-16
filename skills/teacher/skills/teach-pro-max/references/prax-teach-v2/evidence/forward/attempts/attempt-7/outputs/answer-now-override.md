# Answer-now override

A **lost update** happens when two operations read the same old value, each computes a change, and the later write overwrites the earlier one.

Example: a counter starts at 10. Alice and Bob both read 10. Alice writes 11, then Bob also writes 11. The correct result was 12, but Alice’s update was lost.
