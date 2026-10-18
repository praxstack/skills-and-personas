"""`python -m ptk.state ...`: the ported v2 learner-state CLI (consent, evidence, review, export, schema 2)."""
import sys

from .cli import main

sys.exit(main())
