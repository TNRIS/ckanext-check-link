"""Create report table

Revision ID: 564f2016af51
Revises:
Create Date: 2022-06-22 06:24:46.742053

"""
import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB

# revision identifiers, used by Alembic.
revision = "564f2016af51"
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "check_link_report",
        sa.Column("id", sa.UnicodeText, primary_key=True),
        sa.Column("url", sa.UnicodeText),
        sa.Column("state", sa.String(20), nullable=False),
        sa.Column(
            "last_checked",
            sa.DateTime,
            nullable=False,
            server_default=sa.func.current_timestamp(),
        ),
        sa.Column(
            "resource_id",
            sa.UnicodeText,
            sa.ForeignKey("resource.id"),
            nullable=True,
            unique=True,
        ),
        sa.Column(
            "last_status_change",
            sa.DateTime,
            nullable=False,
            server_default=sa.func.current_timestamp(),
        ),
        sa.Column(
            "last_available",
            sa.DateTime,
            nullable=False,
            server_default=sa.func.current_timestamp(),
        ),
        sa.Column("details", JSONB, nullable=False),
        sa.Index("url_idx", "url"),
        sa.UniqueConstraint("url", "resource_id"),
    )


def downgrade():
    op.drop_table("check_link_report")
