"""create transactions table for payments and top-ups

Revision ID: e8b0b5c0fcb2
Revises: 1b2c3d4e5f6g
Create Date: 2025-02-19 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "e8b0b5c0fcb2"
down_revision: Union[str, None] = "1b2c3d4e5f6g"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "transactions",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("company_id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=True),
        sa.Column("type", sa.String(), nullable=False),
        sa.Column("plan_id", sa.Integer(), nullable=True),
        sa.Column("package_type", sa.String(), nullable=True),
        sa.Column("questions_delta", sa.Integer(), nullable=True),
        sa.Column("amount", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("currency", sa.String(), nullable=False, server_default="IDR"),
        sa.Column("gateway", sa.String(), nullable=False, server_default="ipaymu"),
        sa.Column("payment_reference", sa.String(), nullable=True),
        sa.Column("status", sa.String(), nullable=False, server_default="pending_payment"),
        sa.Column("metadata_json", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False),
        sa.Column("paid_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["company_id"], ["Company.id"]),
        sa.ForeignKeyConstraint(["user_id"], ["Users.id"]),
        sa.ForeignKeyConstraint(["plan_id"], ["plans.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_transactions_id"), "transactions", ["id"], unique=False)
    op.create_index(op.f("ix_transactions_company_id"), "transactions", ["company_id"], unique=False)
    op.create_index(op.f("ix_transactions_user_id"), "transactions", ["user_id"], unique=False)
    op.create_index(op.f("ix_transactions_payment_reference"), "transactions", ["payment_reference"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_transactions_payment_reference"), table_name="transactions")
    op.drop_index(op.f("ix_transactions_user_id"), table_name="transactions")
    op.drop_index(op.f("ix_transactions_company_id"), table_name="transactions")
    op.drop_index(op.f("ix_transactions_id"), table_name="transactions")
    op.drop_table("transactions")
