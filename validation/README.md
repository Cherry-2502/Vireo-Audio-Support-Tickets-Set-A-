# Human-Labeled Validation

`annotation_template.csv` contains 25 ticket IDs selected with a fixed random seed from the deduplicated dataset. The gold-label and model-prediction fields are intentionally blank: no independent human annotation or model run was supplied, so this project does not claim classifier accuracy.

For each ticket, use `tickets.csv` to inspect the customer message and agent note. Label `gold_category` using the taxonomy in `src/classify.py`; set `gold_repeat` to true only when the same issue returned within 30 days after a valid resolution. Use `reviewer_note` for ambiguity. Do not use the intake category as ground truth. Label independently before looking at model predictions where possible.

After running the selected tickets through the classifier, fill `predicted_category` and `predicted_repeat`, then run `python -m src.evaluate validation/annotation_template.csv`. The evaluator reports category accuracy and repeat precision, recall, and F1 on non-empty labels. Record the sample size and limitations with the reported scores.
