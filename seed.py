"""
Seed the database with sample data for development.
Run with: python seed.py
"""
from app.database import SessionLocal, engine
from app.models.models import Base, User, Dream, ParticipationFormat, PersonType, UserRole
from app.auth import hash_password

Base.metadata.create_all(bind=engine)
db = SessionLocal()

db.query(Dream).delete()
db.query(User).delete()
db.commit()

# ─── Users ────────────────────────────────────────────────────────────────────
admin = User(
    full_name="Admin User",
    email="admin@dreammaker.org",
    password_hash=hash_password("admin123"),
    role=UserRole.ADMIN,
)
donor = User(
    full_name="Maria Kovalenko",
    email="maria@example.com",
    password_hash=hash_password("password123"),
    role=UserRole.DONOR,
)
child_dreamer = User(
    full_name="Sofia (guardian: Olena)",
    email="sofia@example.com",
    password_hash=hash_password("password123"),
    role=UserRole.DREAMER,
    person_type=PersonType.CHILD,
)
elder_dreamer = User(
    full_name="Mykola Petrenko",
    email="mykola@example.com",
    password_hash=hash_password("password123"),
    role=UserRole.DREAMER,
    person_type=PersonType.ELDERLY,
)
db.add_all([admin, donor, child_dreamer, elder_dreamer])
db.commit()
for u in [admin, donor, child_dreamer, elder_dreamer]:
    db.refresh(u)

# ─── Dreams ───────────────────────────────────────────────────────────────────
dreams = [
    Dream(
        dreamer_id=child_dreamer.user_id,
        title="Learn to Draw Anime Characters",
        description="Sofia, 9, has been sketching for years and dreams of becoming an artist.",
        participation_format=ParticipationFormat.ONLINE,
        target_budget=45.00,
        is_completed=False,
    ),
    Dream(
        dreamer_id=elder_dreamer.user_id,
        title="A Day Trip to the Botanical Garden",
        description="Mykola, 78, hasn't left his care home in six months and longs to see flowers.",
        participation_format=ParticipationFormat.OFFLINE,
        target_budget=120.00,
        is_completed=False,
    ),
    Dream(
        dreamer_id=child_dreamer.user_id,
        title="Birthday Party in Hospital",
        description="Dmytro, 7, is spending his birthday during treatment.",
        participation_format=ParticipationFormat.HYBRID,
        target_budget=80.00,
        is_completed=True,
    ),
]
db.add_all(dreams)
db.commit()
db.close()

print("✅ Database seeded!")
print("   Admin:   admin@dreammaker.org / admin123")
print("   Donor:   maria@example.com / password123")
print("   Dreamer: sofia@example.com / password123")
