"""Adjust transactions: drop currency/gateway, keep metadata_json

Revision ID: 9c6b5f2a7d8e
Revises: e8b0b5c0fcb2
Create Date: 2025-02-19 00:30:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "9c6b5f2a7d8e"
down_revision: Union[str, None] = "e8b0b5c0fcb2"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("transactions") as batch_op:
        batch_op.drop_column("currency")
        batch_op.drop_column("gateway")


def downgrade() -> None:
    with op.batch_alter_table("transactions") as batch_op:
        batch_op.add_column(sa.Column("gateway", sa.String(), nullable=False, server_default="ipaymu"))
        batch_op.add_column(sa.Column("currency", sa.String(), nullable=False, server_default="IDR"))
