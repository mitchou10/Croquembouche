# croquembouche-sdk

Client Python (asynchrone) de l'API de Croquembouche : le catalogue, les analyses, la recherche de documents qui se ressemblent.

```sh
uv add "croquembouche-sdk @ git+https://github.com/mitchou10/Croquembouche@v1.24.0#subdirectory=sdk/python"
```

Le guide est dans [`docs/sdk.md`](../../docs/sdk.md) ; un exemple dans [`examples/`](examples).

Le code de `src/croquembouche/_generated` est généré depuis l'OpenAPI du backend (`scripts/generate.sh`) : on ne le modifie pas à la main.
