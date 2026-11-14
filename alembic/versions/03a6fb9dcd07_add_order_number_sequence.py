"""add order number sequence

Revision ID: 03a6fb9dcd07
Revises: 8e0eafeec0a0
Create Date: 2026-11-12 19:59:17.849784

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '03a6fb9dcd07'
down_revision: Union[str, Sequence[str], None] = '8e0eafeec0a0'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.execute("""
        CREATE SEQUENCE order_number_seq
        START WITH 1
        INCREMENT BY 1
        NO CYCLE;
    """)
    op.execute("""
        GRANT USAGE ON SEQUENCE order_number_seq TO macketi;
    """)

def downgrade() -> None:
    """Downgrade schema."""
    op.execute("""
        DROP SEQUENCE IF EXISTS order_number_seq;
    """)
