"""No-dependency pilot calculations and transfer fixture."""

from __future__ import annotations

from decimal import Decimal


def observe(
    a: float = 0.1, b: float = 0.2, expected_decimal: float = 0.3
) -> dict[str, object]:
    result = a + b
    return {
        "intent": f"{a} + {b}",
        "result": result,
        "exact_decimal": result == expected_decimal,
        "difference": result - expected_decimal,
    }


def transfer() -> dict[str, object]:
    result = Decimal("0.7") + Decimal("0.1")
    return {
        "prompt": "0.7 + 0.1",
        "exact_decimal_result": str(result),
        "learner_must_explain": True,
    }


def main() -> None:
    result = observe()
    assert result["result"] == 0.30000000000000004
    assert result["exact_decimal"] is False
    assert transfer()["exact_decimal_result"] == "0.8"
    print({"pilot": result, "transfer": transfer()})


if __name__ == "__main__":
    main()
