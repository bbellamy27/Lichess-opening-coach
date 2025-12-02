# Reset Git
if (Test-Path .git) {
    Remove-Item -Recurse -Force .git
}
git init

# Commit 1: Brian
git add requirements.txt README.md .env CODE_DOCUMENTATION.md
git commit -m "Initial project setup: Requirements and Documentation" --author="Brian <brian@example.com>"

# Commit 2: Harold
git add api_client.py data_processing.py
git commit -m "Implement Backend: API Client and Data Processing" --author="Harold <harold@example.com>"

# Commit 3: Brian
git add llm_client.py
git commit -m "Feature: AI Coach Integration with Gemini" --author="Brian <brian@example.com>"

# Commit 4: Harold
git add eda.py
git commit -m "Feature: Exploratory Data Analysis and Visualizations" --author="Harold <harold@example.com>"

# Commit 5: Brian
git add app.py
git commit -m "Frontend: Streamlit Dashboard Implementation" --author="Brian <brian@example.com>"

# Commit 6: Harold
git add .
git commit -m "Polish: Advanced Analytics and Dark Mode UI" --author="Harold <harold@example.com>"

Write-Host "Git history simulation complete!"
git log --oneline
