import uuid
from datetime import UTC, datetime

from src.application.company.service import DEFAULT_MATCH_THRESHOLD
from src.domain.company.entities import Company
from src.domain.company.repository import CompanyRepository
from src.domain.user.entities import User, UserRole
from src.domain.user.repository import UserRepository

# Fixed, deterministic — the same row every run, across every environment, without a migration
# data-seed. `Company`/`User` have no natural home in a schema migration; get-or-create here is
# simpler to reason about than seeding.
SYSTEM_COMPANY_ID = uuid.uuid5(
    uuid.NAMESPACE_URL, "ai-talent-match:system:linkedin-scraper:company"
)
SYSTEM_USER_ID = uuid.uuid5(uuid.NAMESPACE_URL, "ai-talent-match:system:linkedin-scraper:user")

_SYSTEM_COMPANY_NAME = "LinkedIn (External Listings)"
_SYSTEM_COMPANY_SLUG = "linkedin-external-listings"
_SYSTEM_USER_EMAIL = "system+linkedin-scraper@ai-talent-match.internal"


def ensure_system_account(
    company_repo: CompanyRepository, user_repo: UserRepository
) -> tuple[Company, User]:
    """Get-or-create the placeholder company/user that own every scraped job — a real recruiter
    account is neither available nor appropriate for a listing nobody at the company actually
    posted. The user is permanently inactive with no password (see application/auth/service.py's
    is_active check on both the password-login and refresh-token paths) so it can never log in."""
    company = company_repo.get_by_id(SYSTEM_COMPANY_ID)
    if company is None:
        now = datetime.now(UTC)
        company = company_repo.add(
            Company(
                id=SYSTEM_COMPANY_ID,
                name=_SYSTEM_COMPANY_NAME,
                slug=_SYSTEM_COMPANY_SLUG,
                plan="free",
                usage_counters={},
                match_threshold=DEFAULT_MATCH_THRESHOLD,
                created_at=now,
                updated_at=now,
            )
        )

    user = user_repo.get_by_id(SYSTEM_USER_ID)
    if user is None:
        now = datetime.now(UTC)
        user = user_repo.add(
            User(
                id=SYSTEM_USER_ID,
                email=_SYSTEM_USER_EMAIL,
                role=UserRole.RECRUITER,
                full_name="LinkedIn Job Ingestion (system)",
                password_hash=None,
                is_active=False,
                email_verified_at=None,
                oauth_google_sub=None,
                created_at=now,
                updated_at=now,
            )
        )

    return company, user
