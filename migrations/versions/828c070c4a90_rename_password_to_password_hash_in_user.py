"""Rename password to password_hash in User

Revision ID: 828c070c4a90
Revises: f77745b7520c
Create Date: [Auto-generated timestamp]

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '828c070c4a90'
down_revision = 'f77745b7520c'
branch_labels = None
depends_on = None

def upgrade():
    # Drop the temporary table if it exists
    op.execute("DROP TABLE IF EXISTS _alembic_tmp_user")

    # Create a temporary table with the new schema
    op.create_table(
        '_alembic_tmp_user',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('username', sa.String(length=150), nullable=False),
        sa.Column('email', sa.String(length=150), nullable=False),
        sa.Column('password_hash', sa.String(length=150), nullable=False),
        sa.Column('role', sa.String(length=50), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('email'),
        sa.UniqueConstraint('username')
    )

    # Copy data from user to _alembic_tmp_user, mapping password to password_hash
    op.execute("""
        INSERT INTO _alembic_tmp_user (id, username, email, password_hash, role, created_at, updated_at)
        SELECT id, username, email, password, role, created_at, updated_at
        FROM user
    """)

    # Drop the old user table
    op.drop_table('user')

    # Rename the temporary table to user
    op.rename_table('_alembic_tmp_user', 'user')

def downgrade():
    # Drop the temporary table if it exists
    op.execute("DROP TABLE IF EXISTS _alembic_tmp_user")

    # Create a temporary table with the old schema
    op.create_table(
        '_alembic_tmp_user',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('username', sa.String(length=150), nullable=False),
        sa.Column('email', sa.String(length=150), nullable=False),
        sa.Column('password', sa.String(length=150), nullable=False),
        sa.Column('role', sa.String(length=50), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('email'),
        sa.UniqueConstraint('username')
    )

    # Copy data back, mapping password_hash to password
    op.execute("""
        INSERT INTO _alembic_tmp_user (id, username, email, password, role, created_at, updated_at)
        SELECT id, username, email, password_hash, role, created_at, updated_at
        FROM user
    """)

    # Drop the current user table
    op.drop_table('user')

    # Rename the temporary table back to user
    op.rename_table('_alembic_tmp_user', 'user')