"""Lit les champs d'un document avec une analyse déjà créée : `python extract_fields.py scan.pdf <id de l'analyse>`.

L'application s'authentifie avec son propre compte de service (voir docs/sdk.md).
"""

import asyncio
import os
import sys

from croquembouche import Croquembouche, token_url


async def main(document: str, analysis_id: str) -> None:
    async with Croquembouche(
        os.environ["CROQUEMBOUCHE_URL"],
        token_url=token_url(os.environ["KEYCLOAK_URL"], os.environ.get("KEYCLOAK_REALM", "croquembouche")),
        client_id=os.environ["CLIENT_ID"],
        client_secret=os.environ["CLIENT_SECRET"],
    ) as client:
        run = await client.analyses.run(analysis_id, document)
        result = await run.wait(timeout=120)
        for element in result.elements:
            name = element.entity.name if element.entity else "(entité inconnue)"
            print(f"{name}: {element.text!r} ({element.confidence:.0%}, page {element.zone.page})")


if __name__ == "__main__":
    asyncio.run(main(sys.argv[1], sys.argv[2]))
