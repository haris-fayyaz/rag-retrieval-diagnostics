"""add version metadata to documents

Revision ID: 9414b7fcc023
Revises: 53f3e0db316d
Create Date: 2026-08-12 15:48:47.215820

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a1b2c3d4e5f6'
down_revision: Union[str, Sequence[str], None] = '53f3e0db316d'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # All four columns nullable, no backfill. Existing documents have no
    # version metadata and must keep working as unversioned documents -
    # unlike pipeline_mode (migration 53f3e0db316d), there is no single
    # correct backfill value for policy_name/version/effective_date, and
    # backfilling status='active' on old rows would be a guess about
    # documents that were never part of the version-aware flow.
    op.add_column('documents', sa.Column('policy_name', sa.String(), nullable=True))
    op.add_column('documents', sa.Column('version', sa.String(), nullable=True))
    op.add_column('documents', sa.Column('effective_date', sa.String(), nullable=True))
    op.add_column('documents', sa.Column('status', sa.String(), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('documents', 'status')
    op.drop_column('documents', 'effective_date')
    op.drop_column('documents', 'version')
    op.drop_column('documents', 'policy_name')