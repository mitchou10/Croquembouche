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
