# Résultat d'une analyse : la carte d'un élément

![Carte d'un élément trouvé](detection-card.png)

Chaque élément trouvé dans un document est montré à deux endroits.

- **Sur le document** : la zone est entourée et porte le nom de l'**entité** (« Élément n » quand elle n'est pas connue),
  avec ce qui en a été décidé (`✓` validé, `✗` invalidé, `✎` annoté) ou, tant qu'il n'est pas relu, la confiance.
  Le modèle n'y figure pas.
- **Dans la carte** (`DetectionCard`) : le nom de l'entité en titre, le **modèle** reconnu en badge, la confiance, une
  vignette de la zone recadrée (`ZoneCrop`) et les classes possibles de la plus à la moins probable.

L'entité vient de `entityId` : le backend ne la garde que si elle existe dans le modèle, sinon elle est vide.
La confiance affichée est celle de la classification, pas celle de la lecture de la valeur.

La capture est faite avec des données fictives.
