"""add job tables

Revision ID: 0003
Revises: 0002
Create Date: 2026-07-19

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0003"
down_revision: str | None = "0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "jobs",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "company_id",
            sa.Uuid(),
            sa.ForeignKey("companies.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("created_by_user_id", sa.Uuid(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("title", sa.String(200), nullable=False),
        sa.Column("raw_description", sa.String(20000), nullable=False),
        sa.Column("summary", sa.String(4000), nullable=True),
        sa.Column("required_skills", sa.JSON(), nullable=False, server_default="[]"),
        sa.Column("nice_to_have_skills", sa.JSON(), nullable=False, server_default="[]"),
        sa.Column("responsibilities", sa.JSON(), nullable=False, server_default="[]"),
        sa.Column("qualifications", sa.JSON(), nullable=False, server_default="[]"),
        sa.Column("min_experience_years", sa.Float(), nullable=True),
        sa.Column("employment_type", sa.String(50), nullable=True),
        sa.Column("work_mode", sa.String(20), nullable=True),
        sa.Column("location_country", sa.String(100), nullable=True),
        sa.Column("location_region", sa.String(100), nullable=True),
        sa.Column("location_city", sa.String(100), nullable=True),
        sa.Column("salary_min", sa.Integer(), nullable=True),
        sa.Column("salary_max", sa.Integer(), nullable=True),
        sa.Column("lifecycle_status", sa.String(20), nullable=False),
        sa.Column("processing_status", sa.String(20), nullable=False),
        sa.Column("parser_version", sa.String(20), nullable=True),
        sa.Column("content_hash", sa.String(64), nullable=False),
        sa.Column("error_message", sa.String(500), nullable=True),
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("closed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("parsed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_jobs_company_id", "jobs", ["company_id"])
    op.create_index("ix_jobs_created_by_user_id", "jobs", ["created_by_user_id"])

    op.create_table(
        "job_versions",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "job_id", sa.Uuid(), sa.ForeignKey("jobs.id", ondelete="CASCADE"), nullable=False
        ),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("raw_description", sa.String(20000), nullable=False),
        sa.Column("content_hash", sa.String(64), nullable=False),
        sa.Column("parser_version", sa.String(20), nullable=False),
        sa.Column("extracted_snapshot", sa.JSON(), nullable=False, server_default="{}"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_job_versions_job_id", "job_versions", ["job_id"])


def downgrade() -> None:
    op.drop_table("job_versions")
    op.drop_table("jobs")
