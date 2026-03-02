from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware

from app.config import get_settings
from app.database import Base, engine
from app.routers import auth, users, dreams, admin

settings = get_settings()

# Create all tables on startup (use Alembic in production)
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="Dream Maker API",
    description=(
        "A charity platform connecting donors with people in need. "
        "Browse and fulfill dreams for children, the elderly, animal shelters, and more."
    ),
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# CORS — tighten origins in production
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"] if settings.APP_ENV == "development" else ["https://vovanchu.github.io/Dream-Maker-Project/"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.add_middleware(
    TrustedHostMiddleware,
    allowed_hosts=["*"],
)


# Routers
app.include_router(auth.router)
app.include_router(users.router)
app.include_router(dreams.router)
app.include_router(admin.router)


@app.get("/", tags=["Health"])
def root():
    return {"status": "ok", "message": "Welcome to the Dream Maker API 🌟"}


@app.get("/health", tags=["Health"])
def health_check():
    return {"status": "healthy"}
