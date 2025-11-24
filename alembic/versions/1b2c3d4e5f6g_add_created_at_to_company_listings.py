"""Add created_at to Company listings (placeholder, already applied elsewhere)

Revision ID: 1b2c3d4e5f6g
Revises: c5634b1f489d
Create Date: 2025-11-23 14:35:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "1b2c3d4e5f6g"
down_revision: Union[str, None] = "c5634b1f489d"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # created_at already added in previous migration; placeholder to keep sequence if needed.
    pass


def downgrade() -> None:
    pass
