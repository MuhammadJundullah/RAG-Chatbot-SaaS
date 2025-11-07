"""empty message

Revision ID: 298a099d748c
Revises: 0edab536e083, 410772c28f8e
Create Date: 2025-11-07 11:30:16.562439

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '298a099d748c'
down_revision: Union[str, None] = ('0edab536e083', '410772c28f8e')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
