# Le stockage des documents, et oublier ce qu'une personne a envoyé

Les documents (les images, les PDF et les captures de leurs pages) sont dans le stockage d'objets (S3, RustFS en local), bucket `AWS_BUCKET`
(`croquembouche-documents`). Ils sont rangés **par type, puis par propriétaire** :

| Préfixe | Ce que c'est |
| ------- | ------------ |
| `analyses/<sub>/<uuid>/…` | Ce qu'une personne envoie **à analyser** : un essai d'analyse, une recherche de documents similaires. |
| `models/<sub>/<uuid>/…` | Les **documents d'exemple des modèles** : ils sont partagés avec d'autres personnes. |
| `documents/<uuid>/…` | Ce qui a été envoyé **avant** que la clé ait un propriétaire. Rien n'est migré : ils se lisent et se suppriment comme avant. |

`<sub>` est l'identifiant Keycloak de la personne (celui d'un compte de service aussi), jamais son e-mail ni son nom ; il est encodé pour une clé
(`a/b` devient `a%2Fb`). Le préfixe se termine par une barre : `bob` n'est pas `bobby`. Sous le préfixe d'un document : `original.<extension>`
et, pour un PDF, `pages/<n>.png`. Les workers reçoivent ces clés sans les interpréter.

## Oublier ce qu'une personne a envoyé

- `DELETE /api/users/me/data` : la personne efface **ses propres envois**.
- `DELETE /api/users/{id}/data` : **administrateurs**, par exemple à la suppression d'un compte (`403` pour un autre compte).

Cela supprime, en base **et** dans le stockage : ses **essais** d'analyses (avec ce qu'ils ont trouvé), ses **recherches**, et les **documents** qu'ils
utilisent (le document analysé, la capture gardée) ; puis tout ce qui reste sous `analyses/<sub>/`. Les documents d'avant le changement de clé sont pris
aussi, par leurs essais et leurs recherches. La réponse dit ce qui a été supprimé : `{runs, searches, documents}`.

**Ce que cela ne supprime pas** : les modèles, leurs documents d'exemple, les analyses (d'autres s'en servent), ni ce qu'une autre personne a envoyé.

Pour un compte de service (une application), « ses envois » sont tout ce que l'application a envoyé : les documents ont pour propriétaire le compte
qui a fait l'appel. Pour qu'ils soient à la personne, l'application doit appeler avec le **jeton de la personne échangé** (`TokenExchange`).

SDK : `client.users.purge_my_data()` et `client.users.purge(id)` (TypeScript : `purgeMyData()` et `purge(id)`).

## Filet de sécurité : faire expirer `analyses/`

Un document d'analyse est supprimé quand le résultat a été lu (sauf si la capture est gardée), mais rien ne fait expirer ce qui serait resté. Une
**règle de cycle de vie du bucket** sur `analyses/` le fait, sans rien dans l'application. Par exemple, au bout de 7 jours :

```sh
aws s3api put-bucket-lifecycle-configuration --bucket croquembouche-documents --endpoint-url "$AWS_ENDPOINT_URL" \
  --lifecycle-configuration '{"Rules":[{"ID":"expire-analyses","Status":"Enabled","Filter":{"Prefix":"analyses/"},"Expiration":{"Days":7}}]}'
```

(avec RustFS ou MinIO : `mc ilm rule add --expire-days 7 --prefix analyses/ <alias>/croquembouche-documents`). Les lignes en base d'un document expiré restent : la
purge d'une personne les supprime, et la page du document répond alors `404`. **Ne mettez pas de règle sur `models/`** : ce sont les exemples des modèles.
