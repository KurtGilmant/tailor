"""Profil maître : faits révisionnés, versions, préférences, banque de réponses, imports.

Revision ID: 0003
Revises: 0002
Create Date: 2026-11-06 21:59:10.134070
"""

from collections.abc import Sequence

import sqlalchemy as sa
import sqlmodel.sql.sqltypes
from alembic import op


revision: str = "0003"
down_revision: str | None = "0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "answer_bank",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("question", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column("question_key", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column("answer", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column("created_at", sqlmodel.sql.sqltypes.UTCDateTime(), nullable=False),
        sa.Column("updated_at", sqlmodel.sql.sqltypes.UTCDateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    with op.batch_alter_table("answer_bank", schema=None) as batch_op:
        batch_op.create_index(
            batch_op.f("ix_answer_bank_question_key"), ["question_key"], unique=True
        )

    op.create_table(
        "cv_import",
        sa.Column("id", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column("filename", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column("created_at", sqlmodel.sql.sqltypes.UTCDateTime(), nullable=False),
        sa.Column("status", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column("text", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column("draft", sa.JSON(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "fact",
        sa.Column("id", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column("kind", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column("parent_id", sqlmodel.sql.sqltypes.AutoString(), nullable=True),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.Column("current_rev", sa.Integer(), nullable=False),
        sa.Column("created_at", sqlmodel.sql.sqltypes.UTCDateTime(), nullable=False),
        sa.Column("retired_at", sqlmodel.sql.sqltypes.UTCDateTime(), nullable=True),
        sa.ForeignKeyConstraint(
            ["parent_id"],
            ["fact.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    with op.batch_alter_table("fact", schema=None) as batch_op:
        batch_op.create_index(batch_op.f("ix_fact_kind"), ["kind"], unique=False)
        batch_op.create_index(batch_op.f("ix_fact_parent_id"), ["parent_id"], unique=False)

    op.create_table(
        "preference",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("content", sa.JSON(), nullable=False),
        sa.Column("updated_at", sqlmodel.sql.sqltypes.UTCDateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "profile_version",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("created_at", sqlmodel.sql.sqltypes.UTCDateTime(), nullable=False),
        sa.Column("reason", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "fact_revision",
        sa.Column("fact_id", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column("rev", sa.Integer(), nullable=False),
        sa.Column("content", sa.JSON(), nullable=False),
        sa.Column("source_excerpt", sqlmodel.sql.sqltypes.AutoString(), nullable=True),
        sa.Column("profile_version", sa.Integer(), nullable=False),
        sa.Column("created_at", sqlmodel.sql.sqltypes.UTCDateTime(), nullable=False),
        sa.ForeignKeyConstraint(
            ["fact_id"],
            ["fact.id"],
        ),
        sa.ForeignKeyConstraint(
            ["profile_version"],
            ["profile_version.id"],
        ),
        sa.PrimaryKeyConstraint("fact_id", "rev"),
    )


def downgrade() -> None:
    op.drop_table("fact_revision")
    op.drop_table("profile_version")
    op.drop_table("preference")
    with op.batch_alter_table("fact", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_fact_parent_id"))
        batch_op.drop_index(batch_op.f("ix_fact_kind"))

    op.drop_table("fact")
    op.drop_table("cv_import")
    with op.batch_alter_table("answer_bank", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_answer_bank_question_key"))

    op.drop_table("answer_bank")
