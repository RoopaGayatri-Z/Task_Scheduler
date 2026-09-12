# Student Task Scheduler — Conflict-Aware Task & Revision Tracker

A cloud-deployed task scheduler for students: assign start/due dates and
priority to tasks, get automatic conflict warnings when high-priority tasks
overlap, and track weekly syllabus revision alongside regular assignments.

## Architecture

```
┌─────────────────┐        REST API (HTTPS/JSON)        ┌──────────────────┐        ┌───────────────────┐
│ Streamlit App    │ ───────────────────────────────────▶ │ FastAPI Backend  │ ─────▶ │ Supabase Postgres │
│ (Streamlit Cloud)│ ◀─────────────────────────────────── │ (Render)         │ ◀───── │ (cloud-hosted DB) │
└─────────────────┘                                        └──────────────────┘        └───────────────────┘
```

- **Frontend:** Streamlit (Python), deployed on Streamlit Community Cloud
- **Backend:** FastAPI (Python), deployed on Render as a Web Service
- **Database:** Supabase (managed PostgreSQL)
- **Communication:** Frontend calls backend exclusively via REST endpoints over HTTPS — no direct DB access from the frontend

## Repo structure

```
task-scheduler/
├── backend/
│   ├── main.py          # FastAPI app + all REST endpoints
│   ├── database.py      # SQLAlchemy engine/session setup
│   ├── models.py        # ORM model (Task table)
│   ├── schemas.py        # Pydantic request/response schemas
│   ├── crud.py           # DB operations + conflict-detection logic
│   ├── requirements.txt
│   └── .env.example
├── frontend/
│   ├── app.py             # Streamlit UI, calls backend via `requests`
│   ├── requirements.txt
│   └── .streamlit/secrets.toml.example
└── README.md
```

## 1. Set up the database (Supabase)

1. Go to https://supabase.com → sign in with GitHub → **New Project**.
2. Pick a name/region, set a DB password (save it — you need it below).
3. Once it's provisioned: **Project Settings → Database → Connection string → URI**.
4. Copy that string — this is your `DATABASE_URL`. Replace `[YOUR-PASSWORD]` in it with the password you set.
   - If Render's free tier can't connect directly, use the **Transaction pooler** connection string shown on the same page instead (port 6543) — Supabase's docs flag this as the fix for serverless/free-tier connection limits.

You don't need to create the `tasks` table manually — `Base.metadata.create_all(engine)` in `main.py` creates it automatically the first time the backend starts.

## 2. Deploy the backend (Render)

1. Push the `backend/` folder (or the whole repo) to a GitHub repo.
2. https://render.com → **New → Web Service** → connect your GitHub repo.
3. Settings:
   - **Root Directory:** `backend`
   - **Build Command:** `pip install -r requirements.txt`
   - **Start Command:** `uvicorn main:app --host 0.0.0.0 --port $PORT`
4. **Environment → Add Environment Variable:** `DATABASE_URL` = the Supabase connection string from step 1.
5. Deploy. Render gives you a URL like `https://your-backend-name.onrender.com`.
6. Visit `https://your-backend-name.onrender.com/docs` — this is your **auto-generated API documentation** (Swagger UI), free from FastAPI. Screenshot/link this for your submission's API documentation deliverable.

## 3. Deploy the frontend (Streamlit Community Cloud)

1. Push `frontend/` to the same (or another) GitHub repo.
2. https://share.streamlit.io → sign in with GitHub → **New app**.
3. Point it at your repo, set **Main file path** to `frontend/app.py`.
4. Under **Advanced settings → Secrets**, paste:
   ```
   API_URL = "https://your-backend-name.onrender.com"
   ```
   (use your actual Render URL from step 2)
5. Deploy. You get a public URL like `https://your-app-name.streamlit.app` — this is your submission's deployed application URL.

## API Endpoints

| Method | Endpoint                  | Description                                  |
|--------|---------------------------|-----------------------------------------------|
| GET    | `/`                        | Health check                                  |
| POST   | `/tasks`                   | Create a task                                 |
| GET    | `/tasks?category=`         | List all tasks (optional category filter)     |
| GET    | `/tasks/{id}`              | Get one task                                  |
| PUT    | `/tasks/{id}`               | Update a task (partial updates supported)     |
| DELETE | `/tasks/{id}`               | Delete a task                                 |
| GET    | `/tasks/conflicts/check`   | List overlapping high-priority pending tasks   |

Full interactive docs (auto-generated, no extra work needed): `<your-render-url>/docs`

## Database schema

**`tasks`**

| Column       | Type      | Notes                                      |
|--------------|-----------|---------------------------------------------|
| id           | integer   | primary key                                 |
| title        | string    | required                                    |
| description  | string    | optional                                    |
| category     | enum      | `assignment` / `revision` / `general`       |
| subject      | string    | optional; used when category = `revision`   |
| start_date   | date      | required                                    |
| due_date     | date      | required                                    |
| priority     | enum      | `low` / `medium` / `high`                   |
| status       | enum      | `pending` / `done`                          |
| created_at   | timestamp | auto-set                                    |
| updated_at   | timestamp | auto-updated                                |

## Local development

```bash
# backend
cd backend
cp .env.example .env   # fill in your Supabase DATABASE_URL
pip install -r requirements.txt
uvicorn main:app --reload

# frontend (separate terminal)
cd frontend
mkdir -p .streamlit && cp .streamlit/secrets.toml.example .streamlit/secrets.toml
# edit secrets.toml -> API_URL = "http://localhost:8000"
pip install -r requirements.txt
streamlit run app.py
```
