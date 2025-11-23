"""Add created_at to Company listings

Revision ID: 1b2c3d4e5f6g
Revises: 0a1c2b3d4e5f
Create Date: 2025-11-23 14:35:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '1b2c3d4e5f6g'
down_revision: Union[str, None] = '0a1c2b3d4e5f'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # created_at already added in previous migration; placeholder to keep sequence if needed.
    pass


def downgrade() -> None:
    pass
