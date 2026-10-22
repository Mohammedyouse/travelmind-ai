"""Create destination and accommodation cache tables."""

from alembic import op
import sqlalchemy as sa


revision = "003_cached_travel_data"
down_revision = "002_saas_features"
branch_labels = None
depends_on = None


def upgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    existing_tables = set(inspector.get_table_names())

    if "cached_places" not in existing_tables:
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
    else:
        place_columns = {column["name"] for column in inspector.get_columns("cached_places")}
        required_place_columns = {
            "id", "destination", "name", "category", "lat", "lon", "address", "rating",
            "price_level", "admission_price", "photo_url", "photo_attribution",
            "description", "website", "source", "created_at",
        }
        missing_place_columns = required_place_columns - place_columns
        if missing_place_columns:
            raise RuntimeError(
                "Existing cached_places table is missing required columns: "
                + ", ".join(sorted(missing_place_columns))
            )

    if "cached_accommodations" not in existing_tables:
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
    else:
        accommodation_columns = {
            column["name"] for column in inspector.get_columns("cached_accommodations")
        }
        required_accommodation_columns = {
            "id", "destination", "name", "tier", "stars", "rating", "price_per_night",
            "currency", "neighborhood", "amenities", "photo_url", "booking_url",
            "pricing_type", "source", "created_at",
        }
        missing_accommodation_columns = required_accommodation_columns - accommodation_columns
        if missing_accommodation_columns:
            raise RuntimeError(
                "Existing cached_accommodations table is missing required columns: "
                + ", ".join(sorted(missing_accommodation_columns))
            )
        for column_name in ("price_usd", "price_inr"):
            if column_name not in accommodation_columns:
                op.add_column("cached_accommodations", sa.Column(column_name, sa.Float(), nullable=True))


def downgrade() -> None:
    raise RuntimeError(
        "Downgrade is disabled because cache tables may have existed before this revision."
    )
