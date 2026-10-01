# Vireo Audio Support Analytics

Local Streamlit dashboard for weekly complaint analysis, optional Gemini-assisted categorization, Tier 1 agent reporting, and policy-based repeat-contact cost estimates.

## Run locally

Use Python 3.11 or later from the project root. Ticket and roster files are in `src/data/`.

```powershell
py -m venv .venv
.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\streamlit.exe run src/app.py
```

The dashboard loads without an API key. To request AI classifications, set `GEMINI_API_KEY` in your operating-system environment using your private secret manager, then click the classification button for the selected week.

Classification is opt-in and sends the selected week's ticket text to Gemini 2.5 Flash in batches of 25. A typical 650-ticket week would use about 26 API requests. Google account quotas and charges depend on the configured billing plan; this project does not promise zero cost. Do not commit API keys.

## What the metrics mean

- Repeats require the same customer, canonical complaint category, and product SKU, with a new ticket opened within 30 days after a prior valid resolution. The export has no issue identifier, so category plus SKU is an explicit issue proxy, not proof of identical issue.
- Invalid resolution timestamps and unresolved tickets do not start a repeat window. Duplicate ticket IDs prefer the helpdesk export over legacy rows.
- Channel costs are chat ₹210, email ₹260, voice ₹520, and social ₹240. The quarterly estimate annualizes the observed cost over the selected date span; a one-day span is safe but should not be treated as a stable forecast.
- Both agent volume views include Tier 1 only. Tier 2 is shown separately with average valid resolution duration. The complexity score remains an uncalibrated heuristic.
- A 30% reduction is a scenario, not a measured intervention result.

## Current full-data baseline

With the present category-plus-SKU repeat proxy, the 11,875 deduplicated tickets contain 980 repeats (8.25%). Channel-priced repeat cost is ₹253,170 over 546 calendar days, or about ₹42,340 per quarter annualized. A 30% reduction scenario is about ₹12,702 per quarter. Recompute these figures after changing data or metric rules; do not quote them as verified same-issue outcomes.

## Tests and validation

Run the deterministic metric, evaluation, and classifier-response tests:

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

The LLM has not been accuracy-validated in this repository. `validation/annotation_template.csv` contains a deterministic sample for independent human labeling. Fill the gold and prediction columns, then run:

```powershell
.\.venv\Scripts\python.exe -m src.evaluate validation/annotation_template.csv
```

Do not use intake-bot tags as gold labels. See `validation/README.md` for the annotation protocol. A completed, independently reviewed benchmark is still required before claiming classifier accuracy.

## Submission files

- `memo-to-priya.md`: current one-page business memo.
- `submission-form.md`: current form draft and explicit items still requiring the author's personal details, public links, and completed recording.
- `recording-outline.md`: a concise walkthrough outline; it is not a substitute for the required video.
