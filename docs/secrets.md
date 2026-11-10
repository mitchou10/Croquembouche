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
| `worker` | `croquembouche-worker` | `INTERNAL_API_KEY` | backend, workers (template matching, OCR et GLiNER) |
| `redis` | `croquembouche-redis` | `REDIS_PASSWORD` | Redis, et `REDIS_URL` pour backend et worker |
| `db-superuser` | `croquembouche-db-superuser` | `username`, `password` | CloudNativePG |
| `db-appuser` | `croquembouche-db-appuser` | `username`, `password` | CloudNativePG, et `DATABASE_URL` pour backend et migration |

`croquembouche-db-infos` (qui porte `DATABASE_URL`) n'a pas de chemin à lui : le Vault Secrets Operator la calcule à partir de `db-appuser`. Même chose pour `REDIS_URL`, calculée à partir de `redis`. **Ne les créez pas** dans Vault.

## Le détail, secret par secret

### `s3` : le stockage des documents (externe)

Le S3 est **externe** au cluster (`rustfs.enabled: false` dans les valeurs communes) : Vault ne garde que les identifiants du compte, l'adresse est dans les valeurs de l'environnement.

| Clé | Valeur |
| --- | ------ |
| `AWS_ACCESS_KEY_ID` | la clé d'accès du compte S3 |
| `AWS_SECRET_ACCESS_KEY` | sa clé secrète |

Le compte doit pouvoir lire, écrire et supprimer dans le bucket `croquembouche-documents` et le créer s'il n'existe pas (le backend le crée au premier usage). Le backend **et le worker** lisent dans ce bucket : les deux pods doivent pouvoir joindre le S3 depuis le cluster (sortie réseau autorisée, certificat reconnu).

Dans le fichier de valeurs de l'environnement (`backend.envCm` **et** `worker_template_matching.envCm`, la même adresse aux deux endroits) :

```yaml
AWS_ENDPOINT_URL: "https://s3.exemple.org"
AWS_BUCKET: "croquembouche-documents"   # facultatif, c'est la valeur par défaut
AWS_REGION: "us-east-1"                  # facultatif, à adapter au fournisseur
```

### `keycloak` : la connexion (externe)

Keycloak est **externe** au cluster : Vault ne garde que le secret du client, les adresses sont dans les valeurs de l'environnement.

| Clé | Valeur |
| --- | ------ |
| `KEYCLOAK_CLIENT_SECRET` | le secret du client Keycloak du backend |

Dans le fichier de valeurs de l'environnement (`backend.envCm`) :

```yaml
KEYCLOAK_URL: "https://keycloak.exemple.org"   # par où le backend joint Keycloak, depuis le cluster
KEYCLOAK_PUBLIC_URL: "https://keycloak.exemple.org"   # par où le navigateur le joint, seulement si différente
BACKEND_PUBLIC_URL: "https://croquembouche.exemple.org"
FRONTEND_URL: "https://croquembouche.exemple.org"
```

Le backend appelle Keycloak depuis le cluster (jeton, clés de signature, déconnexion) : la sortie réseau doit être autorisée et le certificat reconnu. `KEYCLOAK_PUBLIC_URL` n'est utile que si l'adresse vue par le navigateur n'est pas celle vue par le backend.

À faire d'abord dans Keycloak, dans le realm de l'environnement (`KEYCLOAK_REALM`, `mirai` dans les valeurs communes) : un client **confidentiel** dont l'identifiant est `KEYCLOAK_CLIENT_ID` (`croquembouche`), avec le flux « Standard flow » et PKCE, et pour adresse de redirection :

```
https://<hôte>/api/auth/callback
```

(`docker/keycloak/realm-croquembouche.json` montre la forme du client.) Le secret se lit dans l'onglet « Credentials » du client. Les administrateurs sont ceux qui ont le rôle `admin`.

#### Appeler Croquembouche sans personne derrière : un compte de service

Une application (mille-feuille, par exemple) peut appeler l'API avec son propre jeton, sans passer par un utilisateur. Ce compte lit **tous les modèles du catalogue, quelle que soit leur visibilité**, et ne peut **rien modifier** : création, modification, restauration, suppression, partage, étoiles, suggestions et envoi de documents d'exemple répondent `403`. Il peut en revanche faire des analyses, qui sont les siennes comme celles d'une personne.

Dans Keycloak :

1. Créer un client **confidentiel** pour l'application appelante, avec « Service accounts roles » activé (flux `client_credentials`).
2. Dans le client `KEYCLOAK_CLIENT_ID` (`croquembouche`), onglet « Roles », créer le rôle **`catalogue-reader`** (déjà présent dans `docker/keycloak/realm-croquembouche.json`).
3. Dans le client de l'application, onglet « Service account roles » : lui attribuer ce rôle du client `croquembouche`.
4. Le jeton doit porter le rôle et l'audience : le rôle du client `croquembouche` est ajouté au jeton d'accès par le scope `roles` (par défaut), et avec lui l'audience `croquembouche`.

Un compte de service est reconnu à **deux choses ensemble** : le claim `clientId`, que Keycloak ajoute aux seuls jetons de comptes de service, et le rôle `catalogue-reader`. Le rôle sur une personne ne donne rien ; un compte de service sans le rôle n'a pas plus qu'avant. Ce n'est pas un administrateur.

#### Les jetons échangés (RFC 8693)

Pour créer ou modifier un modèle **au nom d'une personne**, l'application échange le jeton de la personne contre un jeton pour Croquembouche. Le backend y voit la personne d'origine (`sub`, e-mail, groupes) : ses droits sont les siens, ni plus ni moins.

Dans Keycloak :

1. Activer les « Standard token exchange » sur le client de l'application (Keycloak 26.2 ou plus ; avant, la fonction préversion `token-exchange` et une permission d'échange sur le client `croquembouche`).
2. L'échange demande `audience=croquembouche` : le jeton obtenu a l'audience `croquembouche`.
3. Le jeton répond à l'identité de la personne seulement si les **mappers `groups` et du rôle `croquembouche`** sont présents pour le client de l'application (`docker/keycloak/realm-croquembouche.json` en montre la forme sur le client `croquembouche` ; le plus simple est d'en faire un scope client commun, attribué aux deux clients).

Pour n'accepter que les jetons destinés à Croquembouche, renseigner dans `backend.envCm` :

```yaml
KEYCLOAK_AUDIENCE: "croquembouche"   # le client du backend (KEYCLOAK_CLIENT_ID)
```

Un jeton est alors accepté s'il a cette audience ou s'il a été émis pour ce client ; les autres reçoivent `401`. Vide (par défaut), tout jeton valide du realm est accepté, comme avant.

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

Ces valeurs sont dans le fichier de valeurs de l'environnement, pas dans Vault : l'adresse de l'application (`BACKEND_PUBLIC_URL`, `FRONTEND_URL`, l'hôte de l'ingress), **les adresses externes de Keycloak (`KEYCLOAK_URL`, `KEYCLOAK_PUBLIC_URL`) et du S3 (`AWS_ENDPOINT_URL`)**, le realm et le client Keycloak, et la liste blanche d'adresses.

## Vérifier

Une fois le Vault Secrets Operator passé, les sept Secrets Kubernetes existent (`croquembouche-s3`, `-keycloak`, `-app`, `-worker`, `-redis`, `-db-superuser`, `-db-appuser`) ainsi que `croquembouche-db-infos` :

```sh
kubectl get secret -n <namespace> | grep croquembouche
kubectl get secret croquembouche-db-infos -n <namespace> -o jsonpath='{.data}' | jq 'keys'   # ["DATABASE_URL"]
kubectl get secret croquembouche-redis -n <namespace> -o jsonpath='{.data}' | jq 'keys'      # ["REDIS_PASSWORD","REDIS_URL"]
```

Un pod qui reste en `CreateContainerConfigError` attend presque toujours un Secret absent : `kubectl describe pod` dit lequel.
