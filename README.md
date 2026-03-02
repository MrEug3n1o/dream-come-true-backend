# Dream Maker — Backend API

A FastAPI backend for the Dream Maker charity platform.

## Stack
- **FastAPI** — web framework
- **SQLAlchemy** — ORM
- **PostgreSQL** (production) / **SQLite** (development)
- **JWT** — authentication via `python-jose`
- **Bcrypt** — password hashing via `passlib`

---

## Project Structure

```
dream_maker/
├── app/
│   ├── main.py          # FastAPI app, middleware, router registration
│   ├── config.py        # Settings from environment variables
│   ├── database.py      # Engine, session, Base
│   ├── auth.py          # JWT logic, password hashing, auth dependencies
│   ├── models/
│   │   ├── models.py    # SQLAlchemy ORM models (User, Dream)
│   │   └── schemas.py   # Pydantic request/response schemas
│   └── routers/
│       ├── auth.py      # POST /auth/register, /auth/login
│       ├── users.py     # GET /users/me, /users/me/dreams
│       ├── dreams.py    # GET/POST /dreams — public + user actions
│       └── admin.py     # /admin/* — full CRUD, user management
├── seed.py              # Dev seed data
├── requirements.txt
└── .env.example
```

---

## Setup

### 1. Clone & install dependencies

```bash
cd dream_maker
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 2. Configure environment

```bash
cp .env.example .env
# Edit .env with your database URL and a strong SECRET_KEY
```

**Development (SQLite — no setup needed):**
```
DATABASE_URL=sqlite:///./dreammaker.db
SECRET_KEY=any-random-string-here
```

**Production (PostgreSQL):**
```
DATABASE_URL=postgresql://user:password@localhost:5432/dreammaker
SECRET_KEY=your-very-strong-secret-key
```

### 3. Seed sample data (optional)

```bash
python seed.py
```

This creates two accounts:
- **Admin:** `admin@dreammaker.org` / `admin123`
- **Donor:** `maria@example.com` / `password123`

### 4. Run the server

```bash
uvicorn app.main:app --reload
```

API available at: http://localhost:8000  
Interactive docs: http://localhost:8000/docs

---

## API Reference

### Authentication

| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| POST | `/auth/register` | — | Create a new account |
| POST | `/auth/login` | — | Get JWT token (form: `username` + `password`) |
| GET | `/auth/me` | ✅ User | Get current user profile |

### Dreams (Public / User)

| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| GET | `/dreams` | — | List dreams with filters |
| GET | `/dreams/match` | — | Smart Match algorithm (3 random results) |
| GET | `/dreams/{id}` | — | Get dream details |
| POST | `/dreams/{id}/fulfill` | ✅ User | Reserve a dream |

**Query params for `GET /dreams`:**
- `format` — `ONLINE` or `OFFLINE`
- `person_type` — `CHILD`, `ELDERLY`, `ANIMAL_SHELTER`, `OTHER`
- `max_budget` — decimal number
- `status` — `AVAILABLE`, `RESERVED`, `COMPLETED`
- `sort_by` — `date` or `budget`

**Query params for `GET /dreams/match`** (all required):
- `format`, `person_type`, `max_budget`

### Admin

| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| POST | `/admin/dreams` | 🔐 Admin | Create a dream |
| PUT | `/admin/dreams/{id}` | 🔐 Admin | Edit a dream |
| DELETE | `/admin/dreams/{id}` | 🔐 Admin | Delete a dream |
| PATCH | `/admin/dreams/{id}/status` | 🔐 Admin | Change dream status |
| GET | `/admin/users` | 🔐 Admin | List all users |
| GET | `/admin/users/{id}` | 🔐 Admin | Get user by ID |
| PATCH | `/admin/users/{id}/toggle-admin` | 🔐 Admin | Promote/demote admin |

### Users

| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| GET | `/users/me` | ✅ User | Profile |
| GET | `/users/me/dreams` | ✅ User | My fulfilled dreams |

---

## Dream Status Workflow

```
AVAILABLE ──► RESERVED (via POST /dreams/{id}/fulfill)
    ▲               │
    │               ▼
    └──────── COMPLETED (via PATCH /admin/dreams/{id}/status)
```

---

## Production Notes

- Replace `SECRET_KEY` with a cryptographically random 32+ byte string
- Set `APP_ENV=production` to restrict CORS origins
- Use **Alembic** for database migrations instead of `create_all`
- Store `DATABASE_URL` and `SECRET_KEY` in a secrets manager, not in `.env`
- Consider rate-limiting the `/auth/login` endpoint
