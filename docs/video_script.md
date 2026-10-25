# Video script (about 3.5 minutes)

**Before recording:** run the app yourself, read the script aloud twice, and replace every
**[BRACKETED]** part with your own real experience. Delete anything that is not true for you.
Speak at a relaxed pace (about 140 words per minute). The script is ~520 words.

**Be honest about AI help.** This project was built with an AI assistant. Say so, and then show that
you understand it. Assessors are testing how you use AI, not whether you avoided it.

---

## 0:00 - The problem (≈25 s)
"Hello, my name is **[YOUR NAME]**. Healthcare directories, lists of clinics, doctors, specialties and phone numbers, are usually collected by hand from many places. That creates duplicates, inconsistent formatting, missing information and wrong-looking contact details. Cleaning it manually is slow and repetitive. So I built a tool that automates the first pass."

## 0:25 - Why this project (≈20 s)
"I chose this because **[YOUR REAL REASON, e.g. it's a clear, repetitive task where automation and AI help, and it connects to the healthcare data work in this role]**. I also wanted something small enough to finish properly and explain clearly."

## 0:45 - AI tools and prompts (≈40 s)
"I used **[NAME OF AI ASSISTANT]** to plan and generate the code. I started with one detailed prompt that gave it a role, the goal, the required features, the tools, and rules such as: never invent data, and keep checks separate from verification. **[Describe a real prompt improvement. For example: my short follow-up prompt only produced one piece of the project, so I rewrote it to state the full outcome I wanted.]** I documented my prompts in a prompt log, including what I had to refine."

## 1:25 - How it works (≈40 s)
"The tool is written in Python with Pandas. It has one pipeline: import the file, clean it, find duplicates, check quality, optionally analyse with AI, and export. Each step is a separate module, so it's easy to test.
Two design decisions matter most to me. First, exact duplicates are removed, but *possible* duplicates are only flagged, because two branches of the same group can look alike, and a person should decide. Second, the tool never claims data is correct. It says 'detected', never 'verified'."

## 2:05 - Live demo (≈60 s)
*(Screen: the running app.)*
"Here is the dashboard. I'll load the sample file. It's fictional data with deliberate mistakes. I click Process data.
At the top: **[READ THE REAL NUMBERS FROM YOUR SCREEN: imported, duplicates removed, cleaned, incomplete, flagged]**.
In the issue report you can see problems like a missing phone number and a badly formed website. In the duplicates tab, one exact duplicate was removed, and two similar records were flagged for review. The change log shows every edit with the original value, so nothing disappears silently.
The AI tab shows the mode. **[Say whether you ran with AI or rule-based.]** Without an API key, the app uses keyword rules and templates, and it clearly says so. With a key, AI output is checked before it's used; if it's invalid, the tool falls back.
Finally I download the cleaned data and the quality report."

## 3:05 - Challenges, limits, next steps (≈35 s)
"A challenge I actually faced was **[YOUR REAL CHALLENGE AND HOW YOU SOLVED IT. If none, say what you learned from running the tests or reading the code.]**
Limitations: it only checks format, it doesn't look anything up online, phone grouping assumes Indian-style numbers, and duplicate matching is simple. Next, I would add optional website checks, address validation and a screen for reviewing possible duplicates.
Thank you for watching."

---

## Questions you may be asked (know the honest answers)
- **"Did you write this code yourself?"** → "I built it with AI assistance. I reviewed it, ran it, and I can explain how each part works."
- **"Why not delete near-duplicates?"** → Risk of deleting real separate branches; a human should decide.
- **"Does a record with no issues mean it's correct?"** → No. It only passed format checks.
- **"What if the AI gives a wrong answer?"** → Output must be valid JSON with allowed categories and no invented numbers; otherwise it's discarded and rule-based results are used.
- **"What needs the AI API?"** → Classifying records the rules can't place, the written summary, and the explanations. Everything else works without it.
