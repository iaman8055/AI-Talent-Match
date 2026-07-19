"""add matching (company match_threshold + match_scores)

Revision ID: 0004
Revises: 0003
Create Date: 2026-07-19

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0004"
down_revision: str | None = "0003"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "companies",
        sa.Column("match_threshold", sa.Integer(), nullable=False, server_default="70"),
    )

    op.create_table(
        "match_scores",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "candidate_id",
            sa.Uuid(),
            sa.ForeignKey("candidates.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "job_id", sa.Uuid(), sa.ForeignKey("jobs.id", ondelete="CASCADE"), nullable=False
        ),
        sa.Column("overall_score", sa.Float(), nullable=False),
        sa.Column("semantic_score", sa.Float(), nullable=False),
        sa.Column("skill_overlap_score", sa.Float(), nullable=False),
        sa.Column("experience_fit_score", sa.Float(), nullable=False),
        sa.Column("salary_fit_score", sa.Float(), nullable=False),
        sa.Column("location_fit_score", sa.Float(), nullable=False),
        sa.Column("rerank_score", sa.Float(), nullable=True),
        sa.Column("matcher_version", sa.String(20), nullable=False),
        sa.Column("candidate_content_hash", sa.String(64), nullable=False),
        sa.Column("job_content_hash", sa.String(64), nullable=False),
        sa.Column("computed_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_match_scores_candidate_id", "match_scores", ["candidate_id"])
    op.create_index("ix_match_scores_job_id", "match_scores", ["job_id"])
    op.create_index("ix_match_scores_job_score", "match_scores", ["job_id", "overall_score"])
    op.create_index(
        "ix_match_scores_candidate_score", "match_scores", ["candidate_id", "overall_score"]
    )


def downgrade() -> None:
    op.drop_table("match_scores")
    op.drop_column("companies", "match_threshold")
