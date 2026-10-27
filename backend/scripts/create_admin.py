import getpass, sys
from app.database import SessionLocal
from app.models.admin_payments import AdminUser
from app.breathquest_core.security import hash_password

email = (sys.argv[1] if len(sys.argv) > 1 else input("Admin email: ")).strip().lower()
pw = getpass.getpass("Password (min 12 chars): ")
assert len(pw) >= 12, "password too short"
with SessionLocal() as s:
    if s.query(AdminUser).filter(AdminUser.email == email).first():
        sys.exit("admin already exists")
    s.add(AdminUser(email=email, password_hash=hash_password(pw)))
    s.commit()
print("created", email)
