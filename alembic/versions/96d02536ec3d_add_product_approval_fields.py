"""add product approval fields

Revision ID: 96d02536ec3d
Revises: 133378971359
Create Date: 2026-09-30 12:58:43.712243

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = '96d02536ec3d'
down_revision: Union[str, Sequence[str], None] = '133378971359'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Crear el tipo ENUM a mano, porque env.py le dice a Alembic
    # que no gestione los tipos automáticamente.
    op.execute("CREATE TYPE product_approval_status AS ENUM ('PENDING', 'APPROVED', 'REJECTED')")

    # Ahora las columnas pueden usar el tipo.
    op.add_column('products', sa.Column('approval_status', postgresql.ENUM('PENDING', 'APPROVED', 'REJECTED', name='product_approval_status', create_type=False), nullable=False, server_default='PENDING'))
    op.add_column('products', sa.Column('rejection_reason', sa.String(length=500), nullable=True))
    op.add_column('products', sa.Column('reviewed_by_id', sa.Integer(), nullable=True))
    op.add_column('products', sa.Column('reviewed_at', sa.DateTime(timezone=True), nullable=True))
    op.add_column('products', sa.Column('proposed_by_id', sa.Integer(), nullable=True))
    op.create_foreign_key('products_reviewed_by_id_fkey', 'products', 'users', ['reviewed_by_id'], ['id'], ondelete='SET NULL')
    op.create_foreign_key('products_proposed_by_id_fkey', 'products', 'users', ['proposed_by_id'], ['id'], ondelete='SET NULL')
    op.create_index('ix_products_approval_status', 'products', ['approval_status'], unique=False)
    op.create_index('ix_products_proposed_by_id', 'products', ['proposed_by_id'], unique=False)
    # ### end Alembic commands ###


def downgrade() -> None:
    op.drop_index('ix_products_proposed_by_id', table_name='products')
    op.drop_index('ix_products_approval_status', table_name='products')
    op.drop_constraint('products_proposed_by_id_fkey', 'products', type_='foreignkey')
    op.drop_constraint('products_reviewed_by_id_fkey', 'products', type_='foreignkey')
    op.drop_column('products', 'proposed_by_id')
    op.drop_column('products', 'reviewed_at')
    op.drop_column('products', 'reviewed_by_id')
    op.drop_column('products', 'rejection_reason')
    op.drop_column('products', 'approval_status')

    # Borrar el tipo ENUM al final.
    op.execute("DROP TYPE IF EXISTS product_approval_status")
    # ### end Alembic commands ###
