"""init postgis schema

Revision ID: 0001_init_postgis
Revises: None
Create Date: 2026-04-17
"""
from alembic import op
import sqlalchemy as sa
from geoalchemy2 import Geography
from sqlalchemy.dialects import postgresql


revision = "0001_init_postgis"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS postgis")

    op.create_table(
        "reports",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("channel", sa.String(length=20), nullable=False),
        sa.Column("damage_type", sa.String(length=50), nullable=False),
        sa.Column("severity", sa.String(length=20), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="new"),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("ai_summary", sa.Text(), nullable=True),
        sa.Column("ai_confidence", sa.Float(), nullable=True),
        sa.Column("location", Geography(geometry_type="POINT", srid=4326), nullable=False),
        sa.Column("address", sa.Text(), nullable=True),
        sa.Column("reporter_id", sa.String(length=100), nullable=True),
        sa.Column("reporter_name", sa.String(length=200), nullable=True),
        sa.Column("photo_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("idx_reports_location", "reports", ["location"], unique=False, postgresql_using="gist")
    op.create_index("idx_reports_severity", "reports", ["severity", "created_at"], unique=False)
    op.create_index("idx_reports_status", "reports", ["status", "created_at"], unique=False)

    op.create_table(
        "media",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("report_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("reports.id", ondelete="CASCADE")),
        sa.Column("url", sa.Text(), nullable=False),
        sa.Column("type", sa.String(length=20), nullable=True),
        sa.Column("ai_labels", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )


def downgrade() -> None:
    op.drop_table("media")
    op.drop_index("idx_reports_status", table_name="reports")
    op.drop_index("idx_reports_severity", table_name="reports")
    op.drop_index("idx_reports_location", table_name="reports")
    op.drop_table("reports")