"""Login and the two seeded accounts (one staff, one patient)."""

from datetime import UTC, datetime

from app import audit, db
from app.auth import DUMMY_HASH, hash_password, issue_token, verify_password
from app.config import Settings
from app.errors import UnauthorizedError
from app.repositories import users as user_repository
from app.schemas import LoginRequest, LoginResponse

# The demo accounts. Only the passwords are secret, and they come from the environment.
STAFF_EMAIL = "staff@beeclinic.test"
PATIENT_EMAIL = "patient@beeclinic.test"

_BAD_LOGIN = "wrong email or password"


def seed_users(settings: Settings) -> list[str]:
    """Create the demo accounts, or refresh a password that changed. Returns the roles seeded.

    Safe to run on every start. A password that is not set means that account is not created.
    """
    accounts = (
        ("user_staff", STAFF_EMAIL, "Front Desk", "staff", settings.staff_password),
        ("user_patient", PATIENT_EMAIL, "Demo Patient", "patient", settings.patient_password),
    )
    seeded: list[str] = []
    with db.get_pool().connection() as conn:
        for user_id, email, name, role, password in accounts:
            if not password:
                continue
            existing = user_repository.get_by_email(conn, email)
            if existing is None:
                user_repository.insert(conn, user_id, email, name, role, hash_password(password))
            elif not verify_password(password, existing["password_hash"]):
                user_repository.update_password(conn, existing["id"], hash_password(password))
            seeded.append(role)
    return seeded


def login(request: LoginRequest, settings: Settings) -> LoginResponse:
    """Check the email and password and return a signed token. One message for every failure."""
    with db.get_pool().connection() as conn:
        user = user_repository.get_by_email(conn, request.email.strip())
    # Always run one hash check, so an unknown email takes as long as a wrong password.
    matches = verify_password(request.password, user["password_hash"] if user else DUMMY_HASH)
    if user is None or not matches:
        audit.record("login_failed")
        raise UnauthorizedError(_BAD_LOGIN)
    token, expires = issue_token(settings.auth_secret, user["id"], user["role"])
    audit.record("login", user_id=user["id"], role=user["role"])
    return LoginResponse(
        token=token,
        role=user["role"],
        name=user["name"],
        expires_at=datetime.fromtimestamp(expires, UTC),
    )
