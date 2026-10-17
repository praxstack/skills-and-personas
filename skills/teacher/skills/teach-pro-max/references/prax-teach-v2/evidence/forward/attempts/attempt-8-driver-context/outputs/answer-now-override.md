# Answer-now override

A **lost update** happens when two operations read the same old value, both calculate a change, and one write silently overwrites the other.

Example: a counter starts at 10. A reads 10 and writes 11; B also read 10 and writes 12. The result is 12 instead of 13—A’s update was lost.

Common preventions include atomic updates, locks or serializable transactions, and version checks such as compare-and-swap.
