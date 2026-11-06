# Résultat d'une analyse : la carte d'un élément

![Carte d'un élément trouvé : sans texte lu, puis avec](detection-card.png)

Chaque élément trouvé dans un document est montré à deux endroits.

- **Sur le document** : la zone est entourée et porte le nom de l'**entité** (« Élément n » quand elle n'est pas connue),
  avec ce qui en a été décidé (`✓` validé, `✗` invalidé, `✎` annoté) ou, tant qu'il n'est pas relu, la confiance.
  Le modèle n'y figure pas.
- **Dans la carte** (`DetectionCard`) : le nom de l'entité en titre, le **modèle** reconnu en badge, la confiance, une
  vignette de la zone recadrée (`ZoneCrop`) et les classes possibles de la plus à la moins probable.

L'entité vient de `entityId` : le backend ne la garde que si elle existe dans le modèle, sinon elle est vide.
La confiance affichée est celle de la classification, pas celle de la lecture de la valeur.

Le bouton **Copier le texte** attend la lecture du texte de la zone (OCR), pas encore faite : il est désactivé tant que
`text` est vide (carte du haut), puis copie le texte affiché (carte du bas).

## Une zone sur un document penché

![Une zone penchée, avant et après redressement](zone-straightened.png)

Le worker reporte les coins de chaque zone du modèle sur le document (homographie), **dans le même ordre** : haut gauche,
haut droite, bas droite, bas gauche. Quand une zone de quatre coins n'est pas droite sur la page (document scanné de
travers ou à l'envers), la vignette la **redresse** avec une transformation de perspective CSS (`matrix3d`, voir
`composables/perspective.ts`), sans rien changer au backend. Une zone droite est simplement découpée par sa boîte, et
une zone qui n'a pas quatre coins (polygone libre) aussi : elle n'a pas de « haut » défini.

La capture est faite avec des données fictives.
