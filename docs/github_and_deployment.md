# Publishing to GitHub and (optionally) deploying

## Before you publish: safety check
1. Make sure `.env` is **not** in the folder you commit (it is git-ignored, but double-check).
2. Run `git status` and confirm you don't see `.env`, `venv/` or `outputs/*.csv`.
3. If you ever pasted an API key anywhere public, revoke it at your provider and create a new one.

## GitHub (step by step)
1. Create a free account at github.com.
2. Click **New repository**. Name it e.g. `healthcare-data-intelligence`. Leave "Add README" **unticked** (we already have one). Choose Public so assessors can view it.
3. In a terminal, inside the project folder:

```bash
git init
git add .
git status                       # review the list - no .env, no venv
git commit -m "Initial commit: healthcare data intelligence & automation"
git branch -M main
git remote add origin https://github.com/YOUR-USERNAME/healthcare-data-intelligence.git
git push -u origin main
```
(If Git asks who you are: `git config --global user.name "Your Name"` and `git config --global user.email "you@example.com"`. GitHub may ask you to sign in through the browser or use a personal access token.)

4. Refresh the GitHub page - your files should appear and the README will display.
5. Prove it works from scratch: clone it into a new folder, create a fresh virtual environment, `pip install -r requirements.txt`, and run `streamlit run app.py`.

## Optional free deployment: Streamlit Community Cloud
*Free hosting for public Streamlit apps existed when this guide was written - check streamlit.io for current terms and availability before relying on it.*

1. Push the project to a **public** GitHub repository (above).
2. Go to share.streamlit.io and sign in with GitHub.
3. Click **Create app**, pick your repository, branch `main`, and main file `app.py`.
4. (Optional AI) In the app's **Advanced settings → Secrets**, add:
   ```toml
   ANTHROPIC_API_KEY = "your-key-here"
   ```
   Streamlit exposes secrets as environment variables, which is what this project reads. Do not put the key in the repository.
5. Click **Deploy**. The first build installs `requirements.txt`.

**Cautions for a public deployment**
- Anyone with the link can upload files. Do **not** upload real personal or sensitive data to a public demo.
- If you add an API key, strangers using the app spend *your* API credit. For an assessment, either leave AI off in the deployed version (rule-based mode works without a key) or demonstrate AI locally.
- The hosted file system is temporary; the log file may not persist. The app handles that automatically.

If you don't deploy, a screen recording of the local app is perfectly fine.
