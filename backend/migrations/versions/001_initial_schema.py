"""Create the initial TravelMind persistence schema."""

from alembic import op
import sqlalchemy as sa

revision = "001_initial_schema"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("email", sa.String(), nullable=False, unique=True),
        sa.Column("full_name", sa.String(), nullable=False),
        sa.Column("password_hash", sa.String(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("role", sa.String(), nullable=False, server_default="traveler"),
        sa.Column("created_at", sa.String(), nullable=False),
    )
    op.create_table(
        "trips",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("user_id", sa.String(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("origin", sa.String(), nullable=True),
        sa.Column("destination", sa.String(), nullable=True),
        sa.Column("departure_date", sa.String(), nullable=True),
        sa.Column("return_date", sa.String(), nullable=True),
        sa.Column("duration_days", sa.Integer(), nullable=True),
        sa.Column("travelers", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("budget", sa.Float(), nullable=True),
        sa.Column("currency", sa.String(), nullable=False, server_default="USD"),
        sa.Column("status", sa.String(), nullable=False, server_default="draft"),
        sa.Column("summary", sa.Text(), nullable=True),
        sa.Column("preferences", sa.Text(), nullable=False, server_default="{}"),
        sa.Column("plan_results", sa.Text(), nullable=False, server_default="{}"),
        sa.Column("created_at", sa.String(), nullable=False),
    )
    op.create_table(
        "itinerary_items",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("trip_id", sa.String(), sa.ForeignKey("trips.id"), nullable=False),
        sa.Column("day", sa.Integer(), nullable=False),
        sa.Column("title", sa.String(), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("cost", sa.Float(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.String(), nullable=False),
    )
    op.create_table(
        "budget_snapshots",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("trip_id", sa.String(), sa.ForeignKey("trips.id"), nullable=False),
        sa.Column("currency", sa.String(), nullable=False, server_default="USD"),
        sa.Column("total", sa.Float(), nullable=False, server_default="0"),
        sa.Column("contingency", sa.Float(), nullable=False, server_default="0"),
    )
    op.create_table(
        "conversations",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("trip_id", sa.String(), sa.ForeignKey("trips.id"), nullable=True),
        sa.Column("user_id", sa.String(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("role", sa.String(), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("created_at", sa.String(), nullable=False),
    )
    op.create_table(
        "preferences",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("user_id", sa.String(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("key", sa.String(), nullable=False),
        sa.Column("value", sa.String(), nullable=False),
        sa.Column("created_at", sa.String(), nullable=False),
    )


def downgrade() -> None:
    for table_name in ("preferences", "conversations", "budget_snapshots", "itinerary_items", "trips", "users"):
        op.drop_table(table_name)