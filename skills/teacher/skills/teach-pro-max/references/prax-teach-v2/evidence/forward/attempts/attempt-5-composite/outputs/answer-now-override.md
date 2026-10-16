# Answer-now override

A **lost update** is a concurrency bug where two operations read the same old value, both modify it, and the later write overwrites the earlier one.

Example: a balance is ₹100. One operation adds ₹10 and writes ₹110; another, having also read ₹100, subtracts ₹20 and writes ₹80. The correct result is ₹90, but the ₹10 update was lost.

Common prevention methods include atomic updates, locks/serializable transactions, or version checks with retries.
