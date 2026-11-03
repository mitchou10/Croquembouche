# Changelog

## [1.2.0](https://github.com/mitchou10/Croquembouche/compare/v1.1.0...v1.2.0) (2026-11-03)


### Features

* backend with Keycloak, Postgres and RustFS, connected to the frontend ([#8](https://github.com/mitchou10/Croquembouche/issues/8)) ([ae73030](https://github.com/mitchou10/Croquembouche/commit/ae73030fd61f53fc25ce7a5c869704c8f9f67758))
* **backend:** add the BFF login, callback, logout and me endpoints ([e17ceee](https://github.com/mitchou10/Croquembouche/commit/e17ceee518057b8aae3fa79647e8a02f0ec7e4dc))
* **backend:** add the Keycloak settings, the session store and the security factory ([c409f9f](https://github.com/mitchou10/Croquembouche/commit/c409f9fe9589557a2b03f9a08a61f6153b035d75))
* **docker:** add Keycloak with the Croquembouche realm and wire the backend to it ([92241d6](https://github.com/mitchou10/Croquembouche/commit/92241d6b04e3c6915de84edb10fef062aa11ea14))
* **frontend:** sign in through the backend and Keycloak instead of the mocked session ([e20692e](https://github.com/mitchou10/Croquembouche/commit/e20692ee178f196a60e330aa91af59bc66e541b7))
* serve the backend under /api of the frontend's origin ([f6fa1ae](https://github.com/mitchou10/Croquembouche/commit/f6fa1aef2110732502f5ad77e7b6de16c1c5dddd))


### Dependencies

* **backend:** add the Keycloak, Redis and settings dependencies and the pytest setup ([bc4c7a5](https://github.com/mitchou10/Croquembouche/commit/bc4c7a5c0f34533a0690c1b0bf0fcc75ccc0e303))

## [1.1.0](https://github.com/mitchou10/Croquembouche/compare/v1.0.0...v1.1.0) (2026-11-03)


### Features

* **frontend:** add analyses, their creation and their sharing ([3fbb2e1](https://github.com/mitchou10/Croquembouche/commit/3fbb2e14d2cb410491ec7f86b6334c563ec1f655))
* **frontend:** add the administrator's overview ([4f2504e](https://github.com/mitchou10/Croquembouche/commit/4f2504e37da121d6902fc7a8dbd2f9bd9dfe2f6b))
* **frontend:** add the app shell with DSFR, routing and a mocked sign-in ([37c52b0](https://github.com/mitchou10/Croquembouche/commit/37c52b016d3cd72add2c6db2822f4b4a08c34024))
* **frontend:** add the catalogue of models ([b3758ec](https://github.com/mitchou10/Croquembouche/commit/b3758ec4a9cf96b29dba37e7dee82ec036e20dad))
* **frontend:** add the dashboard of an analysis ([d25608a](https://github.com/mitchou10/Croquembouche/commit/d25608a371a23230773c9480a46d4125ccc19b80))
* **frontend:** add the mocked data and the backend calls to replace ([0272092](https://github.com/mitchou10/Croquembouche/commit/027209236ff3f52dfeb6b92840201884fb007b10))
* **frontend:** add the shared list components ([ef66620](https://github.com/mitchou10/Croquembouche/commit/ef66620256f2f67ea908338d6d785f3749a85927))


### Dependencies

* add docker compose with hot reload and fix image healthchecks ([dda4864](https://github.com/mitchou10/Croquembouche/commit/dda48645c49d970e1345288ac1b333f704c91097))

## 1.0.0 (2026-11-03)


### Features

* scaffold frontend, backend and template matching worker ([81f3a90](https://github.com/mitchou10/Croquembouche/commit/81f3a9076d7b382f0b13a164f08503b5b32a51d0))
