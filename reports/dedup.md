# Normalización y deduplicación

Generado por `meli-etl normalize` + `meli-etl dedup` (determinista). Unidad de dedup: **sección** (header + cuerpo hasta el siguiente header). Tokens = palabras `\w+`.

## 1. Embudo

| Paso | Archivos | Secciones | Tokens |
|---|---|---|---|
| 0. Crudo (Markdown: contenido + navegación) | 88 | 530 | 33621 |
| 1. Normalizado | 88 | 530 | 32019 |
| 2. Filtro de archivos (nav, stub, todo_only) | 65 | 516 | 31543 |
| 3. Filtro de secciones (cuerpo vacío, TO DO) | 65 | 433 | 31329 |
| 4. Dedup exacto | 42 | 238 | 20287 |
| 5. Dedup casi-duplicados (regla sin pérdida) | 40 | 234 | 19918 |

- Resultado: **234 secciones** = 232 canónicas + 2 variantes, en 232 clusters.
- En los pasos 0–1 los tokens incluyen navegación; desde el paso 2 se cuentan por sección.

## 2. Archivos excluidos del corpus

| Archivo | Motivo | Tokens de contenido |
|---|---|---|
| order-workflow-api/5.6.2-hotfix-1/guide/architecture.md | stub | 0 |
| price-engine-api/latest/guide/arquitectura.md | stub | 0 |
| price-engine-api/latest/guide/flujos.md | stub | 6 |
| zenith-keeper/1.1.6/guide/README.md | stub | 0 |
| price-engine-api/latest/guide/general.md | todo_only | 6 |

Además se excluyen **18 archivos de navegación** (`_sidebar.md`, `_coverpage.md`, `_navbar.md`, `coverpage.md`); su orden, títulos y frase de portada quedan como metadata (`nav_title`, `nav_order`, `nav_parent`, `project_tagline`) y en `nav.jsonl`.
Criterio de stub: menos de 8 tokens de contenido tras quitar headers e imágenes; **cuenta código, tablas y texto de links**.

**Secciones descartadas dentro de archivos conservados**

| Motivo | Secciones | Significado |
|---|---|---|
| empty_body | 83 | header sin cuerpo propio (contenedor) o solo imágenes; su título sigue en `section_path` de las hijas |
| todo | 0 | cuerpo con solo marcadores TO DO |

## 3. Efecto de la normalización

| Transformación | Ocurrencias |
|---|---|
| Entidades HTML decodificadas (`&#39;` → `'`), código incluido | 1084 |
| Tablas re-escritas sin padding | 54 |
| Filas de tabla vacías/rotas quitadas | 4 |
| Imágenes quitadas del texto (→ metadata `images`) | 22 |
| Badges quitados (→ metadata `badges`) | 7 |
| Comentarios HTML/docsify quitados | 4 |
| Atributos `style` quitados | 6 |
| Headers mal formados reparados (`#Título` → `# Título`) | 2 |
| H1 sintetizado desde el nombre de archivo | 5 |

**Casi-duplicados que se volvieron exactos solo por normalizar**

| Nivel | Grupos exactos (crudo) | Copias redundantes (crudo) | Grupos exactos (normalizado) | Copias redundantes (normalizado) | Copias detectadas solo por normalizar | Grupos que crecieron o aparecieron |
|---|---|---|---|---|---|---|
| Archivo | 15 | 21 | 15 | 23 | 2 | 2 |
| Sección (en corpus) | 157 | 189 | 157 | 195 | 6 | 6 |

Copias redundantes = elementos de un grupo exacto además del primero.

Archivos que pasaron a ser idénticos: `vendor-stockkeeper-api/0.0.10-stock-consumer/guide/alerts.md` = `vendor-stockkeeper-api/0.0.3-paused-seller/guide/alerts.md` = `vendor-stockkeeper-api/latest/guide/alerts.md`; `vendor-stockkeeper-api/0.0.10-stock-consumer/guide/important.md` = `vendor-stockkeeper-api/0.0.3-paused-seller/guide/important.md` = `vendor-stockkeeper-api/0.0.6-ep-restock-man/guide/important.md` = `vendor-stockkeeper-api/latest/guide/important.md`

<details><summary>Secciones que pasaron a ser idénticas</summary>

| Sección | Copias | Ubicaciones |
|---|---|---|
| Alerts › Alerts | 4 | vendor-stockkeeper-api/0.0.10-stock-consumer/guide/alerts.md<br>vendor-stockkeeper-api/0.0.3-paused-seller/guide/alerts.md<br>vendor-stockkeeper-api/0.0.6-ep-restock-man/guide/alerts.md<br>vendor-stockkeeper-api/latest/guide/alerts.md |
| Alerts › How to resolve › [LOW PRIORITY] Validation stock (publication has more stock than warehouse's stock | 3 | vendor-stockkeeper-api/0.0.10-stock-consumer/guide/alerts.md<br>vendor-stockkeeper-api/0.0.3-paused-seller/guide/alerts.md<br>vendor-stockkeeper-api/latest/guide/alerts.md |
| Domain › Services › Restock Consumer | 4 | vendor-stockkeeper-api/0.0.10-stock-consumer/guide/api.md<br>vendor-stockkeeper-api/0.0.3-paused-seller/guide/api.md<br>vendor-stockkeeper-api/0.0.6-ep-restock-man/guide/api.md<br>vendor-stockkeeper-api/latest/guide/api.md |
| Domain › Services › Feed Consumer | 4 | vendor-stockkeeper-api/0.0.10-stock-consumer/guide/api.md<br>vendor-stockkeeper-api/0.0.3-paused-seller/guide/api.md<br>vendor-stockkeeper-api/0.0.6-ep-restock-man/guide/api.md<br>vendor-stockkeeper-api/latest/guide/api.md |
| Verification of Items in Inventory Flows › How can we do it? › Restock Flow | 4 | vendor-stockkeeper-api/0.0.10-stock-consumer/guide/important.md<br>vendor-stockkeeper-api/0.0.3-paused-seller/guide/important.md<br>vendor-stockkeeper-api/0.0.6-ep-restock-man/guide/important.md<br>vendor-stockkeeper-api/latest/guide/important.md |
| Verification of Items in Inventory Flows › How can we do it? › Feed Flow | 4 | vendor-stockkeeper-api/0.0.10-stock-consumer/guide/important.md<br>vendor-stockkeeper-api/0.0.3-paused-seller/guide/important.md<br>vendor-stockkeeper-api/0.0.6-ep-restock-man/guide/important.md<br>vendor-stockkeeper-api/latest/guide/important.md |

</details>

## 4. Distribución de similitudes y umbral

Shingles de 5 palabras; Jaccard **exacto** entre los 186 representantes (uno por grupo exacto) con ≥ 20 tokens. 52 representantes más cortos solo participan del dedup exacto.

**Similitud máxima de cada sección con cualquier otra** (n = 186)

| Jaccard | Secciones |  |
|---|---|---|
| [0.0, 0.1) | 143 | ███████████████████████ |
| [0.1, 0.2) | 19 | ███ |
| [0.2, 0.3) | 6 | █ |
| [0.3, 0.4) | 6 | █ |
| [0.4, 0.5) | 0 |  |
| [0.5, 0.6) | 0 |  |
| [0.6, 0.7) | 2 |  |
| [0.7, 0.8) | 2 |  |
| [0.8, 0.9) | 2 |  |
| [0.9, 1.0] | 6 | █ |

**Pares con Jaccard ≥ 0.1** (n = 64 de 17205 pares posibles)

| Jaccard | Pares |  |
|---|---|---|
| [0.1, 0.2) | 42 | ██████████████████████████████ |
| [0.2, 0.3) | 9 | ██████ |
| [0.3, 0.4) | 7 | █████ |
| [0.4, 0.5) | 0 |  |
| [0.5, 0.6) | 0 |  |
| [0.6, 0.7) | 1 | █ |
| [0.7, 0.8) | 1 | █ |
| [0.8, 0.9) | 1 | █ |
| [0.9, 1.0] | 3 | ██ |

- Umbral: **Jaccard ≥ 0.6**. Par más similar por debajo: 0.350; par menos similar por encima: 0.688.
- Pares sobre el umbral: 6 (0 entre proyectos distintos).
- Recall de MinHash/LSH (umbral de banding 0.45, 128 permutaciones) frente al cálculo exhaustivo: **100%** (6/6); 6 candidatos verificados.

**Pares más similares bajo el umbral (0.3 ≤ Jaccard < 0.6)** — no se agrupan

| Jaccard | A | B |
|---|---|---|
| 0.350 | vendor-stockkeeper-api/0.0.6-ep-restock-man/guide/alerts.md › How to resolve › Error restock in vendor-stockkeeper-api | vendor-stockkeeper-api/0.0.6-ep-restock-man/guide/alerts.md › How to resolve › Stockkeeper-api - Error restocking item (negative quantity) |
| 0.348 | vendor-stockkeeper-api/0.0.10-stock-consumer/guide/alerts.md › How to resolve › [IMPORTANT] Stockkeeper-api - Error restocking item (negative quantity) | vendor-stockkeeper-api/0.0.6-ep-restock-man/guide/alerts.md › How to resolve › Error restock in vendor-stockkeeper-api |
| 0.348 | vendor-stockkeeper-api/0.0.10-stock-consumer/guide/alerts.md › How to resolve › [IMPORTANT] Error restock in vendor-stockkeeper-api | vendor-stockkeeper-api/0.0.6-ep-restock-man/guide/alerts.md › How to resolve › Stockkeeper-api - Error restocking item (negative quantity) |
| 0.346 | vendor-stockkeeper-api/0.0.10-stock-consumer/guide/alerts.md › How to resolve › [IMPORTANT] Error restock in vendor-stockkeeper-api | vendor-stockkeeper-api/0.0.10-stock-consumer/guide/alerts.md › How to resolve › [IMPORTANT] Stockkeeper-api - Error restocking item (negative quantity) |
| 0.333 | catalog-portfolio-api/0.0.1-test-bench-v2a/guide/api-reference/brands.md › Update Brand › `PUT /{brandId}` | catalog-portfolio-api/0.0.1-test-bench-v2a/guide/brand-management/README.md › Common Operations › Updating a Brand |
| 0.319 | catalog-portfolio-api/0.0.1-test-bench-v2a/guide/setup/README.md › Prerequisites Summary | catalog-portfolio-api/0.0.1-test-bench-v2a/guide/setup/local-development.md › Prerequisites |
| 0.316 | vendor-stockkeeper-api/0.0.10-stock-consumer/guide/api.md › Services › Restock Consumer | vendor-stockkeeper-api/0.0.10-stock-consumer/guide/api.md › Services › Feed Consumer |

**Pares fusionados más cercanos al umbral**

| Jaccard | A | B |
|---|---|---|
| 0.688 | vendor-stockkeeper-api/0.0.10-stock-consumer/guide/alerts.md › How to resolve › [LOW PRIORITY] Validation stock (publication has more stock than warehouse's stock | vendor-stockkeeper-api/0.0.6-ep-restock-man/guide/alerts.md › How to resolve › Validation stock (publication has more stock than warehouse's stock |
| 0.762 | 2p-revenue-optimizer-api/0.2.2/guide/pages/table_data_dictionary/rule_header.md › rule_header Table | 2p-revenue-optimizer-api/latest/guide/pages/table_data_dictionary/rule_header.md › rule_header Table |
| 0.859 | vendor-stockkeeper-api/0.0.10-stock-consumer/guide/api.md › Services | vendor-stockkeeper-api/0.0.3-paused-seller/guide/api.md › Services |
| 0.917 | 2p-revenue-optimizer-api/0.2.2/guide/pages/table_data_dictionary/rule_row.md › rule_row Table | 2p-revenue-optimizer-api/latest/guide/pages/table_data_dictionary/rule_row.md › rule_row Table |
| 0.990 | vendor-stockkeeper-api/0.0.10-stock-consumer/guide/alerts.md › How to resolve › [IMPORTANT] Error restock in vendor-stockkeeper-api | vendor-stockkeeper-api/0.0.6-ep-restock-man/guide/alerts.md › How to resolve › Error restock in vendor-stockkeeper-api |
| 0.993 | vendor-stockkeeper-api/0.0.10-stock-consumer/guide/alerts.md › How to resolve › [IMPORTANT] Stockkeeper-api - Error restocking item (negative quantity) | vendor-stockkeeper-api/0.0.6-ep-restock-man/guide/alerts.md › How to resolve › Stockkeeper-api - Error restocking item (negative quantity) |

## 5. Clusters de casi-duplicados y regla de fusión

Dentro de cada cluster, la canónica es la sección con más líneas. Otra sección se **absorbe** (pasa a `occurrences`) solo si todas sus líneas ya están en una sección conservada; si aporta al menos una línea nueva queda como **variante** (mismo `cluster_id`, `variant_of` → canónica). No se pierde contenido único.

| Cluster | Representantes | Secciones | Jaccard mín. | Canónica | Absorbidas | Variantes | Proyectos |
|---|---|---|---|---|---|---|---|
| cl-7c88c2e2fa86 | 2 | 4 | 0.99 | vendor-stockkeeper-api/0.0.10-stock-consumer/guide/alerts.md#004 | 1 | 0 | vendor-stockkeeper-api |
| cl-ad2e9580cd32 | 2 | 4 | 0.99 | vendor-stockkeeper-api/0.0.10-stock-consumer/guide/alerts.md#003 | 1 | 0 | vendor-stockkeeper-api |
| cl-b750bbdc9217 | 2 | 4 | 0.86 | vendor-stockkeeper-api/0.0.10-stock-consumer/guide/api.md#002 | 1 | 0 | vendor-stockkeeper-api |
| cl-c36dd1f6921b | 2 | 4 | 0.69 | vendor-stockkeeper-api/0.0.10-stock-consumer/guide/alerts.md#005 | 0 | 1 | vendor-stockkeeper-api |
| cl-916d8eb8beef | 2 | 2 | 0.76 | 2p-revenue-optimizer-api/0.2.2/guide/pages/table_data_dictionary/rule_header.md#000 | 0 | 1 | 2p-revenue-optimizer-api |
| cl-c3fb6265ac02 | 2 | 2 | 0.92 | 2p-revenue-optimizer-api/0.2.2/guide/pages/table_data_dictionary/rule_row.md#000 | 1 | 0 | 2p-revenue-optimizer-api |

**Redundancia que queda (costo de no perder contenido):** 2 variantes con 206 tokens; de ellos 118 tokens están en líneas compartidas con su canónica = **0.6%** del corpus final (19918 tokens).

<details><summary>Líneas únicas que justifican cada variante</summary>

- `2p-revenue-optimizer-api/latest/guide/pages/table_data_dictionary/rule_header.md#000` (variante de `2p-revenue-optimizer-api/0.2.2/guide/pages/table_data_dictionary/rule_header.md#000`, J = 0.762): `| date | timestamp | Not null | Date timestamp when was created | DEFAULT_GENERATED |`; `| version | int | Not null | Version |  |`
- `vendor-stockkeeper-api/0.0.6-ep-restock-man/guide/alerts.md#005` (variante de `vendor-stockkeeper-api/0.0.10-stock-consumer/guide/alerts.md#005`, J = 0.688): `2. You should confirm that the item was correctly paused by **checking the item's status**`; `This alert happens when something goes wrong while trying to sell a publication without st`

</details>

## 6. Ejemplos de pares casi-duplicados

### Jaccard 0.688 — mismo cluster → variante (aporta líneas nuevas)

- A: `vendor-stockkeeper-api/0.0.10-stock-consumer/guide/alerts.md › How to resolve › [LOW PRIORITY] Validation stock (publication has more stock than warehouse's stock` (0.0.10-stock-consumer)
- B: `vendor-stockkeeper-api/0.0.6-ep-restock-man/guide/alerts.md › How to resolve › Validation stock (publication has more stock than warehouse's stock` (0.0.6-ep-restock-man)

````diff
@@ -1,5 +1,4 @@
-### [LOW PRIORITY] Validation stock (publication has more stock than warehouse's stock
+### Validation stock (publication has more stock than warehouse's stock
 
-This alert is to verify that item was correctly paused.
-It happens when something goes wrong while trying to sell a publication without stock into 3PL facilities
+This alert happens when something goes wrong while trying to sell a publication without stocK into 3PL facilities
 
@@ -7,5 +6,3 @@
 1. You should review the **vendor-stockkeeper-api** logs with the **stream-prod** scope to easily identify the item and SKU associated with the potential out-of-stock sale.
-2. You should confirm that the item was correctly paused by **checking the item's status**. You need to use api core item endpoint with item_id and check "status" If the item was not correctly paused, you should raise a ticket in Shield to request the publication be blocked to prevent potential out-of-stock sales.
+2. You should confirm that the item was correctly paused by **checking the item's status**. If the item was not correctly paused, you should raise a ticket in Shield to request the publication be blocked to prevent potential out-of-stock sales.
 3. Additionally, you should identify the item to monitor it in case of future out-of-stock sales.
-
-PS: This alert is just to check item was correctly paused, it may be works automatically
````

### Jaccard 0.859 — mismo cluster → absorbida en la canónica

- A: `vendor-stockkeeper-api/0.0.10-stock-consumer/guide/api.md › Services` (0.0.10-stock-consumer)
- B: `vendor-stockkeeper-api/0.0.3-paused-seller/guide/api.md › Services` (0.0.3-paused-seller)

````diff
@@ -9,2 +9 @@
 | GET | [Get Detail Doma](#item-detail) | `/stock-operations/3pl/{identifierRegister}` |
-| GET | [Operation Validation Consumer](#) | `/stock-operations/3pl/validation/restock-consumer` |
````

### Jaccard 0.990 — mismo cluster → absorbida en la canónica

- A: `vendor-stockkeeper-api/0.0.10-stock-consumer/guide/alerts.md › How to resolve › [IMPORTANT] Error restock in vendor-stockkeeper-api` (0.0.10-stock-consumer)
- B: `vendor-stockkeeper-api/0.0.6-ep-restock-man/guide/alerts.md › How to resolve › Error restock in vendor-stockkeeper-api` (0.0.6-ep-restock-man)

````diff
@@ -1,2 +1,2 @@
-### [IMPORTANT] Error restock in vendor-stockkeeper-api
+### Error restock in vendor-stockkeeper-api
 
````

### Jaccard 0.993 — mismo cluster → absorbida en la canónica

- A: `vendor-stockkeeper-api/0.0.10-stock-consumer/guide/alerts.md › How to resolve › [IMPORTANT] Stockkeeper-api - Error restocking item (negative quantity)` (0.0.10-stock-consumer)
- B: `vendor-stockkeeper-api/0.0.6-ep-restock-man/guide/alerts.md › How to resolve › Stockkeeper-api - Error restocking item (negative quantity)` (0.0.6-ep-restock-man)

````diff
@@ -1,2 +1,2 @@
-### [IMPORTANT] Stockkeeper-api - Error restocking item (negative quantity)
+### Stockkeeper-api - Error restocking item (negative quantity)
 
````

### Jaccard 0.350 — rechazado (bajo el umbral)

- A: `vendor-stockkeeper-api/0.0.6-ep-restock-man/guide/alerts.md › How to resolve › Error restock in vendor-stockkeeper-api` (0.0.6-ep-restock-man)
- B: `vendor-stockkeeper-api/0.0.6-ep-restock-man/guide/alerts.md › How to resolve › Stockkeeper-api - Error restocking item (negative quantity)` (0.0.6-ep-restock-man)

````diff
@@ -1,9 +1,11 @@
-### Error restock in vendor-stockkeeper-api
+### Stockkeeper-api - Error restocking item (negative quantity)
 
-This alert happens when something goes wrong while trying to restock
-This error can be generated by any really rare case that has not been controlled in the code, so it is important to check the logs to identify the problem.
+This alert happens when something goes wrong while trying to restock publications and this publication has negative quantity
+This case does not have a specific process defined as it is a very rare case that has not been controlled in the code, so it is important to check the logs to identify the problem.
 
 To resolve this alert, you need to do the following:
-1. Identify in the **vendor-stockkeeper-api** logs which item could not be restocked correctly and determine the reason for this.
-2. Resolve the issue.
-3. It may be necessary to perform a manual restock via the database or, in the most extreme case, release a new version.
+1. Identify in the **vendor-stockkeeper-api** logs which item is associated with the negative restock attempt.
+2. Notify to **Envio Pack** that the restock could not be completed correctly.
+3. Proceed to identify what happened (why a restock is executed that leaves the available quantities below 0).
+4. Resolve the issue.
+5. It may be necessary to perform a manual restock via the database or, in the most extreme case, release a new version.
````

## 7. Versiones: declarada vs. efectiva (por contenido)

La versión efectiva de una carpeta alias (`latest`) es la carpeta concreta con contenido idéntico (mismo conjunto de hashes de sección); si no existe, se usa la declarada en `documentationTypes.json`.

| Carpeta | Declarada | Efectiva | Idéntica a | Más parecida (Jaccard) | Observación |
|---|---|---|---|---|---|
| 2p-revenue-optimizer-api/0.2.2 | 0.2.2 | 0.2.2 | — | latest (0.72) | ok |
| 2p-revenue-optimizer-api/latest | 0.0.3-rc-1 | 0.0.3-rc-1 | — | 0.2.2 (0.72) | sin carpeta idéntica; más parecida `0.2.2` (Jaccard de secciones 0.72, contenido ≠ `0.2.2`) |
| catalog-portfolio-api/0.0.1-test-bench-v2a | 0.0.1-test-bench-v2a | 0.0.1-test-bench-v2a | latest | latest (1.00) | ok |
| catalog-portfolio-api/latest | 0.0.1-test-bench-v2a | 0.0.1-test-bench-v2a | 0.0.1-test-bench-v2a | 0.0.1-test-bench-v2a (1.00) | ok |
| demand-forecast-docs/latest | 0.1.3 | 0.1.3 | — | — | ok |
| order-workflow-api/5.6.2-hotfix-1 | 5.6.2-hotfix-1 | 5.6.2-hotfix-1 | — | — | ok |
| payment-promise-gateway/0.0.10-test-crc-migration | 0.0.10-test-crc-migration | 0.0.10-test-crc-migration | latest | latest (1.00) | ok |
| payment-promise-gateway/latest | 3.7.0 | 0.0.10-test-crc-migration | 0.0.10-test-crc-migration | 0.0.10-test-crc-migration (1.00) | declara `3.7.0` (no presente en docs_raw) pero el contenido es idéntico a `0.0.10-test-crc-migration` |
| price-engine-api/latest | 0.0.2-setting-up | 0.0.2-setting-up | — | — | ok |
| traffic-gate-api/latest | 1.65.0 | 1.65.0 | — | — | ok |
| unified-transaction-configs/v0.0.2 | v0.0.2 | v0.0.2 | — | — | ok |
| vendor-stockkeeper-api/0.0.10-stock-consumer | 0.0.10-stock-consumer | 0.0.10-stock-consumer | — | latest (0.89) | ok |
| vendor-stockkeeper-api/0.0.3-paused-seller | 0.0.3-paused-seller | 0.0.3-paused-seller | latest | latest (1.00) | ok |
| vendor-stockkeeper-api/0.0.6-ep-restock-man | 0.0.6-ep-restock-man | 0.0.6-ep-restock-man | — | latest (0.79) | ok |
| vendor-stockkeeper-api/latest | 0.41.0 | 0.0.3-paused-seller | 0.0.3-paused-seller | 0.0.3-paused-seller (1.00) | declara `0.41.0` (no presente en docs_raw) pero el contenido es idéntico a `0.0.3-paused-seller` |
| zenith-keeper/1.1.6 | 1.1.6 | 1.1.6 | — | — | ok |

<!-- threshold-validation:start -->
## 8. Validación del umbral con etiquetas humanas

Sin etiquetas todavía: `meli-etl label-pairs` genera `data/labels/near_dup_labels.csv`; completarlo y correr `meli-etl validate-threshold`.
<!-- threshold-validation:end -->

## Salidas

- `sections_dedup.jsonl`: secciones canónicas y variantes con `occurrences` (proyecto, versión declarada/efectiva, archivo, `section_path`, tipo de match).
- `cluster_id` agrupa duplicados exactos y casi-duplicados: **es la clave del split train/eval**.
- `versions.json`, `nav.jsonl`, `normalized_docs.jsonl`, `sections.jsonl` en `processed_dir`.
- `near_dup_pairs.jsonl`: pares de representantes con Jaccard ≥ 0.1 (insumo de `label-pairs` y `validate-threshold`).
