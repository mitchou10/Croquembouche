# Recherche de documents qui se ressemblent

La page **Recherche** (menu de gauche) prend un document et montre, sous forme de **graphe**, les pages de modèles du
catalogue qui lui ressemblent le plus.

## Ce que l'on voit

- Le document envoyé au centre : une image est un nœud, un **PDF** met **toutes ses pages en ligne**, de gauche à droite.
- Autour, les pages de modèles les plus proches, chacune avec son image. Plus une page ressemble, plus elle est proche,
  grande, et son lien épais. Une page de modèle est **reliée à chaque page du document** qui lui ressemble ; les pages
  de modèles qui se ressemblent entre elles sont reliées en pointillés, ce qui fait apparaître des groupes.
- À droite, la liste des mêmes pages (avec « pages 1, 3 » pour un PDF), la **consommation** de la recherche, et un lien
  vers le modèle quand on en choisit un.

## Réglages

| Réglage | Effet |
| --- | --- |
| Voisins par page | De 1 à 12 (6 par défaut) : combien de pages de modèles chaque page du document demande. |
| Où chercher | Tous les modèles du catalogue (par défaut, le catalogue est à tout le monde), ou seulement ceux que l'on choisit. |

Seuls les modèles qui ont un **document d'exemple** sont dans l'index : les autres ne peuvent pas ressembler à quoi que ce soit.

## Comment ça marche

La recherche est **asynchrone**, comme une utilisation d'analyse :

1. `POST /api/searches` garde le document (ses pages sont dans le store), demande la recherche au worker
   `template_matching` (tâche `template_matching.find_neighbours`, même file que le matching) et répond tout de suite
   `running`.
2. Le worker représente chaque page (CLIP, comme pour le matching), interroge Qdrant (les pages des modèles, chacune
   indexée de quatre côtés et dans chaque version X du modèle) et garde, pour chaque page de modèle, son meilleur score.
   Il rend les voisins, les liens, ce qu'il a consommé et l'**exemple** (le document de la version X) où il l'a trouvé :
   `POST /internal/searches/{id}/result`.
3. La page suit la recherche toutes les 2 s jusqu'à `done` ou `failed`. Un worker qui ne répond pas au bout de
   `MATCHING_TIMEOUT_SECONDS` met la recherche en échec.

Les recherches sont **gardées** (`/recherche`, « Mes recherches ») avec le document envoyé : on les rouvre, on les
supprime (le document est supprimé avec). Elles sont à leur auteur seul, administrateur compris.

## API

| Route | Rôle |
| --- | --- |
| `POST /api/searches` | `file`, `k`, `templateIds` (répété ; absent : tous les modèles). 201, `running`. |
| `GET /api/searches` | Mes recherches, de la plus récente à la plus ancienne. |
| `GET /api/searches/{id}` | L'état, les voisins, les liens et la consommation. |
| `DELETE /api/searches/{id}` | Supprime la recherche et son document. |
| `GET /api/searches/{id}/pages/{n}` | L'image d'une page du document envoyé. |
| `GET /api/templates/{id}/pages/{n}?documentId=` | L'image d'une page d'un modèle, lisible par tout le monde ; `documentId` est l'exemple d'une version X du modèle (le courant par défaut). |

Dans les liens, `page-N` est la page N du document et un voisin est `<modèle>:<page>`.

## Consommation

Comme pour une utilisation, le worker mesure l'électricité, le CO₂ et la durée (CodeCarbon) et le backend estime l'eau
(voir [consommation](consumption.md)). Elle est affichée avec chaque recherche, et **à part** des utilisations dans
« Ma consommation » (section « Mes recherches », champ `searches`).

## À savoir

- La **ressemblance** est le cosinus brut des représentations CLIP, de 0 à 1 : il est souvent compressé (0,6 à 0,95).
- Deux pages de modèles sont reliées à partir de `SEARCH_LINK_MIN` (0,9 par défaut, réglage du worker).
- La vue d'ensemble de l'administrateur ne compte pas encore les recherches.
