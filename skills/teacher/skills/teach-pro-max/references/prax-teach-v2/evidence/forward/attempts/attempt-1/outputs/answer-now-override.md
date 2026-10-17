# Answer now override

A **lost update** is a concurrency bug where two operations read the same old value, then one write overwrites the other.

Example: a balance is ₹100. Two requests both read ₹100; one adds ₹20 and writes ₹120, while the other adds ₹10 and writes ₹110. The correct result is ₹130, but it ends at ₹110—the ₹20 update was lost.
