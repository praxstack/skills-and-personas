"""Smallest replayable model used by the practical forward-behavior case."""

import sys


def predict(xs: list[float], w: float, b: float) -> list[float]:
    return [w * x + b for x in xs]


def mse(predictions: list[float], targets: list[float]) -> float:
    return sum(
        (prediction - target) ** 2
        for prediction, target in zip(predictions, targets, strict=True)
    ) / len(targets)


def values(numbers: list[float]) -> str:
    return "[" + ", ".join(f"{number:.2f}" for number in numbers) + "]"


def step(
    xs: list[float], targets: list[float], w: float, b: float, learning_rate: float
) -> tuple[float, float, float, float]:
    errors = [
        prediction - target
        for prediction, target in zip(predict(xs, w, b), targets, strict=True)
    ]
    dw = 2 * sum(error * x for error, x in zip(errors, xs, strict=True)) / len(xs)
    db = 2 * sum(errors) / len(xs)
    return w - learning_rate * dw, b - learning_rate * db, dw, db


def run_case(
    name: str,
    xs: list[float],
    targets: list[float],
    w: float,
    b: float,
    learning_rate: float,
) -> None:
    before_predictions = predict(xs, w, b)
    before_loss = mse(before_predictions, targets)
    next_w, next_b, dw, db = step(xs, targets, w, b, learning_rate)
    after_predictions = predict(xs, next_w, next_b)
    print(f"case={name} learning_rate={learning_rate:.2f}")
    print(
        f"before w={w:.3f} b={b:.3f} predictions={values(before_predictions)} loss={before_loss:.3f}"
    )
    print(f"gradients dw={dw:.3f} db={db:.3f}")
    print(
        f"after w={next_w:.3f} b={next_b:.3f} predictions={values(after_predictions)} loss={mse(after_predictions, targets):.3f}"
    )


CASES = {
    "rent-stable": ([1, 2, 3], [1.5, 2.0, 2.5], 0.2, 0.5, 0.1),
    "rent-overshoot": ([1, 2, 3], [1.5, 2.0, 2.5], 0.2, 0.5, 1.0),
    "delivery-transfer": ([1, 2], [5, 7], 1.0, 1.0, 0.1),
}

selected = sys.argv[1:] or list(CASES)
if any(name not in CASES for name in selected):
    raise SystemExit(f"unknown case; choose from: {', '.join(CASES)}")
for case_name in selected:
    run_case(case_name, *CASES[case_name])
