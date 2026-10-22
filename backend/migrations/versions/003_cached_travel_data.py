"""Create destination and accommodation cache tables."""

from alembic import op
import sqlalchemy as sa


revision = "003_cached_travel_data"
down_revision = "002_saas_features"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "cached_places",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("destination", sa.String(), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("category", sa.String(), nullable=False),
        sa.Column("lat", sa.Float(), nullable=True),
        sa.Column("lon", sa.Float(), nullable=True),
        sa.Column("address", sa.Text(), nullable=True),
        sa.Column("rating", sa.Float(), nullable=True),
        sa.Column("price_level", sa.String(), nullable=True),
        sa.Column("admission_price", sa.String(), nullable=True),
        sa.Column("photo_url", sa.Text(), nullable=True),
        sa.Column("photo_attribution", sa.Text(), nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("website", sa.Text(), nullable=True),
        sa.Column("source", sa.String(), nullable=False),
        sa.Column("created_at", sa.String(), nullable=False, server_default=sa.func.current_timestamp()),
    )
    op.create_table(
        "cached_accommodations",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("destination", sa.String(), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("tier", sa.String(), nullable=False),
        sa.Column("stars", sa.Integer(), nullable=True),
        sa.Column("rating", sa.Float(), nullable=True),
        sa.Column("price_per_night", sa.Float(), nullable=True),
        sa.Column("currency", sa.String(), nullable=False, server_default="USD"),
        sa.Column("neighborhood", sa.String(), nullable=True),
        sa.Column("amenities", sa.Text(), nullable=True, server_default="[]"),
        sa.Column("photo_url", sa.Text(), nullable=True),
        sa.Column("booking_url", sa.Text(), nullable=True),
        sa.Column("pricing_type", sa.String(), nullable=False, server_default="estimated_reference_rate"),
        sa.Column("source", sa.String(), nullable=False),
        sa.Column("created_at", sa.String(), nullable=False, server_default=sa.func.current_timestamp()),
        sa.Column("price_usd", sa.Float(), nullable=True),
        sa.Column("price_inr", sa.Float(), nullable=True),
    )


def downgrade() -> None:
    op.drop_table("cached_accommodations")
    op.drop_table("cached_places")
