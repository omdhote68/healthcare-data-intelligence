# 🩺 Healthcare Data Intelligence & Automation

A small, practical tool that takes a messy healthcare practice directory file (CSV or Excel),
cleans it with Python, flags data-quality problems, optionally uses AI to categorise and
summarise, and exports a cleaned dataset plus a separate data-quality report.

**All sample data is fictional.** Phone numbers use `555` patterns and websites use
`example.com` / `example.org` (domains reserved for documentation).

> **Detected is not verified.** Every check here is an automated *format* check. A record that
> passes has **not** been confirmed as real, accurate or current. Missing information is
> never guessed, and no digits are ever added to phone numbers.

## What it does

| Stage | What happens | Needs AI API? |
|---|---|---|
| Import | Reads `.csv` / `.xlsx`; maps differently named columns (e.g. "Clinic Name", "Speciality") to a standard set | No |
| Clean | Trims whitespace, tidies capitalisation, formats phone numbers, fixes missing `https://`, keeps originals | No |
| Deduplicate | **Removes** exact duplicates (same name + city + phone after cleaning); **flags** possible duplicates for human review | No |
| Validate | Flags missing fields, invalid-looking phones/URLs, incomplete records | No |
| Categorise | Keyword rules assign a specialty category; AI optionally handles records the rules can't place | Rules: No · AI step: Yes |
| Summarise / explain | Template text by default; AI-written summary and explanations optionally | Template: No · AI: Yes |
| Export | Cleaned CSV, quality-report CSV, change-log CSV, multi-sheet Excel workbook | No |

If no API key is available, the AI features fall back to the rule-based versions and the
dashboard labels the mode as **rule-based**. AI output is always validated (valid JSON, allowed
categories only, no numbers the AI was not given); anything that fails is discarded.

## Quick start

Requires **Python 3.10+**.

```bash
# 1. Create and activate a virtual environment
python -m venv venv
venv\Scripts\activate            # Windows (PowerShell: venv\Scripts\Activate.ps1)
source venv/bin/activate         # Mac / Linux

# 2. Install dependencies
pip install -r requirements.txt

# 3. Start the dashboard
streamlit run app.py
```

Then: choose **Use sample data** (or upload your own file) → click **Process data**.

### No dashboard? Use the command line

```bash
python run_pipeline.py                       # built-in sample file
python run_pipeline.py data/my_file.xlsx     # your own file
python run_pipeline.py data/my_file.csv --ai # with AI (needs a key)
```
Results are written to the `outputs/` folder.

### Optional: turn on the AI features

1. Get an API key from your AI provider (this project uses the Anthropic API).
2. Copy `.env.example` to `.env` and paste your key after `ANTHROPIC_API_KEY=`.
3. Restart the app. The **Use AI analysis** checkbox becomes available.

`.env` is listed in `.gitignore`, so your key is never committed. **Never paste a key into the code.**
Only specialty/practice names and aggregate counts are sent to the AI, never phone numbers or URLs.
The model name can be changed with the optional `ANTHROPIC_MODEL` variable if the default is retired.

## Input format

Any CSV/Excel file with a practice-name column. Recognised headings (case/spacing ignored):

| Standard field | Also recognised |
|---|---|
| practice_name *(required)* | clinic name, hospital name, practice, name |
| doctor_name | doctor, physician |
| specialty | speciality, specialization, department |
| city | town, location |
| phone | phone number, telephone, tel, contact number, mobile |
| website | url, web, site |
| source_url | source, source link |

Missing columns are left empty. Extra columns are ignored (and reported).

## Outputs

| File | Contents |
|---|---|
| `cleaned_data.csv` | Cleaned records + category + status columns + original phone/website + flags |
| `data_quality_report.csv` | One row per detected issue (row, field, type, severity, detail) |
| `change_log.csv` | Every value the cleaner changed, with original and new value |
| `healthcare_data_results.xlsx` | All of the above plus summary and duplicate sheets |

## How "flagged" and "incomplete" are defined

- **Incomplete**: missing any of practice name, specialty, city, phone.
- **Flagged**: at least one *medium/high* issue (missing required field, invalid-looking phone/URL, possible duplicate). Missing doctor name or website alone does not flag a record.
- **Exact duplicate** (removed): same name, city and phone after cleaning.
- **Possible duplicate** (kept, flagged): same valid phone number, or near-identical names in the same city. Branches of one group can legitimately look like this, so a human decides.

## Project structure

```
app.py                 Streamlit dashboard
run_pipeline.py        Command-line runner
src/
  config.py            Column aliases, thresholds, constants
  logger.py            Logging to console + logs/pipeline.log
  loader.py            Read CSV/Excel, map columns
  cleaner.py           Text / phone / URL cleaning, change log
  dedupe.py            Exact + potential duplicate detection
  validator.py         Issue detection and per-record flags
  ai_analysis.py       Rule-based categories + optional AI (validated)
  exporter.py          CSV / Excel export
  pipeline.py          Ties the steps together
tests/                 Automated tests (pytest)
data/sample_practices.csv   Fictional sample data with deliberate errors
docs/                  Prompt log, video script, GitHub/deployment guide, checklist
```

## Run the tests

```bash
pytest -v
```

## Known limitations

- Phone grouping assumes Indian-style numbers (e.g. `+91 98765 55501`); other numbers are kept as plain digits, not guessed at.
- A valid-looking URL or phone number may still be wrong, dead, or belong to someone else. No network lookups are performed.
- Duplicate matching is rule-based and simple; it will miss duplicates with very different names and may flag genuine separate branches.
- Capitalisation tidying is conservative; unusual names may need manual review.
- Designed for files up to 20,000 rows.
- If you collect real data from public websites, follow each site's terms of use and applicable privacy law. This project does not scrape anything.

## Ideas for future improvement

Optional website-reachability checks (with permission), address/pincode validation, fuzzy matching with more signals, a manual "review and accept" screen for possible duplicates, and support for more languages.

See `docs/github_and_deployment.md` to publish this project.
