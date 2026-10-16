# Capability-adaptive execution

The skill states roles, evidence, authorization, and stop conditions—not `codex exec`, `claude -p`, or any other provider command. At each iteration an agent inspects its exposed tools, separates capability from authorization, uses the smallest bounded delegation only when useful, and keeps the primary agent responsible for integration and claims. If no approved delegate exists, it continues as one agent. External calls default to zero and are bounded by task, quota, privacy, and human-approval gates.
