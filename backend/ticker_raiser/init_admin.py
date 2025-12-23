"""
Admin initialization script - Creates default admin/problem setter user
Run this once to set up the admin user in the database
"""

from app.core.database import SessionLocal, engine, Base
from app.crud.auth import UserCRUD
from app.core.security import hash_password

def init_admin_user():
    """Create admin problem setter user if it doesn't exist"""
    # Create tables first
    Base.metadata.create_all(bind=engine)
    
    db = SessionLocal()
    try:
        # Check if admin already exists
        admin = UserCRUD.get_user_by_email(db, "admin@ticketraiser.com")
        if admin:
            print("✓ Admin user already exists")
            return
        
        # Create admin user
        admin_user = UserCRUD.create_user(
            db,
            username="admin",
            email="admin@ticketraiser.com",
            hashed_password=hash_password("Admin@123456"),
            role="PROBLEM_SETTER"
        )
        
        print(f"✓ Admin user created successfully!")
        print(f"  Email: admin@ticketraiser.com")
        print(f"  Password: Admin@123456")
        print(f"  Role: PROBLEM_SETTER")
        
    except Exception as e:
        print(f"✗ Error creating admin user: {str(e)}")
    finally:
        db.close()

if __name__ == "__main__":
    init_admin_user()
