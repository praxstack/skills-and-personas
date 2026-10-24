# Hosted CI compatibility failure

Both initial bounded-regression runs40116715981 and40116703598 failed the required pipeline import/parity suite under pinned Python3.11.17. The actual uploaded tests.txt trace identifies enhance_final_notes.py:293, SyntaxError: f-string expression part cannot include a backslash. The surrounding expected sandbox OOM/log/count exhaustion output is deliberate negative-control evidence, not this failure's cause.

The source and new-skills mirror used three backslash-containing joins inside an f-string, a construct accepted by the local Python3.13 checks. The repair hoists those joins without changing output. Local Python3.11.15 now compiles all26 modules and passes all5 import/CLI/parity controls; all9 guide configurations produce byte-identical output under old/new module comparison on3.13. CI's pinned Python version, required suite and failure propagation remain unchanged.

Original runs: https://github.com/praxstack/skills-and-personas/actions/runs/40116715981 and https://github.com/praxstack/skills-and-personas/actions/runs/40116703598 . Uploaded teacher-regression-receipts contains the actual failure trace. Current-head CI is rerun after the repair.
