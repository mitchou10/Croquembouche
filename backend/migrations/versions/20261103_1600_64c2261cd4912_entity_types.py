"""seed the entity types

Revision ID: 64c2261cd491b
Revises: 64c2261cd491
Create Date: 2026-11-03 16:00:00

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "64c2261cd491b"
down_revision: str | Sequence[str] | None = "64c2261cd491"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

# The same list as the frontend's, with the definitions it shows to people.
ENTITY_TYPES = [
    (
        "text",
        "Texte",
        "Une suite de caractères libre : un nom, une adresse, une référence… La valeur est gardée telle qu’elle est écrite.",
    ),
    (
        "date",
        "Date",
        "Une date, quelle que soit la façon dont elle est écrite (12/03/2026, 12 mars 2026). Elle est lue et rendue au format AAAA-MM-JJ.",
    ),
    (
        "integer",
        "Entier",
        "Un nombre sans partie décimale : une quantité, un numéro. Les séparateurs de milliers (espaces, points) sont ignorés.",
    ),
    (
        "decimal",
        "Nombre décimal",
        "Un nombre avec une partie décimale. La virgule et le point sont acceptés comme séparateur.",
    ),
    (
        "amount",
        "Montant",
        "Une somme d’argent, avec ou sans devise (1 250,00 €). Le montant et la devise sont extraits séparément.",
    ),
    (
        "percentage",
        "Pourcentage",
        "Un taux exprimé en pourcentage (20 %). La valeur est rendue sous forme de nombre, 20 pour 20 %.",
    ),
    (
        "yes_no",
        "Oui / non",
        "Une réponse à deux issues : une case cochée ou non, « oui » ou « non ». Rendue sous forme de booléen.",
    ),
]

entity_types = sa.table(
    "entity_types", sa.column("value", sa.String), sa.column("label", sa.String), sa.column("definition", sa.Text)
)


def upgrade() -> None:
    op.bulk_insert(entity_types, [{"value": v, "label": label, "definition": d} for v, label, d in ENTITY_TYPES])


def downgrade() -> None:
    op.execute(entity_types.delete().where(entity_types.c.value.in_([v for v, _, _ in ENTITY_TYPES])))
