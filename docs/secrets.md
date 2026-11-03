# Les secrets à créer

Sur le cluster (`helm/values/common-values.yaml`), aucun secret n'est dans les valeurs : chacun est lu dans **Vault** par le Vault Secrets Operator, qui le dépose dans un Secret Kubernetes que les pods lisent par `envFrom`.

Chemin d'un secret dans Vault (KV v2) :

```
<mount>/<env>/croquembouche/<nom>
```

- `<mount>` : le projet, `global.project` (`exploration` par défaut) ;
- `<env>` : l'environnement, `global.vault.env` (`dev` par défaut, à surcharger dans le fichier de valeurs de chaque environnement) ;
- `<nom>` : un des sept secrets ci-dessous.

Les clés ci-dessous sont **exactement** les noms des variables d'environnement lues par l'application : une clé de plus est sans effet, une clé manquante est une variable qui prend sa valeur de développement (ou fait échouer le démarrage).

## Récapitulatif

| Chemin Vault (`<mount>/<env>/croquembouche/…`) | Secret Kubernetes | Clés à y mettre | Lu par |
| ---------------------------------------------- | ----------------- | --------------- | ------ |
| `s3` | `croquembouche-s3` | `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY` | backend, worker |
| `keycloak` | `croquembouche-keycloak` | `KEYCLOAK_CLIENT_SECRET` | backend |
| `app` | `croquembouche-app` | `DATA_ENCRYPTION_KEYS`, `BLIND_INDEX_PEPPER` | backend |
| `worker` | `croquembouche-worker` | `INTERNAL_API_KEY` | backend, worker |
| `redis` | `croquembouche-redis` | `REDIS_PASSWORD` | Redis, et `REDIS_URL` pour backend et worker |
| `db-superuser` | `croquembouche-db-superuser` | `username`, `password` | CloudNativePG |
| `db-appuser` | `croquembouche-db-appuser` | `username`, `password` | CloudNativePG, et `DATABASE_URL` pour backend et migration |

`croquembouche-db-infos` (qui porte `DATABASE_URL`) n'a pas de chemin à lui : le Vault Secrets Operator la calcule à partir de `db-appuser`. Même chose pour `REDIS_URL`, calculée à partir de `redis`. **Ne les créez pas** dans Vault.

## Le détail, secret par secret

### `s3` : le stockage des documents

| Clé | Valeur |
| --- | ------ |
| `AWS_ACCESS_KEY_ID` | la clé d'accès du compte S3 |
| `AWS_SECRET_ACCESS_KEY` | sa clé secrète |

Le compte doit pouvoir lire, écrire et supprimer dans le bucket `croquembouche-documents` et le créer s'il n'existe pas (le backend le crée au premier usage). L'adresse du S3 n'est pas un secret : `AWS_ENDPOINT_URL` dans les valeurs de l'environnement.

### `keycloak` : la connexion

| Clé | Valeur |
| --- | ------ |
| `KEYCLOAK_CLIENT_SECRET` | le secret du client Keycloak du backend |

À faire d'abord dans Keycloak, dans le realm de l'environnement (`KEYCLOAK_REALM`, `mirai` dans les valeurs communes) : un client **confidentiel** dont l'identifiant est `KEYCLOAK_CLIENT_ID` (`croquembouche`), avec le flux « Standard flow » et PKCE, et pour adresse de redirection :

```
https://<hôte>/api/auth/callback
```

(`docker/keycloak/realm-croquembouche.json` montre la forme du client.) Le secret se lit dans l'onglet « Credentials » du client. Les administrateurs sont ceux qui ont le rôle `admin`.

### `app` : le chiffrement des données personnelles

| Clé | Valeur | À générer avec |
| --- | ------ | -------------- |
| `DATA_ENCRYPTION_KEYS` | une ou plusieurs clés Fernet, séparées par des virgules | `python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"` (depuis `backend/`, `uv run python -c …`) |
| `BLIND_INDEX_PEPPER` | une chaîne aléatoire | `openssl rand -hex 32` |

> **À garder précieusement.** Sans ces deux valeurs, ce qui est chiffré en base (noms de fichiers, adresses des partages…) est illisible.
>
> - `DATA_ENCRYPTION_KEYS` : la **première** clé chiffre, **toutes** déchiffrent. Pour une rotation, on met la nouvelle en tête et on garde les anciennes derrière : `nouvelle,ancienne`.
> - `BLIND_INDEX_PEPPER` ne change **jamais** : il sert à retrouver les partages par empreinte, et le changer les fait tous disparaître.
> - Si elles manquent, le backend prend des valeurs **de développement publiques**, sans rien dire : ne déployez pas sans elles.

### `worker` : la clé du worker

| Clé | Valeur | À générer avec |
| --- | ------ | -------------- |
| `INTERNAL_API_KEY` | une chaîne aléatoire | `openssl rand -hex 32` |

Le worker la présente au backend (en-tête `X-Internal-Key`) pour lui rendre le résultat d'un essai. Backend et worker la lisent dans le même secret, elle est donc identique des deux côtés. Sans elle, le backend refuse tous les résultats (503) et les essais finissent en échec au bout du délai.

### `redis` : les sessions et la file du worker

| Clé | Valeur | À générer avec |
| --- | ------ | -------------- |
| `REDIS_PASSWORD` | le mot de passe de Redis | `openssl rand -hex 24` |

`REDIS_URL` (`redis://:<mot de passe>@croquembouche-redis:6379/0`) est construite par le Vault Secrets Operator à partir de cette clé. Utilisez de l'hexadécimal : un mot de passe avec des caractères réservés d'une URL (`@`, `:`, `/`, `#`, `%`) casserait l'adresse.

### `db-superuser` et `db-appuser` : PostgreSQL (CloudNativePG)

| Secret | `username` | `password` |
| ------ | ---------- | ---------- |
| `db-superuser` | `postgres` | `openssl rand -hex 24` |
| `db-appuser` | `croquembouche` | `openssl rand -hex 24` |

`username` de `db-appuser` doit être le propriétaire de la base défini dans `cnpg.cluster.initdb` (`croquembouche`), qui est aussi le nom de la base. CloudNativePG exige ces deux secrets sous la forme `kubernetes.io/basic-auth` : c'est déjà dit dans `extraObjects`, il n'y a rien à faire de plus que de mettre les deux clés.

`DATABASE_URL` (`postgresql+asyncpg://<username>:<password>@croquembouche-pg-cluster-rw:5432/croquembouche`) est construite à partir de `db-appuser`. Même précaution que pour Redis : un mot de passe hexadécimal.

## Créer les secrets

Avec la CLI Vault, pour l'environnement `dev` du projet `exploration` :

```sh
vault kv put exploration/dev/croquembouche/s3 \
  AWS_ACCESS_KEY_ID=... AWS_SECRET_ACCESS_KEY=...
vault kv put exploration/dev/croquembouche/keycloak \
  KEYCLOAK_CLIENT_SECRET=...
vault kv put exploration/dev/croquembouche/app \
  DATA_ENCRYPTION_KEYS="$(uv run --project backend python -c 'from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())')" \
  BLIND_INDEX_PEPPER="$(openssl rand -hex 32)"
vault kv put exploration/dev/croquembouche/worker \
  INTERNAL_API_KEY="$(openssl rand -hex 32)"
vault kv put exploration/dev/croquembouche/redis \
  REDIS_PASSWORD="$(openssl rand -hex 24)"
vault kv put exploration/dev/croquembouche/db-superuser \
  username=postgres password="$(openssl rand -hex 24)"
vault kv put exploration/dev/croquembouche/db-appuser \
  username=croquembouche password="$(openssl rand -hex 24)"
```

Un environnement de plus, c'est le même jeu de commandes avec un autre `<env>` (et ses propres valeurs : ne réutilisez pas les secrets d'un environnement dans un autre).

## Ce qui n'est pas un secret

Ces valeurs sont dans le fichier de valeurs de l'environnement, pas dans Vault : l'adresse de l'application (`BACKEND_PUBLIC_URL`, `FRONTEND_URL`, l'hôte de l'ingress), celle de Keycloak (`KEYCLOAK_URL`, et `KEYCLOAK_PUBLIC_URL` s'il est derrière un proxy), celle du S3 (`AWS_ENDPOINT_URL`), le realm et le client Keycloak, et la liste blanche d'adresses.

## Vérifier

Une fois le Vault Secrets Operator passé, les sept Secrets Kubernetes existent (`croquembouche-s3`, `-keycloak`, `-app`, `-worker`, `-redis`, `-db-superuser`, `-db-appuser`) ainsi que `croquembouche-db-infos` :

```sh
kubectl get secret -n <namespace> | grep croquembouche
kubectl get secret croquembouche-db-infos -n <namespace> -o jsonpath='{.data}' | jq 'keys'   # ["DATABASE_URL"]
kubectl get secret croquembouche-redis -n <namespace> -o jsonpath='{.data}' | jq 'keys'      # ["REDIS_PASSWORD","REDIS_URL"]
```

Un pod qui reste en `CreateContainerConfigError` attend presque toujours un Secret absent : `kubectl describe pod` dit lequel.
