# DA3 Runbook - run top to bottom (PowerShell, from the repo root)

Time budget if nothing breaks: ~3.5 h (setup 30 min, Q2 60 min, Q1 60 min, report 45 min, video 25 min).
Take a screenshot at every step marked **[SHOT]**.

## What to open (and why)

| What | URL | Used for |
|---|---|---|
| GitHub repo | https://github.com/RoopaGayatri-Z/Task_Scheduler | push the `assignment-3` branch |
| Supabase dashboard | https://supabase.com/dashboard | Table Editor + SQL Editor (password before/after, roles) |
| Render dashboard | https://dashboard.render.com | DA1 backend: only to update `DATABASE_URL` after the password reset |
| Docker Desktop | (app on your PC) | must be running for every `docker` command |
| Local API docs | http://localhost:8080/docs | Swagger for the 3-instance stack |
| Local frontend | http://localhost:8501 | Streamlit login / QR / app |

---

## Step 0 - Fix the leaked DB password (10 min, do this first)

`backend/.env` was committed to your **public** repo (in the very first commit), so the Supabase password is public.

1. Supabase -> Project Settings -> Database -> **Reset database password**. Copy the new one.
2. Render -> your backend service -> Environment -> edit `DATABASE_URL` with the new password -> Save (redeploys).
   If you skip this, your live DA1 app stops working.
3. In the repo:
   ```powershell
   git checkout -b assignment-3
   git rm --cached backend/.env
   ```
   (the updated `.gitignore` in this zip now blocks `.env`)

## Step 1 - Install the new files and create your local `.env`

1. Copy everything from this zip over your repo (keep your own `.venv`).
2. `backend/.env` (never commit it):
   ```
   DATABASE_URL=<Supabase transaction-pooler URL with the NEW password>
   JWT_SECRET=<output of: python -c "import secrets; print(secrets.token_urlsafe(48))">
   ```
3. Install new packages in your venv:
   ```powershell
   pip install -r backend/requirements.txt
   pip install -r frontend/requirements.txt
   ```
   (if bcrypt tries to compile: `pip install bcrypt --only-binary :all:`)
4. Start the backend once so the new `users` table is created:
   ```powershell
   cd backend
   uvicorn main:app --port 8000
   ```
   Leave it running; open a second terminal for the next steps.

---

# QUESTION 2 (do this first - Q1's load test needs a login token)

## 2a - Salted password hashes, before / after

Honest framing for the report: the "before" state is a legacy account with a plain-text password inserted by hand to demonstrate the migration.

1. Supabase -> SQL Editor:
   ```sql
   INSERT INTO users (username, password_hash, role, totp_enabled)
   VALUES ('legacy_demo', 'student123', 'student', false);
   ```
   Table Editor -> `users` **[SHOT: BEFORE - plain text visible]**
2. Run the migration (from `backend/`, venv active):
   ```powershell
   python migrate_hash_passwords.py
   ```
   Refresh Table Editor **[SHOT: AFTER - value starts with $2b$...]**
3. Delete the demo row (it has MFA off):
   ```sql
   DELETE FROM users WHERE username = 'legacy_demo';
   ```
4. Also register a real account (step 2b) - its row shows a bcrypt hash too.

## 2b - TOTP MFA + role-restricted update/delete

1. New terminal, from repo root:
   ```powershell
   $env:API_URL="http://localhost:8000"; streamlit run frontend/app.py
   ```
2. Register tab -> create user `snow` (or any name) -> scan the QR with Google/Microsoft Authenticator **[SHOT: QR page - blur the key]**.
3. Log in with password + 6-digit code **[SHOT: app with "Signed in as ... (student)"]**. Also **[SHOT: wrong code -> error]**.
4. Create a second account `viewer_demo` (scan it into the authenticator too), then in Supabase SQL Editor:
   ```sql
   UPDATE users SET role = 'viewer' WHERE username = 'viewer_demo';
   ```
5. Get tokens and prove the rules (task id 999999 does not exist, so nothing real is deleted):
   ```powershell
   $b = @{ username="snow"; password="YOUR_PASSWORD"; totp_code="123456" } | ConvertTo-Json
   $student = (Invoke-RestMethod -Method Post -Uri http://localhost:8000/auth/login -ContentType "application/json" -Body $b).access_token

   curl.exe -i -X DELETE http://localhost:8000/tasks/999999                                          # 401  [SHOT]
   curl.exe -i -X DELETE http://localhost:8000/tasks/999999 -H "Authorization: Bearer $student"      # 404 = passed auth [SHOT]

   # log in as viewer_demo the same way -> $viewer
   curl.exe -i -X DELETE http://localhost:8000/tasks/999999 -H "Authorization: Bearer $viewer"       # 403 [SHOT]
   ```
   Also **[SHOT: Swagger /docs -> Authorize]** if you want a visual.

## 2c - Trivy before / after

```powershell
cd backend
docker build -f Dockerfile.insecure -t task-scheduler-backend:before .
docker build -f Dockerfile          -t task-scheduler-backend:after  .
docker image ls task-scheduler-backend           # [SHOT: sizes]
docker run --rm task-scheduler-backend:before whoami   # root
docker run --rm task-scheduler-backend:after  whoami   # appuser

docker run --rm -v /var/run/docker.sock:/var/run/docker.sock aquasec/trivy:latest image --scanners vuln --severity HIGH,CRITICAL task-scheduler-backend:before   # [SHOT]
docker run --rm -v /var/run/docker.sock:/var/run/docker.sock aquasec/trivy:latest image --scanners vuln --severity HIGH,CRITICAL task-scheduler-backend:after    # [SHOT]
```
Read the `Total: N (HIGH: x, CRITICAL: y)` line(s) in each report (add up the OS and Python-package blocks) and fill the table:

| Image | Base | User | Size | CRITICAL | HIGH |
|---|---|---|---|---|---|
| before | python:3.12 | root | | | |
| after | python:3.12-slim | appuser (uid 10001) | | | |

Report whatever numbers you get. If `after` still shows HIGH items, say which package and that it is a base-image issue.

## 2d - Threat agents and regulation (paste-ready)

Regulation: **GDPR.** Why: the app stores personal data of identifiable people (usernames, login credentials, each student's academic deadlines and workload), and GDPR is the general personal-data regulation (HIPAA only covers health data, which this app does not hold). Note: for students in India the DPDP Act 2023 is the closest local law; GDPR is used here because the assignment names it as the general reference.

| Threat agent | What they do | Control implemented | GDPR requirement |
|---|---|---|---|
| External attacker / credential-stuffing bot | Tries leaked or guessed passwords, or steals the database | bcrypt salted hashes (a stolen DB does not reveal passwords) + TOTP MFA (a stolen password alone is not enough) + signed, expiring JWTs | Art. 32 - security of processing: "appropriate technical measures" to protect confidentiality of personal data |
| Malicious or careless insider (a read-only user, or a student trying to change data they should not) | Edits or deletes records without authorisation | Role-based access control: create/update/delete need a token with role `student` or `faculty`; `viewer` gets 403; no token gets 401 | Art. 5(1)(f) - integrity and confidentiality: protect against unauthorised processing |

Limitations to state honestly (shows you understand the gaps): tasks are not yet owned per user (any student can see/edit any task), the TOTP secret is stored unencrypted in the DB, and there is no login rate-limiting yet.

---

# QUESTION 1

## 1a - Run 3 instances behind Nginx

Peak-demand text (paste-ready): *Deadline night. The evening before a CAT/FAT or assignment-submission deadline, hundreds of students open the dashboard within the same hour to check what is due and whether tasks clash. The hardest-hit API is `GET /tasks` (it loads the main dashboard and is read-heavy), followed by `GET /tasks/conflicts/check`.*

```powershell
cd <repo root>
docker compose up -d --build
docker compose ps                                  # [SHOT: backend1-3 + nginx_lb running]
curl.exe -s http://localhost:8080/                  # smoke test
1..9 | ForEach-Object { curl.exe -s http://localhost:8080/instance }     # [SHOT: backend1, backend2, backend3, repeating]
docker compose logs nginx --tail 15                 # [SHOT: instance=backendN in the log lines]
```

## 1b - 1 instance vs 3 instances (same tool, same concurrency)

Get a login token for the load test (keep the Streamlit/venv terminal separate):
```powershell
$b = @{ username="snow"; password="YOUR_PASSWORD"; totp_code="123456" } | ConvertTo-Json
$token = (Invoke-RestMethod -Method Post -Uri http://localhost:8080/auth/login -ContentType "application/json" -Body $b).access_token
```
Run each test twice and record the **second** run (the first warms up connections):
```powershell
# 1 instance
$env:NGINX_CONF="./nginx/nginx.single.conf"; docker compose up -d --force-recreate nginx
docker run --rm httpd:2.4 ab -n 1000 -c 50 -H "Authorization: Bearer $token" http://host.docker.internal:8080/tasks      # [SHOT]

# 3 instances
$env:NGINX_CONF="./nginx/nginx.three.conf";  docker compose up -d --force-recreate nginx
docker run --rm httpd:2.4 ab -n 1000 -c 50 -H "Authorization: Bearer $token" http://host.docker.internal:8080/tasks      # [SHOT]
```
Fill from the ab output: `Requests per second`, `Time per request` (the first one = mean), `Failed requests`.

| Setup | Requests/s | Mean time per request (ms) | Failed |
|---|---|---|---|
| 1 instance | | | |
| 3 instances | | | |
| Improvement | x% | -y% | |

Improvement % = (new - old) / old x 100. Be honest if it is modest: all three containers share your laptop's CPU and every request waits on the remote Supabase database, so gains come mainly from three connection pools instead of one.

## 1c - Failover: before / after

**Before** (retry disabled):
```powershell
docker compose start backend1 backend2 backend3
$env:NGINX_CONF="./nginx/nginx.noretry.conf"; docker compose up -d --force-recreate nginx
```
Terminal A:
```powershell
docker run --rm httpd:2.4 ab -n 5000 -c 50 -H "Authorization: Bearer $token" http://host.docker.internal:8080/tasks
```
Terminal B, about 2 seconds after A starts:
```powershell
docker compose stop backend2
```
Record `Failed requests` and `Non-2xx responses` **[SHOT]**.
(5,000 requests instead of 1,000 only so the test is long enough to stop an instance mid-run - say this in the report.)

**After** (retry on next instance + passive health check):
```powershell
docker compose start backend2
$env:NGINX_CONF="./nginx/nginx.failover.conf"; docker compose up -d --force-recreate nginx
```
Repeat Terminal A / Terminal B exactly the same **[SHOT]**.

| Nginx config | Requests | Failed | Non-2xx |
|---|---|---|---|
| noretry (`proxy_next_upstream off`) | 5000 | | |
| failover (`proxy_next_upstream error timeout http_502 http_503 http_504`, `max_fails=1 fail_timeout=10s`) | 5000 | | expected 0 |

Explain: Nginx marks the stopped instance as failed and transparently retries the request on the next healthy backend, so users never see an error.

## 1d - Diagram + bursting text

Diagram: `docs/architecture_diagram_da3.png` (cloud bursting is the pink dashed component).

Paste-ready explanation: *On deadline night the three baseline containers can saturate. With cloud bursting, a monitor watches Nginx/container CPU and p95 latency; when CPU stays above ~70% (or p95 latency above ~500 ms) for 2 minutes, extra identical backend containers (burst-1..N) are started on a public cloud (e.g. Render or Cloud Run) and added to the Nginx upstream list; they are removed again ~15 minutes after load drops. Because the backend is stateless and all instances use the same Supabase database, burst nodes need no data migration. Chosen because student peaks are short and predictable (deadline nights, exam weeks), so we pay for extra capacity only when needed. Edge/fog computing was rejected: there are no IoT devices or latency-critical local processing in this domain. (Bursting is shown in the design only; it is not implemented.)*

---

## Run the frontend against the 3-instance stack (for the demo video)
```powershell
$env:NGINX_CONF="./nginx/nginx.failover.conf"; docker compose up -d --force-recreate nginx
$env:API_URL="http://localhost:8080"; streamlit run frontend/app.py
```

## Submit
```powershell
git add .
git status            # make sure backend/.env is NOT listed
git commit -m "DA3: docker compose + nginx scaling, bcrypt, TOTP MFA, RBAC, Trivy hardening"
git push -u origin assignment-3
```
Do **not** merge into `main` tonight: Render deploys `main`, and the new backend needs `JWT_SECRET` set there first.

## 3-minute video outline
0:00 app + problem (15 s) - 0:15 `docker compose ps`, instance rotation (30 s) - 0:45 ab 1 vs 3 results table (30 s) - 1:15 stop backend2 mid-test, before/after (40 s) - 1:55 register + QR + login with TOTP (25 s) - 2:20 401 / 403 / 200 rejection demo (20 s) - 2:40 Trivy before/after table + whoami (20 s).
