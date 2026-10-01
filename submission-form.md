# Submission Form — Vireo Audio Support Analytics

## 1. What did you build, and what business outcome does it move?

A local Streamlit dashboard with weekly complaint summaries, optional Gemini classification, Tier 1 agent reporting, and repeat-contact cost estimates. In the current dataset, the category-plus-SKU proxy flags 980 of 11,875 tickets (8.25%). A 30% relative reduction to 5.78% would be worth approximately ₹12,700 per quarter at policy channel costs, if validated and achieved.

## 2. What does one run cost, and what would a month cost at Vireo's volume?

The dashboard and deterministic metrics run locally without API calls. AI classification is optional: one request per 25 tickets, or about 26 requests for a 650-ticket week. No API call was made during this verification. Actual Gemini charges depend on the Google account's model pricing, quota, and billing settings; a reliable rupee estimate has not been established.

## 3. How do you know it works?

Eleven automated tests cover repeat-window rules, issue/customer matching, unresolved and invalid prior tickets, empty and one-day inputs, weekly buckets, roster-date assignments, Tier 2 exclusion, classifier response validation, and empty/partial evaluation files. These do not measure LLM quality. No independent human-labeled benchmark is complete; an annotation template and evaluation script are included. Classifier accuracy is not claimed.

## 4. Did you change, narrow, or push back on the client's ask?

The leaderboard reports Tier 1 by weekly resolved volume and does not rank Tier 2 by volume, consistent with policy §6 and Neha's request. Tier 2 duration is shown separately. The dashboard uses a selectable week over the historical export rather than pretending the static export is an automated live weekly feed. Savings are framed as a repeat-contact reduction scenario, not guaranteed ROI.

## 5. What is wrong with what you are handing us?

Same issue is approximated by canonical category plus SKU because the data has no issue ID. The 30% reduction is an assumption. The complexity score is not calibrated. The LLM has not been independently human-evaluated. Some legacy resolution timestamps are impossible and excluded from repeat-window starts. Public links and the required screen recording are not yet supplied.

## 6. What did you deliberately leave out, and why?

Live helpdesk integration, duplicate blocking, cloud hosting, and automated scheduled delivery are out of scope; the email thread asks for a simple tool and the provided data is a static export. Predictive routing is also not implemented.

## 7. Anything you built or found that nobody asked for?

The stricter repeat proxy identifies VA-EB-PL2 as the largest product signal (298 repeats). The cleaned export contains 1,874 resolution timestamps earlier than ticket creation; these are flagged and cannot start a repeat window. These are leads for review, not confirmed root causes.

## 8. What did you use AI for? Which tools/models, where they helped, what did you discard?

The app is configured for optional Gemini 2.5 Flash classification; it was not called during this verification, so this verification incurred no model API usage. GitHub Copilot was used to implement and test the code changes in this workspace. Confirm any other tools, earlier model versions, prompts, and discarded prototypes from your own work history before submitting. The current prompt is in `src/classify.py`; the prior draft's Gemini 1.5 claim did not match the configured model.

## 9. Someone picks this up Monday and you're unreachable. What do they need to know?

1. From the project root, install `requirements.txt` and run `streamlit run src/app.py`; the CSVs are in `src/data/`.
2. The dashboard loads without a key. Set `GEMINI_API_KEY` only to enable the explicit weekly classification action; it sends ticket text to Google Gemini.
3. Repeat rate uses customer + canonical category + SKU as an issue proxy and resolution-based 30-day timing. Recheck the policy proxy and cost assumptions before external use.

## 10. Honest hours spent

The working notes report approximately five hours. The author should confirm this reflects actual effort.

## 11. GitHub repository link

Not published or supplied yet. Add the actual public repository URL before submission.

## 12. Public Google Drive link

Not created or supplied yet. Add the actual public folder link before submission.

## Required recording

Not recorded yet. Submit a video of at most three minutes following `recording-outline.md`; include actual prompts used, changes between versions, and discarded approaches.
