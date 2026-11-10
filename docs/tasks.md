# Les tâches des workers

Chaque worker (`template_matching`, `ocr`, `gliner`) **déclare au backend** les tâches qu'il sait faire, avec leur version, et dit
régulièrement qu'il est vivant. Le backend les liste : `GET /api/tasks`.

## Ce qu'une tâche déclare

| Champ | Contenu |
| ----- | ------- |
| `name` | Le nom de la tâche Celery : `template_matching.classify_pages`, `ocr.read_document`… |
| `version` | La version du worker qui la porte (celle de son paquet, que change une release). |
| `description` | Ce qu'elle fait. |
| `author` | Qui l'a faite (`WORKER_AUTHOR`, « Croquembouche » par défaut). |
| `inputSchema` | Ce qu'elle prend, en JSON Schema : un objet dont les propriétés sont les arguments de la tâche, par nom. |
| `parameters` | Ce qu'on peut régler, en JSON Schema : les réglages du worker qui changent ce qu'elle fait (seuils, modèle, langue), avec leur valeur actuelle en `default`. |
| `outputSchema` | Ce qu'elle donne, en JSON Schema : sa valeur de retour, ou ce qu'elle rend au backend (les tâches de calcul rendent leur résultat par `/internal/...`). |

Les schémas sont dans `worker/<nom>/app/catalog.py`. Un test de chaque worker vérifie que ce catalogue et les tâches Celery sont les mêmes :
on ne peut pas ajouter une tâche sans la décrire.

## Les tables

- **`worker_heartbeats`** : une ligne par instance de worker (`instance_id`, `service`, `hostname`, `started_at`, `last_seen_at`). L'`instance_id`
  est refait à chaque démarrage : deux processus, ou un redémarrage, sont deux instances.
- **`worker_tasks`** : une ligne par tâche et par instance (`name`, `version`, `description`, `input_schema`, `parameters`, `output_schema`, `author`,
  `instance_id`, `created_at`). Unique sur (`name`, `version`, `instance_id`). Supprimer une instance supprime ses tâches.

## Le protocole (réservé au worker, clé `X-Internal-Key`)

| Appel | Quand |
| ----- | ----- |
| `PUT /internal/workers/{instance_id}` | Au démarrage : `{service, hostname, tasks: […]}`. Remplace ce que l'instance avait déclaré. |
| `POST /internal/workers/{instance_id}/heartbeat` | Toutes les `WORKER_HEARTBEAT_SECONDS` (30 s). Répond `404` si le backend ne connaît pas l'instance (il a été redémarré sans sa base) : l'instance **se déclare de nouveau**. |
| `DELETE /internal/workers/{instance_id}` | À l'arrêt propre : ses tâches ne sont plus offertes. |

Le worker ne s'arrête jamais à cause de cela : un backend injoignable est réessayé au battement suivant. `REGISTER_TASKS=0` désactive tout.

## Lire les tâches

`GET /api/tasks` (toute personne connectée, un compte de service aussi) : une entrée par **nom et version**, avec les instances qui l'ont.

- Une instance est **en ligne** si elle a donné signe de vie depuis `WORKER_HEARTBEAT_TTL_SECONDS` (90 s, réglage du backend). `online` compte ces
  instances ; `?online=true` ne garde que les tâches qu'une instance vivante a.
- Un instance silencieuse reste listée, hors ligne, puis **est oubliée** (avec ses tâches) après `WORKER_PURGE_DAYS` jours (7), au prochain enregistrement.
- Quand les instances d'une même version ne sont pas d'accord, la description et les schémas sont ceux de la plus récemment déclarée.
- `GET /api/tasks/{name}` : toutes les versions d'une tâche (`404` si aucun worker ne la déclare).

Les SDK ont `client.tasks.list()` et `client.tasks.get(nom)` (voir [sdk.md](sdk.md)).
