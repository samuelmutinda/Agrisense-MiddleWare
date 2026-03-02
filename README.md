# Agrisense Middleware

FastAPI-based middleware for the Agrisense platform. Provides REST APIs for tenants, users, harvests, devices, and integrations (e.g. ChirpStack).

## Prerequisites

- **Python 3.11+**
- **PostgreSQL 14+**
- **Docker & Docker Compose** (for ChirpStack; optional if you use an existing ChirpStack instance)

---

## 1. PostgreSQL setup

### Install PostgreSQL

**macOS (Homebrew):**
```bash
brew install postgresql@14
brew services start postgresql@14
```

**Ubuntu/Debian:**
```bash
sudo apt update
sudo apt install postgresql postgresql-contrib
sudo systemctl start postgresql
```

**Windows:**  
Download and run the installer from [postgresql.org](https://www.postgresql.org/download/windows/).

### Create the database and user

Connect to PostgreSQL (as a superuser, e.g. `postgres`):

```bash
# macOS/Linux: switch to postgres user or use local socket
psql postgres

# Or with username and host
psql -U postgres -h localhost
```

In the `psql` shell:

```sql
-- Create a dedicated user (optional but recommended)
CREATE USER agrisense WITH PASSWORD 'your_password';

-- Create the database (owned by that user)
CREATE DATABASE agrisense OWNER agrisense;

-- Grant privileges
GRANT ALL PRIVILEGES ON DATABASE agrisense TO agrisense;

-- Connect to the new database to allow future schema creation
\c agrisense

-- Allow the user to create objects in public schema
GRANT ALL ON SCHEMA public TO agrisense;
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO agrisense;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO agrisense;

\q
```

**Connection URL format:**

- With user/password:  
  `postgresql+asyncpg://agrisense:your_password@localhost:5432/agrisense`
- Same machine, default user:  
  `postgresql+asyncpg://localhost:5432/agrisense`

The app uses **asyncpg** (async driver). The URL must use the `postgresql+asyncpg://` scheme (see `.env` below).

---

## 2. ChirpStack setup (Docker)

ChirpStack is the LoRaWAN network server. The middleware talks to its API and receives webhooks from it. Use Docker to run ChirpStack locally.

### Install Docker and Docker Compose

- **macOS / Windows:** Install [Docker Desktop](https://www.docker.com/products/docker-desktop/) (includes Compose).
- **Linux:** Install [Docker Engine](https://docs.docker.com/engine/install/) and [Docker Compose](https://docs.docker.com/compose/install/).

### Run ChirpStack with Docker Compose

```bash
# Clone the official ChirpStack Docker setup
git clone https://github.com/chirpstack/chirpstack-docker.git
cd chirpstack-docker

# Start all services (first run may show DB init messages)
docker compose up -d

# Check that containers are running
docker compose ps
```

- **Web UI & API:** http://localhost:8080  
- **Default login:** See the repo’s README or `docker-compose` comments (e.g. `admin` / `admin` or as stated in the project).

### Create an API key in ChirpStack

The middleware needs a ChirpStack API token to create tenants, applications, devices, etc.

1. Open http://localhost:8080 and log in.
2. Go to **Administration** → **API keys** (or **Users** → your user → **API keys**).
3. Create a new API key with the required permissions (e.g. full access or at least tenant/application/device management).
4. Copy the generated token; this is `CHIRPSTACK_API_TOKEN` in the middleware `.env`.

### Connect ChirpStack to the middleware (webhooks)

So that ChirpStack can send events (e.g. uplinks) to the middleware:

1. In ChirpStack, add an **HTTP integration** (or webhook) for your application.
2. Set the URL to your middleware webhook endpoint.  
   If ChirpStack runs in Docker and the middleware runs on the host:
   - **macOS / Windows:** `http://host.docker.internal:9000/api/integrations/chirpstack/events`
   - **Linux:** Use your machine’s IP, e.g. `http://192.168.1.100:9000/api/integrations/chirpstack/events`
3. Set the HTTP header: **Authorization:** `Bearer <your-webhook-token>`  
   Use the same value you set as `CHIRPSTACK_WEBHOOK_TOKEN` in the middleware `.env` (see below).

The middleware expects `POST` requests with that Bearer token; the token is checked against `CHIRPSTACK_WEBHOOK_TOKEN`.

---

## 3. Project setup

### Clone and virtual environment

Use a virtual environment so project dependencies stay isolated from the system Python.

1. **Go to the project directory** (if you haven’t already):
   ```bash
   cd Agrisense_Middleware
   ```

2. **Create a virtual environment** (Python 3.11+):
   ```bash
   python3 -m venv .venv
   ```
   On some systems the command may be `python -m venv .venv`. If you use multiple Python versions, ensure you use 3.11 or newer (e.g. `python3.11 -m venv .venv`).

3. **Activate the virtual environment:**
   - **macOS / Linux:**
     ```bash
     source .venv/bin/activate
     ```
   - **Windows (Command Prompt):**
     ```cmd
     .venv\Scripts\activate.bat
     ```
   - **Windows (PowerShell):**
     ```powershell
     .venv\Scripts\Activate.ps1
     ```
   When active, your prompt usually shows `(.venv)`.

4. **Upgrade pip (recommended):**
   ```bash
   pip install --upgrade pip
   ```

5. **Install dependencies from `requirements.txt`:**
   ```bash
   pip install -r requirements.txt
   ```
   This installs FastAPI, SQLAlchemy, asyncpg, JWT and bcrypt libraries, ChirpStack HTTP client, and the rest of the project requirements. Re-run this command whenever `requirements.txt` changes.

### Environment variables

Create a `.env` file in the project root. Below is a full example with comments; remove or change values as needed.

```bash
# -----------------------------------------------------------------------------
# Database (required)
# Use the asyncpg driver. Replace user, password, host and DB name as needed.
# -----------------------------------------------------------------------------
DATABASE_URL=postgresql+asyncpg://agrisense:your_password@localhost:5432/agrisense

# -----------------------------------------------------------------------------
# JWT (required)
# Used to sign access tokens. Use a long random string in production.
# -----------------------------------------------------------------------------
JWT_SECRET_KEY=your-long-random-secret-key-change-in-production

# -----------------------------------------------------------------------------
# Sysadmin (optional)
# If both are set, the app creates/updates a sysadmin user in the "sysadmin"
# tenant on startup. Omit both to skip.
# -----------------------------------------------------------------------------
SYSADMIN_EMAIL=admin@example.com
SYSADMIN_PASSWORD=your-secure-password-at-least-8-chars

# -----------------------------------------------------------------------------
# ChirpStack (required for device integrations)
# After starting ChirpStack with Docker (see "ChirpStack setup" above):
# - CHIRPSTACK_BASE_URL: ChirpStack app URL (no trailing slash), e.g. http://localhost:8080
# - CHIRPSTACK_API_TOKEN: From ChirpStack UI → Administration → API keys
# - CHIRPSTACK_WEBHOOK_TOKEN: Any secret string; use the same value when configuring
#   the ChirpStack HTTP integration (Authorization: Bearer <this-token>)
# -----------------------------------------------------------------------------
CHIRPSTACK_BASE_URL=http://localhost:8080
CHIRPSTACK_API_TOKEN=your-chirpstack-api-token-from-ui
CHIRPSTACK_WEBHOOK_TOKEN=your-webhook-secret-token

# -----------------------------------------------------------------------------
# Optional
# -----------------------------------------------------------------------------
CORS_ORIGINS=http://localhost:3000,http://localhost:8081
```

**Quick reference:**

| Variable | Where to get it |
|----------|-----------------|
| `DATABASE_URL` | Your PostgreSQL user, password, host, and database name. Must use `postgresql+asyncpg://`. |
| `JWT_SECRET_KEY` | Generate a long random string (e.g. `openssl rand -hex 32`). |
| `SYSADMIN_EMAIL` / `SYSADMIN_PASSWORD` | Choose any admin email and strong password; used to auto-create sysadmin on startup. |
| `CHIRPSTACK_BASE_URL` | ChirpStack URL, e.g. `http://localhost:8080` when run via Docker. |
| `CHIRPSTACK_API_TOKEN` | ChirpStack web UI → **Administration** → **API keys** → create key → copy token. |
| `CHIRPSTACK_WEBHOOK_TOKEN` | Pick a secret string; set the same value in ChirpStack’s HTTP integration as `Authorization: Bearer <token>`. |

- **DATABASE_URL** must use `postgresql+asyncpg://` for the async driver.
- If **SYSADMIN_EMAIL** and **SYSADMIN_PASSWORD** are both set, the app creates (or updates) a sysadmin user and the `sysadmin` tenant on startup.
- Tables are created automatically on first run (`Base.metadata.create_all` in lifespan).

### Run the app

From the project root:

```bash
python main.py
```

Or with uvicorn directly:

```bash
uvicorn app.main:app --host 0.0.0.0 --port 9000 --reload
```

The API is served at **http://localhost:9000**. The API prefix is `/api` (e.g. `http://localhost:9000/api/...`).

---

## 4. API documentation

FastAPI exposes interactive API docs at the **root** of the app (not under `/api`):

| Doc type   | URL                      |
|-----------|---------------------------|
| Swagger UI | http://localhost:9000/docs |
| ReDoc      | http://localhost:9000/redoc |

Open either URL in a browser to explore and call endpoints.

- **Swagger UI (`/docs`):** Try out requests; use “Authorize” to set a Bearer token after logging in.
- **ReDoc (`/redoc`):** Read-only, good for sharing and reading.

### Getting a token for “Authorize”

1. **Login:**  
   `POST /api/auth/token`  
   Body (form): `username=<email>&password=<password>`
2. Copy the `access_token` from the response.
3. In Swagger UI, click **Authorize** and enter:  
   `Bearer <access_token>`

Admin endpoints require a user with the **admin** role (e.g. the sysadmin created via `SYSADMIN_EMAIL` / `SYSADMIN_PASSWORD`).

---

## 5. Optional: create admin via script

If you did not set sysadmin env vars, you can create an admin user once the app and DB are running:

```bash
python scripts/create_admin_user.py --email admin@example.com --password yourpassword
```

Or run the script and follow the prompts.

---

## 6. Scripts

| Script | Purpose |
|--------|--------|
| `scripts/create_admin_user.py` | Create or update an admin user (and admin role / tenant if missing). |
| `scripts/drop_all_tables.py` | Drop all application tables (destructive; use with care). |
| `scripts/sync_tenants_from_chirpstack.py` | Sync tenants from ChirpStack into the database. |

Run from the project root, e.g. `python scripts/create_admin_user.py`.

---

## Summary

1. **PostgreSQL:** Install, create database and user, set `DATABASE_URL` with `postgresql+asyncpg://`.
2. **ChirpStack (optional):** Run with Docker (`chirpstack-docker`), create an API key, configure HTTP integration to `http://host.docker.internal:9000/api/integrations/chirpstack/events` with Bearer token = `CHIRPSTACK_WEBHOOK_TOKEN`.
3. **App:** `pip install -r requirements.txt`, configure `.env` (see table above), run `python main.py`.
4. **Docs:** Open **http://localhost:9000/docs** (Swagger) or **http://localhost:9000/redoc** (ReDoc).
5. **Sysadmin:** Set `SYSADMIN_EMAIL` and `SYSADMIN_PASSWORD` in `.env` for automatic creation on startup, or use `scripts/create_admin_user.py` once.
