# Assessment checklist

"Checked by builder" = I (the AI assistant) ran it in my own environment while building.
"You must check" = I could not run it there; please verify on your machine and tick it off yourself.

| Requirement | Where | Status |
|---|---|---|
| Upload CSV/Excel, flexible column names | `src/loader.py`, `app.py` | Loader checked by builder (CSV, Excel, odd headings, latin-1, missing columns). Uploader widget: **you must check** |
| Duplicate removal | `src/dedupe.py` | Checked by builder on sample + unit tests |
| Standardise text / phone / URL, keep originals | `src/cleaner.py` | Checked by builder |
| Missing / invalid / inconsistent detection | `src/validator.py` | Checked by builder |
| "Detected vs verified" distinction | `VERIFICATION_LABEL`, banner in `app.py`, README | Checked by builder (labels present in outputs) |
| AI categorisation / summary / explanations with JSON validation | `src/ai_analysis.py` | Validation + fallback checked by builder using a **fake** AI function. **The real API was never called** - you must test with your own key |
| Non-API fallback, clearly labelled | `src/ai_analysis.py`, AI tab | Checked by builder |
| Pipeline + logging + clear errors | `src/pipeline.py`, `run_pipeline.py`, `logs/` | Checked by builder |
| Metrics + CSV/Excel export | `src/exporter.py` | Checked by builder (files written and re-read) |
| Streamlit dashboard | `app.py` | Compiles; logic smoke-tested against a **stub** of Streamlit. **You must run `streamlit run app.py` and look at it** |
| Automated tests | `tests/` | 61 tests passed using a minimal stand-in runner (real pytest wasn't installable). **You must run `pytest -v`** |
| Prompt log | `docs/prompt_log.md` | Template + entries that really happened. **You must add your own** |
| GitHub publishing | `docs/github_and_deployment.md` | Instructions only; not performed |
| Optional deployment | same | Instructions only; **not deployed** |
| Video script | `docs/video_script.md` | Draft with blanks for your real experience |

## Final submission package
- [ ] GitHub link (public) or the zip
- [ ] Screenshot or 3-4 minute screen recording of the working app
- [ ] `docs/prompt_log.md`, completed with your real prompts
- [ ] Be ready to explain: what each file in `src/` does, why exact duplicates are removed but possible ones only flagged, why "passed checks" is not "verified"
