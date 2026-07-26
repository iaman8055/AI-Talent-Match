"""add job source (native/linkedin) and external listing fields

Revision ID: 0009
Revises: 0008
Create Date: 2026-07-26

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0009"
down_revision: str | None = "0008"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "jobs",
        sa.Column("source", sa.String(20), nullable=False, server_default="native"),
    )
    op.add_column("jobs", sa.Column("external_id", sa.String(100), nullable=True))
    op.add_column("jobs", sa.Column("external_url", sa.String(500), nullable=True))
    op.add_column("jobs", sa.Column("external_company_name", sa.String(200), nullable=True))
    # server_default was only needed to backfill existing rows as "native" — the application
    # always supplies an explicit value going forward, matching every other column on this table.
    op.alter_column("jobs", "source", server_default=None)

    op.create_index("ix_jobs_source", "jobs", ["source"])
    # Defense against double-ingesting the same LinkedIn posting on a re-run — the ingestion
    # service also dedups before insert, this is the backstop.
    op.create_index(
        "uq_jobs_source_external_id",
        "jobs",
        ["source", "external_id"],
        unique=True,
        postgresql_where=sa.text("external_id IS NOT NULL"),
    )


def downgrade() -> None:
    op.drop_index("uq_jobs_source_external_id", table_name="jobs")
    op.drop_index("ix_jobs_source", table_name="jobs")
    op.drop_column("jobs", "external_company_name")
    op.drop_column("jobs", "external_url")
    op.drop_column("jobs", "external_id")
    op.drop_column("jobs", "source")
