"""dátum vydania setu

Revision ID: c3e2vydanie0108
Revises: b2d1diely0101
Create Date: 2026-11-25 12:00:00.000000

Dátum vydania prichádza v odpovediach, ktoré už ťaháme: Brickset
(``launchDate``, inak prvý deň na LEGO.com) do ``brickset_facts.launch_date``
a BrickEconomy (``released_date``) do ``brickeconomy_facts.released_date``.
``brickset_facts.dates_at`` hovorí, že odpoveď už dátumy niesla; staršie
riadky ho nemajú a detail sa ich opýta raz znova. Písané ručne.
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "c3e2vydanie0108"
down_revision: str | Sequence[str] | None = "b2d1diely0101"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("brickset_facts", sa.Column("launch_date", sa.Date(), nullable=True))
    op.add_column(
        "brickset_facts", sa.Column("dates_at", sa.DateTime(timezone=True), nullable=True)
    )
    op.add_column("brickeconomy_facts", sa.Column("released_date", sa.Date(), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table("brickeconomy_facts") as batch:
        batch.drop_column("released_date")
    with op.batch_alter_table("brickset_facts") as batch:
        batch.drop_column("dates_at")
        batch.drop_column("launch_date")
