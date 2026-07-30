"""add pipeline_mode to answer_runs

Revision ID: 53f3e0db316d
Revises: f9b3096dcc21
Create Date: 2026-07-29 10:48:10.539576

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '53f3e0db316d'
down_revision: Union[str, Sequence[str], None] = 'f9b3096dcc21'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # server_default backfills every existing answer_runs row to 'custom' -
    # accurate, since 'custom' was the only pipeline that existed before
    # this migration. New inserts always specify pipeline_mode explicitly
    # (see answer_service._record_audit), the server_default only exists
    # for this one-time backfill of pre-existing rows.
    op.add_column(
        'answer_runs',
        sa.Column('pipeline_mode', sa.String(), nullable=False, server_default='custom'),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('answer_runs', 'pipeline_mode')