# Lecture du texte (OCR)

![Le texte lu dans la zone d'un élément, avec le bouton pour le copier](ocr-text.png)

En plus de chercher les éléments des modèles, chaque utilisation **lit le texte du document** avec
[PaddleOCR](https://github.com/PaddlePaddle/PaddleOCR), sur CPU. Le texte de la zone de chaque élément s'affiche sur sa
carte, avec un bouton pour le copier.

## Deux temps

La lecture se fait **en parallèle** de l'analyse (`worker/ocr` d'un côté, `worker/template_matching` de l'autre) et
**l'analyse n'attend pas** : son résultat s'affiche dès qu'il est prêt, le texte arrive ensuite.

![Le résultat est là, le texte est encore en cours de lecture](ocr-running.png)

Une utilisation a donc deux états indépendants : `status` (l'analyse) et `ocrStatus` (`none`, `running`, `done`,
`failed`). La page continue de s'enquérir de l'utilisation tant que le texte n'est pas lu. Si la lecture échoue, on perd
le texte, pas l'analyse.

## Quels éléments ont un texte

| Type de l'entité | Texte |
| --- | --- |
| texte, date, entier, décimal, montant, pourcentage, oui/non | Les lignes lues dont le centre est dans la zone, de haut en bas. |
| image (signature, tampon, logo) | Aucun : il n'y a rien à lire. |
| tableau | Aucun : il sera lu autrement. |

![Un tableau n'a pas de texte](ocr-no-text.png)

Un élément dont l'entité n'est pas connue (dessiné à la main, ou entité supprimée) est traité comme un texte.

## Retrouver une entité sans zone (GLiNER)

Une entité n'a pas toujours de zone à reporter sur le document : son modèle n'a pas d'image ni de PDF, ou la zone n'a
pas été dessinée. Un **worker à part**, `worker/gliner`, cherche alors sa valeur **dans le texte lu** avec
[GLiNER](https://github.com/urchade/GLiNER) (extraction d'entités « zero-shot »), et rend un élément avec sa zone.

**GLiNER attend l'OCR.** Il lui faut le texte : le backend ne lui envoie sa tâche qu'une fois que l'OCR a répondu. Une
utilisation a un troisième état, `findStatus` : `none` (rien à retrouver), `waiting` (le texte n'est pas encore lu),
`running` (GLiNER cherche), `done`, `failed`. Si le texte ne peut pas être lu, ou n'a aucune ligne, il n'y a rien à
chercher dedans.

- **Quelles entités** : celles d'un modèle **sans document** (aucune n'a de zone), et celles **sans zone** d'un modèle qui
  en a un. Une entité de type image ou tableau n'a pas de texte à retrouver : elle est ignorée.
- **Ce qu'on demande à GLiNER** : la **définition** de l'entité (son nom si elle n'en a pas). Plus la définition est
  précise (« Le numéro de la facture »), mieux c'est.
- **La zone** est celle de ce qui a été trouvé : la partie de la ligne OCR où se trouve le texte (au prorata des
  caractères), ou le rectangle autour de plusieurs lignes. Elle est approximative, la carte le dit.
- **La confiance** est celle de GLiNER, le reste étant « autre ». Pour chaque entité, on garde la réponse la plus sûre sur
  **toutes** les pages : sans zone, on ne sait pas sur quelle page elle est.
- **Le texte trouvé** est gardé chiffré avec l'élément (`detections.text_encrypted`) et rendu tel quel.
- Ces éléments arrivent **après le texte**, donc après l'analyse, et s'ajoutent à ceux qu'elle a trouvés (qui ne les
  remplacent pas). Si GLiNER échoue ou n'est pas déployé, on perd ces éléments, pas le texte ni l'analyse.
- Sa consommation (CodeCarbon) s'ajoute à celle de l'utilisation.
- Le modèle (et son tokenizer) est dans l'image : rien n'est téléchargé au démarrage.

Réglages du worker : `GLINER_MODEL` (`urchade/gliner_multi-v2.1`, multilingue, à la construction de l'image),
`GLINER_THRESHOLD` (`0.4`), `GLINER_CHUNK_WORDS` (`250` : GLiNER lit environ 380 mots à la fois, une page est lue par
morceaux). Backend : `GLINER_ENABLED` (`true`) : `false` ne cherche plus rien par la définition.

## Ce que fait le worker

- Il remet la page d'aplomb (0, 90, 180 ou 270°) et chaque ligne à l'endroit avant de lire : un scan couché ou à l'envers
  est lu normalement. `angle` dit de combien la page était tournée.
- Il rend chaque ligne avec son texte, sa confiance et ses quatre coins **sur la page telle qu'elle a été envoyée**, de 0 à
  1 comme les zones des modèles : les deux se comparent directement.
- Il mesure sa consommation avec CodeCarbon, qui **s'ajoute** à celle de l'analyse : la consommation d'une utilisation est
  celle des deux (ci-dessus, 37 s d'OCR pour une page A4).
- Les modèles sont dans l'image : rien n'est téléchargé au démarrage. Une autre langue est une autre image
  (`--build-arg OCR_LANG=...`).

## Où est gardé le texte

Dans la table `runs` (`ocr_status`, `ocr_encrypted`), **chiffré** comme le nom du fichier : c'est le contenu du document.
Il n'est renvoyé que par `GET /api/analyses/{id}/runs/{run_id}`, à la personne qui a lancé l'utilisation, jamais dans la
liste des utilisations d'une analyse. Le document lui-même n'est supprimé qu'une fois l'analyse **et** la lecture
terminées (sauf si la capture est gardée).

## Réglages

Worker (`worker/ocr`) :

| Variable | Défaut | Effet |
| --- | --- | --- |
| `OCR_LANG` | `fr` | La langue du modèle de reconnaissance (à la construction de l'image). |
| `OCR_MIN_SCORE` | `0.5` | Sous cette confiance, une ligne est écartée. |
| `OCR_CPU_THREADS` | `10` | Les threads de calcul de Paddle. |
| `MEASURE_CONSUMPTION`, `COUNTRY_ISO_CODE`, `CONSUMPTION_TRACKING_MODE` | | Comme pour l'analyse, voir [consumption.md](consumption.md). |

Backend : `OCR_ENABLED` (`true`) : `false` ne lit plus aucun texte.
