# Deploying CAS Dashboard to GitHub & Streamlit Cloud

The application is now a **Single Page App (SPA)**. Follow these steps to deploy.

## Step 1: Push Code to GitHub

Since you encountered errors, let's reset and initialize correctly.

Run these commands in your terminal one by one:

```bash
# 1. Initialize Git (Safe to run again)
git init

# 2. Add all files
git add .

# 3. Create the first commit
git commit -m "Initial commit of CAS Dashboard SPA"

# 4. Enforce the branch name to be 'main'
git branch -M main

# 5. Link your repository (ignore error if already exists)
# Replace <your-repo-url> with your actual GitHub URL
# Example: https://github.com/gpakle/casapp.git
git remote add origin https://github.com/gpakle/casapp.git

# 6. Push code (Force push to overwrite empty remote state if needed)
git push -u origin main --force
```

**Critical**: Make sure the `data/` folder containing `.csv` files (`pay_matrix.csv`, `da_rates.csv`, etc.) is tracked and pushed.

## Step 2: Deploy on Streamlit Cloud

1.  Go to [share.streamlit.io](https://share.streamlit.io/)
2.  Click **"New app"**
3.  Select your Repository (`gpakle/casapp`) and Branch (`main`).
4.  Main file path: `app.py`
5.  Click **"Deploy"**.

## ⚠️ Important Notes

- **Data Persistence**: The app uses SQLite (`cas_app.db`). On Streamlit Cloud, this database is **ephemeral** (deleted on restart).
- **Security**: Do not commit secrets (API keys, etc.) to GitHub. This app currently requires no secrets.

## Step 3: Updating the App

Streamlit Cloud has **Continuous Deployment**. This means the app updates automatically whenever you push code to the `main` branch.

**Workflow for Making Changes:**

1.  **Make Edits Locally**: Change code in `app.py`, `src/`, etc.
2.  **Test Locally**: Run `streamlit run app.py` to verify.
3.  **Commit & Push**:

```bash
# Add changed files
git add .

# Commit with a message describing the change
git commit -m "Fixed typo in header"

# Push to GitHub
git push origin main
```

4.  **Auto-Deploy**: Go to your Streamlit Cloud dashboard. You will see the app updating (often within seconds).
