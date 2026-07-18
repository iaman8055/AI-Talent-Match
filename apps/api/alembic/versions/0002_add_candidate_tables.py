"""add candidate tables

Revision ID: 0002
Revises: 0001
Create Date: 2026-07-18

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0002"
down_revision: str | None = "0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "candidates",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "user_id", sa.Uuid(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False
        ),
        sa.Column("full_name", sa.String(200), nullable=True),
        sa.Column("headline", sa.String(300), nullable=True),
        sa.Column("summary", sa.String(4000), nullable=True),
        sa.Column("skills", sa.JSON(), nullable=False, server_default="[]"),
        sa.Column("total_experience_years", sa.Float(), nullable=True),
        sa.Column("location_country", sa.String(100), nullable=True),
        sa.Column("location_region", sa.String(100), nullable=True),
        sa.Column("location_city", sa.String(100), nullable=True),
        sa.Column("desired_salary_min", sa.Integer(), nullable=True),
        sa.Column("desired_salary_max", sa.Integer(), nullable=True),
        sa.Column("work_mode_preference", sa.String(20), nullable=True),
        sa.Column("work_experience", sa.JSON(), nullable=False, server_default="[]"),
        sa.Column("education", sa.JSON(), nullable=False, server_default="[]"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_candidates_user_id", "candidates", ["user_id"], unique=True)

    op.create_table(
        "resumes",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "candidate_id",
            sa.Uuid(),
            sa.ForeignKey("candidates.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("s3_key", sa.String(500), nullable=False),
        sa.Column("original_filename", sa.String(255), nullable=False),
        sa.Column("file_type", sa.String(10), nullable=False),
        sa.Column("content_type", sa.String(200), nullable=False),
        sa.Column("file_size", sa.Integer(), nullable=False),
        sa.Column("content_hash", sa.String(64), nullable=False),
        sa.Column("status", sa.String(20), nullable=False),
        sa.Column("parser_version", sa.String(20), nullable=False),
        sa.Column("error_message", sa.String(500), nullable=True),
        sa.Column("uploaded_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("parsed_at", sa.DateTime(timezone=True), nullable=True),
        sa.UniqueConstraint(
            "candidate_id", "content_hash", name="uq_resumes_candidate_content_hash"
        ),
    )
    op.create_index("ix_resumes_candidate_id", "resumes", ["candidate_id"])
    op.create_index("ix_resumes_content_hash", "resumes", ["content_hash"])


def downgrade() -> None:
    op.drop_table("resumes")
    op.drop_table("candidates")
