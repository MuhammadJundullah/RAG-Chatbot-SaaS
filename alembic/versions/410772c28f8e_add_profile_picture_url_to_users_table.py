"""Add profile_picture_url to users table

Revision ID: 410772c28f8e
Revises: e86c506b3e6c
Create Date: 2025-11-04 20:16:32.288054

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '410772c28f8e'
down_revision: Union[str, None] = 'e86c506b3e6c'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Check if the column exists before adding it
    from sqlalchemy import inspect
    inspector = inspect(op.get_bind())
    columns = inspector.get_columns('Users')
    column_names = [c['name'] for c in columns]
    
    if 'profile_picture_url' not in column_names:
        op.add_column('Users', sa.Column('profile_picture_url', sa.String(), nullable=True))


def downgrade() -> None:
    op.drop_column('Users', 'profile_picture_url')
