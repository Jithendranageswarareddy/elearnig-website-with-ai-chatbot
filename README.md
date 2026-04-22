# eLearning Website with AI Chatbot

This repository contains a Django-based eLearning platform with role-based dashboards (Student, Faculty, Principal), syllabus PDF ingestion, and AI-assisted curriculum chat.

## Tech Stack

- Django
- SQLite (local development)
- Optional PostgreSQL via `DATABASE_URL` (recommended for Vercel demo)
- Optional Celery/Redis
- PDF processing with PyMuPDF

## Local Run

1. Create and activate virtual environment.
2. Install dependencies:

```powershell
pip install -r requirements.txt
```

3. Run migrations:

```powershell
python .\elearning_project\manage.py migrate
```

4. Start the server:

```powershell
python .\run_server.py
```

## Deploy to Vercel

### 1) Push to GitHub

```powershell
git init
git add .
git commit -m "Initial deploy-ready setup"
git branch -M main
git remote add origin https://github.com/Jithendranageswarareddy/elearnig-website-with-ai-chatbot.git
git push -u origin main
```

### 2) Import in Vercel

- Go to Vercel dashboard
- Import the GitHub repository
- Keep default framework detection

### 3) Required Environment Variables (Vercel)

- `DJANGO_SECRET_KEY`
- `DJANGO_ALLOWED_HOSTS` = `.vercel.app`
- `DJANGO_CSRF_TRUSTED_ORIGINS` = `https://*.vercel.app`
- `DJANGO_DEBUG` = `0`

Recommended for full writable demo:

- `DATABASE_URL` (PostgreSQL connection string, e.g., Neon/Supabase)

Optional:

- `OPENROUTER_API_KEY`
- `REDIS_CACHE_URL`

## Important Demo Note

For Vercel, using SQLite is not suitable for a full interactive demo because serverless file systems are not persistent for database writes. Use PostgreSQL (`DATABASE_URL`) for login, chat history, bookmarks, and progress tracking in live demo.
