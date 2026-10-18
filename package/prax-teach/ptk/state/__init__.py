"""Consent-first learner state, ported from Prax Teach v2 (praxteach) for v2.1 (AC-8.4).

Versions:
- SCHEMA_VERSION "1" is the record version of every v1 record kind (observation, correction,
  invalidation, misconception_rejection, the scheduler records, sources.json). Their shape did not
  change, so their bytes and event ids stay exactly as v2 wrote them.
- WORKSPACE_SCHEMA "2" is what v2.1 writes to learner.json. A v2 workspace may hold the two new kinds:
  `evidence` records (schema "2") in sessions.jsonl and `navigation` records (schema "2") in their own
  file, state/navigation.jsonl, so navigation is never mixed with attempts.
- A v1 workspace (learner.json schema "1") reads unchanged and keeps working with v1 kinds only.
  `ptk.state.schema2.migrate` snapshots it and moves it to "2". v2 can't read a "2" workspace, which
  is why rollback restores the snapshot.
- CORE_VERSION is the projection generator version. The projection algorithm is unchanged, so it stays
  "1.0.0" and stored v1 projections still match.
"""

from __future__ import annotations

SCHEMA_VERSION = "1"
RECORD_SCHEMA_V2 = "2"
WORKSPACE_SCHEMA = "2"
READABLE_WORKSPACE_SCHEMAS = ("1", "2")
CORE_VERSION = "1.0.0"
