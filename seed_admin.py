#! /usr/bin/env python3

# run this once to seed the first admin role

from database import Base, engine, SessionLocal, User, UserRole
from utils import hash_password

def seed_admin():
    Base.metadata.create_all(bind=engine)  # creates only if doesn't exists
    db = SessionLocal()
    try:
        existing_admin = db.query(User).filter(User.role == UserRole.ADMIN).first()
        if existing_admin:
            print("Admin already exists:", existing_admin.name)
            return

        admin = User(
            name="Super Admin",
            email="admin@example.com",
            password_hash=hash_password("admin123"),
            role=UserRole.ADMIN
        )
        db.add(admin)
        db.commit()
        print("Admin seeded successfully:", admin.email)
    finally:
        db.close()

if __name__ == "__main__":
    seed_admin()
