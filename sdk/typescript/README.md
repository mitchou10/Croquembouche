# croquembouche-sdk (TypeScript)

Client TypeScript de l'API de Croquembouche : le catalogue, les analyses, la recherche de documents qui se ressemblent.

```sh
pnpm add "croquembouche-sdk@github:mitchou10/Croquembouche#v1.24.0&path:/sdk/typescript"
```

Le guide est dans [`docs/sdk.md`](../../docs/sdk.md) ; un exemple dans [`examples/`](examples).

Les types de `src/generated/schema.d.ts` sont générés depuis l'OpenAPI du backend (`scripts/generate.sh`) : on ne les modifie pas à la main.
