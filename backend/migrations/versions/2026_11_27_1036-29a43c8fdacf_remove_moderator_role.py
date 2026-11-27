"""remove moderator role

Revision ID: 29a43c8fdacf
Revises: ceb97deb50de
Create Date: 2026-11-27 10:36:00

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '29a43c8fdacf'
down_revision: Union[str, Sequence[str], None] = 'ceb97deb50de'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

OLD_ROLE = sa.Enum('ADMIN', 'USER', 'MODERATOR', name='userrole')
NEW_ROLE = sa.Enum('ADMIN', 'USER', name='userrole')


def upgrade() -> None:
    """Chỉ còn 2 role: ADMIN và USER. Moderator hiện có bị hạ xuống USER."""
    op.execute("UPDATE users SET role = 'USER' WHERE role = 'MODERATOR'")
    op.alter_column(
        'users', 'role',
        existing_type=OLD_ROLE,
        type_=NEW_ROLE,
        existing_nullable=False,
    )


def downgrade() -> None:
    op.alter_column(
        'users', 'role',
        existing_type=NEW_ROLE,
        type_=OLD_ROLE,
        existing_nullable=False,
    )
