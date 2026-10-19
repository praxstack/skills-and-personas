"""Every ptk error class and its exit code (spec §5.4, CEO §2, D18.4).

Exit codes:
    0 verified/packaged   1 gate failed   2 host/environment   3 model error
    4 claims-pending      5 incomplete    6 degraded
No other module defines exception classes for the CLI to catch.
"""

EXIT_OK = 0
EXIT_GATE = 1
EXIT_HOST = 2
EXIT_MODEL = 3
EXIT_CLAIMS_PENDING = 4
EXIT_INCOMPLETE = 5
EXIT_DEGRADED = 6


class PtkError(Exception):
    exit_code = EXIT_GATE

    def __init__(self, message, **detail):
        super().__init__(message)
        self.message = message
        self.detail = detail

    @property
    def kind(self):
        return type(self).__name__

    def as_dict(self):
        return {"error": self.kind, "message": self.message, "exit": self.exit_code, **self.detail}


# ---- host / environment (exit 2) ----
class HostError(PtkError):
    exit_code = EXIT_HOST


class HostToolMissing(HostError):
    pass


class SandboxUnavailable(HostError):
    pass


class SetupError(HostError):
    pass


class TTSUnavailable(HostError):
    pass


class ToolFailed(HostError):
    """An external tool exited non-zero where ptk expected success."""


# ---- model (exit 3) ----
class ModelError(PtkError):
    exit_code = EXIT_MODEL


class ModelSchemaError(ModelError):
    pass


class ModelReferenceError(ModelError):
    pass


class IllegalTransition(ModelError):
    pass


class NarrationEmpty(ModelError):
    pass


# ---- gate / capture failures (exit 1) ----
class GateError(PtkError):
    exit_code = EXIT_GATE


class CompileError(GateError):
    pass


class RunTimeout(GateError):
    pass


class RunCrashed(GateError):
    pass


class NondeterministicOutput(GateError):
    pass


class CompilerDisagreement(GateError):
    pass


class SanitizerFinding(GateError):
    pass


class ExpectationMismatch(GateError):
    pass


class OutboundRequest(GateError):
    pass


class MemoryLimitExceeded(GateError):
    pass


class OutputLimitExceeded(GateError):
    pass


class RenderCheckFailed(GateError):
    pass


class RenderFailed(GateError):
    pass


class ClaimsReviewInvalid(GateError):
    pass


class ClaimsUnmapped(GateError):
    pass


class SourceExcerptMissing(GateError):
    """AC-7.7: a claim cites an outside document whose passage is not stored under the lesson's sources/, or a
    quote is not in its stored passage."""


class GateFailed(GateError):
    pass
