# Prompt Log

> **Honesty rule:** Only the entries marked ✅ REAL describe things that actually happened while this
> project was built. Entries marked ⬜ YOUR TURN are templates: do the step yourself, then write down
> what really happened. Do not fill them in with things you did not do.

---

## ✅ REAL - Entry 1: Initial project-planning prompt
1. **Problem:** I needed a small, achievable project showing practical AI use, Python and automation for the AI Growth & Automation Associate assessment.
2. **Prompt used:** A long structured prompt that set a role ("senior Python developer, AI automation engineer, healthcare data specialist and technical mentor"), the project objective, 7 required features, the tech stack, development rules, prompt-log rules, video requirements, quality standards, and a working style ("one step at a time, wait for me"). *(Paste your full prompt here.)*
3. **Result produced:** Project overview, Mermaid architecture diagram, folder structure, roadmap, software list, and only Step 1 (setup + fictional sample data with deliberate errors).
4. **What was wrong or incomplete:** Nothing wrong with the content, but my own instruction "implement the first step only and wait" meant I would have needed ~9 more rounds of conversation.
5. **How the prompt was improved:** See Entry 2.
6. **How the result was checked:** I read the plan against my requirements list. *(Add what you personally checked.)*

## ✅ REAL - Entry 2: "okay now lets make it"
1. **Problem:** I wanted to move forward.
2. **Prompt used:** `okay now lets make it`
3. **Result produced:** Step 2 only (the loader + tests).
4. **What was wrong or incomplete:** The prompt was too vague. The assistant followed my earlier "step by step" instruction literally, so it built one module instead of the project.
5. **How the prompt was improved:** I stated the outcome explicitly (Entry 3).
6. **How the result was checked:** I noticed it was only one step of the project.

*Lesson for the assessment: a short prompt inherits all the earlier constraints in the conversation. If the goal changes, say so explicitly.*

## ✅ REAL - Entry 3: Clarifying the deliverable
1. **Problem:** Entry 2 produced a fragment, not a finished project.
2. **Prompt used:** `no you have to build everything and give me zip file`
3. **Result produced:** The complete project in a zip file: loader, cleaner, duplicate detection, validator, AI analysis with rule-based fallback, exporter, pipeline, command-line runner, Streamlit dashboard, 61 tests, README, docs.
4. **What was wrong or incomplete:** Some things could not be run in the assistant's environment: the real Streamlit UI, real `pytest`, and the real AI API call. Those must be checked by me.
5. **How the prompt was improved:** Could have been: *"Build the complete project now (all files, tests, README, prompt log, video script), run whatever you can, tell me what you could not test, and give me a zip."*
6. **How the result was checked:** The assistant reported running the pipeline on the sample file (11 imported, 1 duplicate removed, 10 cleaned, 3 incomplete, 6 flagged) and 61 tests with a stand-in runner. **My own check:** ⬜ run `pytest -v` and `streamlit run app.py` and record what I saw: ________

## ✅ REAL - Entry 4: Problems that came up while the assistant built it
These happened during the build and were fixed by the assistant. Record them here only if you want to describe them; you did not personally debug them.
- **Directory creation failed** in the build environment because the shell did not support `{a,b,c}` brace expansion. Fix: create folders one at a time. *(Environment issue, not a project bug.)*
- **A stray leftover line** (`result.summary_source = "ai"`) was spotted during review and removed.
- **Real pytest could not be installed** (no network), so a minimal stand-in runner was used. This is why you must run real pytest yourself.

---

## ⬜ YOUR TURN - Entry 5: Running and debugging
1. **Problem encountered:** (e.g. an install error, a failing test, a Streamlit error. Paste the real error text.)
2. **Prompt used:** *Suggested pattern:* "I ran `<command>` in my project and got this error: `<full error text>`. My Python version is `<version>` and my OS is `<OS>`. Here is the relevant file: `<paste>`. Explain the cause in simple words, then give the smallest fix."
3. **Result produced:**
4. **What was wrong or incomplete:**
5. **How the prompt was improved:**
6. **How the result was checked:** (re-ran the command; what happened?)

## ⬜ YOUR TURN - Entry 6: Improving the user interface
1. **Problem:** (what looked wrong or confusing when you ran the dashboard?)
2. **Prompt used:** *Suggested pattern:* "Here is my `app.py`. When I ran it, `<what I saw>`. I want `<specific change>`, for a non-technical user. Change only that part."
3-6. (Result / what was wrong / improved prompt / how you checked: screenshot before and after.)

## ⬜ YOUR TURN - Entry 7: Validating the output
Ideas that make good, genuine entries (do them, then record the real outcome):
- Make your own test CSV with messy data (different column names, lowercase names, a phone with letters). Run it. Did the results match what you expected?
- Ask the AI: "Review `src/cleaner.py` for edge cases that would produce wrong results. Give three example inputs that might break it." Then run those inputs and record what actually happened.
- If you have an API key: run with AI on, then compare AI categories with the rule-based ones. Did anything look wrong?

## ⬜ YOUR TURN - Entry 8: Follow-up prompts that improved the results
Record any prompt where the first answer was weak and your second prompt made it better: what was missing, what you added (role, constraints, examples, output format), and how the result changed.
