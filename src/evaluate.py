"""Evaluate completed human labels and model predictions from a CSV file."""

import argparse
import json

import pandas as pd


def _binary_scores(gold, predicted):
    true_positive = sum(actual and guess for actual, guess in zip(gold, predicted))
    false_positive = sum(not actual and guess for actual, guess in zip(gold, predicted))
    false_negative = sum(actual and not guess for actual, guess in zip(gold, predicted))
    precision = true_positive / (true_positive + false_positive) if true_positive + false_positive else 0.0
    recall = true_positive / (true_positive + false_negative) if true_positive + false_negative else 0.0
    f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
    return {
        "n": len(gold),
        "precision": round(precision, 4),
        "recall": round(recall, 4),
        "f1": round(f1, 4),
    }


def evaluate_labels(frame):
    required = {
        "gold_category", "predicted_category", "gold_repeat", "predicted_repeat"
    }
    missing = required - set(frame.columns)
    if missing:
        raise ValueError(f"Missing evaluation columns: {', '.join(sorted(missing))}")

    category_rows = frame[["gold_category", "predicted_category"]].replace(r"^\s*$", pd.NA, regex=True).dropna()
    category_accuracy = (
        float(category_rows["gold_category"].eq(category_rows["predicted_category"]).mean())
        if not category_rows.empty else None
    )

    repeat_rows = frame[["gold_repeat", "predicted_repeat"]].replace(r"^\s*$", pd.NA, regex=True).dropna()
    true_values = {"true", "1", "yes", "y"}
    gold_repeat = repeat_rows["gold_repeat"].astype(str).str.casefold().isin(true_values).tolist()
    predicted_repeat = repeat_rows["predicted_repeat"].astype(str).str.casefold().isin(true_values).tolist()
    repeat_scores = _binary_scores(gold_repeat, predicted_repeat) if gold_repeat else {
        "n": 0, "precision": None, "recall": None, "f1": None
    }

    return {
        "category": {
            "n": len(category_rows),
            "accuracy": round(category_accuracy, 4) if category_accuracy is not None else None,
        },
        "repeat_flag": repeat_scores,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("csv_path", help="CSV with gold and predicted labels")
    args = parser.parse_args()
    frame = pd.read_csv(args.csv_path, keep_default_na=False)
    print(json.dumps(evaluate_labels(frame), indent=2))


if __name__ == "__main__":
    main()