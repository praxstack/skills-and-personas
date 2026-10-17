"""Typed errors and stable CLI exit codes."""

from __future__ import annotations


class PraxTeachError(Exception):
    """Expected user-facing failure."""

    exit_code = 5


class ConsentRequired(PraxTeachError):
    """Persistence was requested without explicit consent."""

    exit_code = 3


class ConfirmationRequired(PraxTeachError):
    """A destructive operation needs an explicit confirmation flag."""

    exit_code = 4


class SafetyError(PraxTeachError):
    """A path or filesystem invariant failed closed."""

    exit_code = 5


class ValidationError(PraxTeachError):
    """Input or state did not satisfy the public contract."""

    exit_code = 6


class StateNotFound(PraxTeachError):
    """The requested learner workspace has not been initialized."""

    exit_code = 7
