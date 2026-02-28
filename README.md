# LeadGen Platform – MVP

A lead generation platform with async jobs, multi-source data collection, lead scoring, and export. This document describes the current MVP and how to run it.

## Features (MVP)

- **Async generation jobs** – Start a job, poll status, retrieve leads
- **Google Places** – Primary data source (official API, compliant)
- **Lead deduplication** – Place ID / name+address+domain dedupe
- **Basic lead scoring** – Rating, reviews, website, phone, address
- **CSV export** – Filter and export leads

## Project Structure

```
backend/          # FastAPI app
  app/
    api/          # Routes: jobs, leads, auth, campaigns, export, health
    models/       # Lead, ScrapeJob (GenerationJob), User
    services/     # run_generation_job, scoring
    providers/    # Google Places client
frontend/         # Static dashboard (HTML + JS)
docker-compose.yml
```

## Quick Start

### 1. Create environment file

```bash
cp .env.example .env
```

### 2. Configure required API keys

Edit `.env` and set:

```bash
# Required for lead generation (Google Places)
GOOGLE_PLACES_API_KEY=your_google_places_api_key_here
```

**Get a Google Places API key:**
1. Go to [Google Cloud Console](https://console.cloud.google.com/apis/credentials)
2. Create or select a project
3. Enable "Places API" and "Places API (New)"
4. Create an API key (Credentials → Create credentials → API key)
5. Paste the key into `GOOGLE_PLACES_API_KEY`

### 3. Start services

```bash
docker compose up --build
```

This starts:
- **PostgreSQL** on `localhost:5432`
- **Redis** on `localhost:6379`
- **API** on `http://localhost:8000`
- **Celery worker** (for async jobs; MVP uses BackgroundTasks)

### 4. Open the dashboard

```bash
cd frontend
python3 -m http.server 8080
```

Then visit `http://localhost:8080`.

## Jobs → Leads Flow

1. **Create job** – `POST /api/v1/jobs` with query, location, max_results
2. **Job runs in background** – Scrapes Google Places, dedupes, scores, inserts leads
3. **Poll status** – `GET /api/v1/jobs/{id}` until `status` is `completed` or `failed`
4. **Fetch leads** – `GET /api/v1/jobs/{id}/leads` or `GET /api/v1/leads?job_id=...`
5. **Export** – `GET /api/v1/leads/export/csv?job_id=...`

### Example queries

```bash
# Create a job
curl -X POST http://localhost:8000/api/v1/jobs \
  -H "Content-Type: application/json" \
  -d '{"query": "restaurants", "location": "San Francisco", "max_results": 20}'

# List jobs
curl http://localhost:8000/api/v1/jobs

# Get job status
curl http://localhost:8000/api/v1/jobs/{job_id}

# Get leads for a job
curl http://localhost:8000/api/v1/jobs/{job_id}/leads

# Search leads (filter)
curl "http://localhost:8000/api/v1/leads?city=San%20Francisco&min_score=50&limit=50"

# Export to CSV
curl "http://localhost:8000/api/v1/leads/export/csv?job_id={job_id}" -o leads.csv
```

## API Overview

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/health` | GET | Root health check |
| `/api/v1/health` | GET | API health check |
| `/api/v1/jobs` | POST | Create generation job |
| `/api/v1/jobs` | GET | List jobs |
| `/api/v1/jobs/{id}` | GET | Get job status |
| `/api/v1/jobs/{id}/leads` | GET | Get leads for job |
| `/api/v1/leads` | GET | List/search leads (q, city, min_score, job_id) |
| `/api/v1/leads/{id}` | GET | Get single lead |
| `/api/v1/leads/export/csv` | GET | Export leads as CSV |

## Environment Variables (.env template)

| Variable | Description | Default |
|----------|-------------|---------|
| `APP_NAME` | API title | LeadGen MVP API |
| `API_PREFIX` | API path prefix | /api/v1 |
| `DEBUG` | Debug mode | false |
| `DATABASE_URL` | PostgreSQL (asyncpg) | postgresql+asyncpg://postgres:postgres@db:5432/leadgen |
| `REDIS_URL` | Redis URL | redis://redis:6379/0 |
| `CELERY_BROKER_URL` | Celery broker | redis://redis:6379/1 |
| `CELERY_RESULT_BACKEND` | Celery results | redis://redis:6379/2 |
| `GOOGLE_PLACES_API_KEY` | **Required** for Google Places | (empty) |
| `GOOGLE_CUSTOM_SEARCH_*` | Optional, for future sources | (empty) |
| `BING_SEARCH_API_KEY` | Optional | (empty) |
| `HUNTER_API_KEY` | Optional, email finder | (empty) |
| `SNOV_API_KEY` | Optional | (empty) |
| `APOLLO_API_KEY` | Optional | (empty) |
| `CORS_ORIGINS` | Allowed origins (comma-separated) | http://localhost:8080 |
| `REQUEST_TIMEOUT_SECONDS` | HTTP timeout for providers | 20 |

For **local development** (outside Docker), use `localhost` instead of `db` and `redis` in URLs:
- `DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/leadgen`
- `REDIS_URL=redis://localhost:6379/0`

## Job Error Messages

If the Google Places API key is missing or invalid, jobs will fail immediately with a clear message:

- `"Google Places API key is missing or empty. Set GOOGLE_PLACES_API_KEY in your .env file."`

Check `GET /api/v1/jobs/{id}` → `error_message` when `status` is `failed`.

## Notes

- Tables are auto-created on API startup (no migrations yet).
- `email` is not populated in the MVP; Google Places does not provide direct email data.
- Additional providers can be added under `backend/app/providers/` and wired in `services/generator.py`.
