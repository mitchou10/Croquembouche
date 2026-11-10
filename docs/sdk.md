# Le SDK Python

`croquembouche-sdk` est un client **asynchrone** de l'API : il prend en charge le jeton (et son renouvellement), l'envoi des
documents, l'attente d'un résultat et les erreurs, pour que lire le catalogue ou analyser un document tienne en quelques lignes.
Il est dans [`sdk/python`](../sdk/python).

## Installer

Il n'est pas publié sur un registre : il s'installe depuis le dépôt, à la version voulue. Le SDK a le numéro de version de
l'application (il est publié avec elle, sous le même tag).

```sh
uv add "croquembouche-sdk @ git+https://github.com/mitchou10/Croquembouche@v1.24.0#subdirectory=sdk/python"
```

Python 3.11 ou plus.

## Se connecter

```python
from croquembouche import Croquembouche, token_url

async with Croquembouche(
    "https://croquembouche.exemple.org",
    token_url=token_url("https://keycloak.exemple.org", "mon-realm"),
    client_id="mille-feuille",
    client_secret="…",
) as client:
    ...
```

Le client se connecte comme l'application, **sans personne derrière** (`client_credentials`) : le compte de service doit avoir le
rôle `catalogue-reader` pour lire tous les modèles (voir [secrets.md](secrets.md)). Le jeton est demandé au premier appel, gardé,
puis redemandé 30 secondes avant la fin de sa validité ; un `401` le fait redemander une fois.

Les autres façons de se présenter, de la plus simple à la plus complète :

| Vous avez | Écrire |
| --------- | ------ |
| rien à présenter (un backend sans authentification, en développement) | `Croquembouche(url)` |
| un jeton | `Croquembouche(url, token="…")` ou `auth=BearerToken(lambda: mon_jeton())` (la fonction donne le jeton courant, à chaque requête) |
| un compte de service | `token_url=`, `client_id=`, `client_secret=` (ci-dessus), ou `auth=ClientCredentials(…)` |
| le jeton d'une personne, à échanger | `auth=TokenExchange(token_url, client_id, client_secret, jeton_de_la_personne)` |

Avec `TokenExchange` (RFC 8693), tout ce que fait le client est fait **au nom de la personne** : ses droits, ses groupes, et elle est
propriétaire de ce qu'elle crée. `jeton_de_la_personne` peut être une fonction, appelée à chaque renouvellement. L'audience demandée est
`croquembouche-backend` (`audience=` pour une autre).

## Le catalogue

```python
modeles = await client.templates.list("facture")       # recherche ; mine=True pour les siens
formulaire = await client.templates.get(modele_id)
for entite in formulaire.entities:
    print(entite.name, entite.type_, [(z.page, len(z.points)) for z in entite.zones])

await client.templates.versions(modele_id)             # 1.2.0, 1.1.0…
await client.templates.version(modele_id, "1.1.0")     # le modèle tel qu'il était
image = await client.templates.page(modele_id, 1)      # PNG de la page 1, en octets
```

Les noms des champs sont ceux de l'API, en `snake_case` (`owner_name`, `template_ids`). Seul `type` devient `type_`. Les modèles
(`TemplateOut`, `EntityOut`, `Zone`…) sont dans `croquembouche.models`.

Avec le jeton d'une personne, créer, modifier et partager :

```python
from croquembouche import models

document = await client.templates.upload_document("exemple.pdf")
modele = await client.templates.create(
    models.TemplateCreate(
        name="Facture",
        document_id=document.id,
        entities=[models.EntityFields(name="Numéro", type_="text", zones=[haut, bas])],  # plusieurs zones
    )
)
await client.templates.share(modele.id, "shared", [models.Share(kind=models.ShareKind.GROUP, value="compta")])
```

Un compte de service en lecture seule reçoit `ForbiddenError` pour tout cela.

## Analyser un document

```python
analyse = await client.analyses.create(
    "Factures", [modele.id], template_versions={modele.id: "1.2.0"}  # épinglée : rejouable
)
run = await client.analyses.run(analyse.id, "facture.pdf")           # un chemin, des octets ou un fichier
resultat = await run.wait(timeout=120)                               # attend la fin, texte lu compris
for element in resultat.elements:
    print(element.entity.name, element.text, element.confidence, element.zone.page, element.zone_index)
```

- `run()` démarre l'essai et rend la main ; `wait()` l'interroge (`interval=` secondes, 1 par défaut) jusqu'à sa fin.
- Un **élément** est un champ trouvé : l'`entity` (nommée d'après les modèles de l'analyse et leurs sous-modèles), le `text` lu dans
  la zone (`None` pour une image ou un tableau), la `confidence` (0 à 1), la `zone` et, pour une entité à plusieurs zones, le
  `zone_index` (à partir de 0). `resultat.pages` dit à quel modèle ressemble chaque page.
- `wait(text=False)` n'attend pas la lecture du texte (les éléments n'ont alors pas encore leur `text`).
- `WaitTimeoutError` après le délai : l'essai continue côté serveur. On peut attendre encore (`await run.wait()`) ou
  l'**annuler** (`await run.cancel()`). `RunFailedError` si l'essai a échoué.
- Un essai appartient à qui l'a lancé : le résultat n'est lisible que par le même jeton (le compte de service pour ses essais).

## Chercher des documents qui se ressemblent

```python
recherche = await client.searches.start("scan.pdf", k=5)   # parmi tous les modèles lisibles, ou template_ids=[…]
trouve = await recherche.wait()
for voisin in trouve.neighbours:
    print(voisin.template_id, voisin.template_page, voisin.similarity)
```

## Les erreurs

Chaque réponse d'erreur de l'API est une exception qui porte le `status_code` et le `detail` donné par l'API :

| Exception | Statut |
| --------- | ------ |
| `AuthenticationError` | 401, ou Keycloak refuse le jeton |
| `ForbiddenError` | 403 |
| `NotFoundError` | 404 (un modèle qu'on ne peut pas utiliser n'existe pas) |
| `InvalidRequestError` | 400, 422 |
| `ConflictError` | 409 |
| `ServerError` | 5xx |

Toutes héritent de `APIError`, puis de `CroquembouchError`. `WaitTimeoutError` (aussi un `TimeoutError`) et `RunFailedError` ne
viennent pas d'une réponse.

## Mettre à jour le client

Le code qui parle à l'API (`src/croquembouche/_generated`) est **généré** depuis l'OpenAPI du backend ; `openapi.json` en est la
source. Après un changement de l'API :

```sh
sdk/python/scripts/generate.sh
```

La CI refuse une branche où le client commité n'est pas celui que donne l'API. Ce qui est écrit à la main (`auth.py`, `client.py`,
`analyses.py`, `templates.py`, `searches.py`, `errors.py`) ne change pas à la régénération.

## Les tests

- `cd sdk/python && uv run pytest` : contre une fausse API.
- `cd backend && uv run --with ../sdk/python pytest tests/test_sdk.py` : de bout en bout contre l'application et sa base (le worker
  est joué par le test). La CI le fait dans le job du backend.
- La CI installe aussi le SDK depuis Git, comme le ferait `uv add`, et y rejoue les tests : c'est ce que reçoit un utilisateur.
