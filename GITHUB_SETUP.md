# How to Push Your Project to GitHub

Currently, your project and its git history (with the 6 commits from Brian and Harold) exist only on your **local computer**. To see them on GitHub, follow these steps:

## Step 1: Create a New Repository on GitHub
1. Go to [github.com/new](https://github.com/new).
2. Repository name: `lichess-opening-coach` (or whatever you prefer).
3. **Important**: Do NOT check "Initialize with README", "Add .gitignore", or "Choose a license". Create an **empty repository**.
4. Click **Create repository**.

## Step 2: Push Your Code
Copy the URL of your new repository (e.g., `https://github.com/bbellamy27/lichess-opening-coach.git`).

Run the following commands in your VS Code terminal (make sure you are in `c:\Users\Brian\chess_analysis\lichess_coach`):

```powershell
# Link your local repo to GitHub
git remote add origin https://github.com/YOUR_USERNAME/YOUR_REPO_NAME.git

# Rename the branch to main (standard practice)
git branch -M main

# Push your code and history
git push -u origin main
```

## Step 3: Verify
Refresh your GitHub page. You should see:
- All your files.
- A "Commits" counter (showing 6 commits).
- Clicking "Commits" will show the history with "Brian" and "Harold" as authors.
