# Answer-now override

A **lost update** occurs when two concurrent operations read the same old value, modify it independently, and the later write overwrites the earlier one—silently losing one change.

Example: both read `100`; A writes `110`, then B writes `80`. A’s `+10` update is lost.
