# Changelog

## [1.7.0](https://github.com/mitchou10/Croquembouche/compare/v1.6.2...v1.7.0) (2026-11-04)


### Features

* **templates:** move, resize and delete a rectangle already drawn ([7b5f70a](https://github.com/mitchou10/Croquembouche/commit/7b5f70ac77cbfe52cc983714163c693731b11fc7)), closes [#38](https://github.com/mitchou10/Croquembouche/issues/38)

## [1.6.2](https://github.com/mitchou10/Croquembouche/compare/v1.6.1...v1.6.2) (2026-11-03)


### Bug Fixes

* **helm:** set a CPU limit on the backend and the worker, as the namespace quota asks ([aa7ff1a](https://github.com/mitchou10/Croquembouche/commit/aa7ff1a35fd9e93ada70e58632e67a1cc021e5ef))

## [1.6.1](https://github.com/mitchou10/Croquembouche/compare/v1.6.0...v1.6.1) (2026-11-03)


### Bug Fixes

* **helm:** run the migration after an upgrade, not before, so Argo CD applies the release first ([9397d6c](https://github.com/mitchou10/Croquembouche/commit/9397d6cad3dbf9199ea1b5853089af72d939daf5))

## [1.6.0](https://github.com/mitchou10/Croquembouche/compare/v1.5.0...v1.6.0) (2026-11-03)


### Features

* **backend:** give the quality of the analysis for a person and for everyone, over every model ([7320b46](https://github.com/mitchou10/Croquembouche/commit/7320b46b346a8655a4434142dcb93d5136e3849c))
* **backend:** measure the analysis from the decisions of the users, per model and per entity ([987978d](https://github.com/mitchou10/Croquembouche/commit/987978d17efa18fb12720de782f095093db8efba))
* **frontend:** add an evaluation page with one's own decisions and, for an admin, everyone's ([f6bdc2d](https://github.com/mitchou10/Croquembouche/commit/f6bdc2d9bf9601a1659f7a727c57b58fe1e8a309))
* **frontend:** show the quality of the analysis on a model, and the entity of an added element ([51dde5e](https://github.com/mitchou10/Croquembouche/commit/51dde5ed44e482197939e1323f8bddaaa5dbf9e7))

## [1.5.0](https://github.com/mitchou10/Croquembouche/compare/v1.4.0...v1.5.0) (2026-11-03)


### Features

* **frontend:** fill the address of the backend into the nginx configuration at start ([54c40f3](https://github.com/mitchou10/Croquembouche/commit/54c40f3ef56b6492fa15eb6c9fac10984d4c5fce))
* **helm:** add a chart built on the this-is-tobi template for the components and their services ([78c0c24](https://github.com/mitchou10/Croquembouche/commit/78c0c2408330fd4f0d974c8d0064ea77a02f2b8f))
* **helm:** add the common values of the platform: Harbor, Vault secrets and a CloudNativePG cluster ([05463eb](https://github.com/mitchou10/Croquembouche/commit/05463eb46fd875220a3ff77652bfa26e009068b7))
* **worker:** put the embedding model in the image at build time, so a pod downloads nothing ([8359f1c](https://github.com/mitchou10/Croquembouche/commit/8359f1c4164f8c3cf845a5f3c8f1bcd68cec9a97))

## [1.4.0](https://github.com/mitchou10/Croquembouche/compare/v1.3.0...v1.4.0) (2026-11-03)


### Features

* **backend:** add the per-page classification and the pages of a model to the data model ([8e3db09](https://github.com/mitchou10/Croquembouche/commit/8e3db09906c87517ea43a8445b4f67b766f5a18c))
* **backend:** ask the worker to index a model when it is saved, and to forget it when it is deleted ([d8205b4](https://github.com/mitchou10/Croquembouche/commit/d8205b438b664a3d9caa45fd88bcac9cc73bee3f))
* **backend:** ask the worker to match a document and keep what it answers (running, done, failed) ([8c7677d](https://github.com/mitchou10/Croquembouche/commit/8c7677de96d5b38cf028f9f334a1cf89186c7606))
* **backend:** classify and review page by page, and name the pages of a model ([152d78e](https://github.com/mitchou10/Croquembouche/commit/152d78e518b3121109758d36cd7a71186bfe3379))
* **backend:** classify each page of a document, as a page of a model, in the matcher contract ([e03d2d0](https://github.com/mitchou10/Croquembouche/commit/e03d2d0059031a315b919cc3b23ae12e8d766e63))
* **docker:** add Qdrant and give the worker what it needs to index the catalogue ([d7bd421](https://github.com/mitchou10/Croquembouche/commit/d7bd421b2889977adb78e4cc82a482871a125549))
* **docker:** give the backend and the worker the key the results are handed back with ([2594149](https://github.com/mitchou10/Croquembouche/commit/2594149137795c188b7bcfbd29e6daa74eea3c8b))
* **frontend:** classify and review a document page by page, and name the pages of a model ([0d182c6](https://github.com/mitchou10/Croquembouche/commit/0d182c62240742a2343f457bb31af1f95adb79ec))
* **frontend:** show a use as running while the worker computes it, and follow it until it ends ([f61eb24](https://github.com/mitchou10/Croquembouche/commit/f61eb242fb85c75f28204f8f3af35547afa61c90))
* **worker:** carry the zones of a model page onto a document page with keypoints and a homography ([1f76730](https://github.com/mitchou10/Croquembouche/commit/1f76730a49ebee8e0534750f7e9073a1d51d3514))
* **worker:** classify each page of a document from its nearest neighbours in Qdrant ([ec97e7e](https://github.com/mitchou10/Croquembouche/commit/ec97e7eb421e586420d928bd6238ec4277227339))
* **worker:** index pages and entity crops turned by 0, 90, 180 and 270 degrees, with details ([2518f86](https://github.com/mitchou10/Croquembouche/commit/2518f8654c17aa9690faf39613a6f6408c4d5d2d))
* **worker:** index the pages of a model and its entity zones in Qdrant with image embeddings ([43012c1](https://github.com/mitchou10/Croquembouche/commit/43012c1665273f836e23fc0fc34348d5791c3728))
* **worker:** match a document the backend asks for and hand the result back to it ([9d51eb5](https://github.com/mitchou10/Croquembouche/commit/9d51eb58954f24f3c0982463fde89891e3065e4e))


### Bug Fixes

* **frontend:** put the name and the description of a page side by side above the document ([ade0628](https://github.com/mitchou10/Croquembouche/commit/ade0628fcac0497f18e565cc168f0d8ed3368e99))

## [1.3.0](https://github.com/mitchou10/Croquembouche/compare/v1.2.0...v1.3.0) (2026-11-03)


### Features

* **backend:** suggest the entities and zones of a PDF from its form fields, boxes and blanks ([31da4ab](https://github.com/mitchou10/Croquembouche/commit/31da4abdfa3f9c7ad69850168c438627567d0053))
* **frontend:** offer the entities a PDF suggests, with their zones, in the model form ([68bf611](https://github.com/mitchou10/Croquembouche/commit/68bf611e4debdaf0bda4983c82c33df477879f2a))

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
