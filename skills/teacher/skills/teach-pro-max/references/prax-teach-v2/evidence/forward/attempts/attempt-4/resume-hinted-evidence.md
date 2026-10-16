# Resume hinted evidence

Using the supplied saved-state summary for `/tmp/prax-forward-resume-course`: `prefix-application-1` scored `1.0` on application at hint level `4`—the strongest hint. That is a correct but scaffolded success, not evidence of independent mastery. No other learner history was supplied, and this observation remains unchanged and version-linked.

Fresh unassisted check: Assume an ordinary B-tree index on `(customer_id, status, created_at)` and ignore database-specific skip-scan optimizations. For each query, state whether the index can narrow the search using a contiguous leftmost prefix, and name the columns in that prefix:

1. `WHERE customer_id = 42`
2. `WHERE customer_id = 42 AND status = 'paid'`
3. `WHERE status = 'paid'`
4. `WHERE customer_id = 42 AND created_at >= '2026-08-01'`

What is your classification and reasoning?
