# Perfil de `docs_raw`

Fuente: `data/raw/docs_raw`. Generado por `meli-etl profile` (determinista: misma entrada → mismo reporte).

## 1. Resumen

| Métrica | Valor |
|---|---|
| Proyectos | 10 |
| Carpetas de versión | 16 |
| Archivos | 107 |
| Tamaño total (KB) | 314.7 |
| Markdown de contenido | 70 |
| Markdown de navegación (_sidebar/_coverpage) | 18 |
| Specs (swagger/openapi) | 3 |
| Metadatos (documentationTypes.json) | 16 |
| Grupos de duplicados exactos (sha256) | 19 |
| Archivos redundantes (copias sobre el primero) | 28 (26%) |
| Grupos duplicados solo tras normalizar espacios | 0 |
| Contenido vacío / solo TO DO / stub | 0 / 1 / 6 |
| Contenido con al menos una sección TO DO | 1 |
| Idioma del contenido (es / en / mixed / unknown) | 9 / 51 / 0 / 10 |
| Archivos no UTF-8 | 0 |

## 2. Archivos por proyecto / versión / tipo

| Proyecto | Versión (carpeta) | Versión resuelta | Total | content | nav | spec | meta | other | KB |
|---|---|---|---|---|---|---|---|---|---|
| 2p-revenue-optimizer-api | 0.2.2 | = | 4 | 3 | 0 | 0 | 1 | 0 | 6.9 |
| 2p-revenue-optimizer-api | latest | 0.0.3-rc-1 | 5 | 4 | 0 | 0 | 1 | 0 | 7.6 |
| catalog-portfolio-api | 0.0.1-test-bench-v2a | = | 10 | 8 | 1 | 0 | 1 | 0 | 33.1 |
| catalog-portfolio-api | latest | 0.0.1-test-bench-v2a | 10 | 8 | 1 | 0 | 1 | 0 | 33.1 |
| demand-forecast-docs | latest | 0.1.3 | 6 | 4 | 1 | 0 | 1 | 0 | 46.2 |
| order-workflow-api | 5.6.2-hotfix-1 | = | 10 | 8 | 1 | 0 | 1 | 0 | 19.2 |
| payment-promise-gateway | 0.0.10-test-crc-migration | = | 2 | 1 | 0 | 0 | 1 | 0 | 16.1 |
| payment-promise-gateway | latest | 3.7.0 | 2 | 1 | 0 | 0 | 1 | 0 | 16.1 |
| price-engine-api | latest | 0.0.2-setting-up | 8 | 4 | 2 | 1 | 1 | 0 | 6.2 |
| traffic-gate-api | latest | 1.65.0 | 9 | 5 | 2 | 1 | 1 | 0 | 35.9 |
| unified-transaction-configs | v0.0.2 | = | 4 | 2 | 1 | 0 | 1 | 0 | 2.2 |
| vendor-stockkeeper-api | 0.0.10-stock-consumer | = | 8 | 5 | 2 | 0 | 1 | 0 | 20.1 |
| vendor-stockkeeper-api | 0.0.3-paused-seller | = | 8 | 5 | 2 | 0 | 1 | 0 | 16.4 |
| vendor-stockkeeper-api | 0.0.6-ep-restock-man | = | 8 | 5 | 2 | 0 | 1 | 0 | 16.1 |
| vendor-stockkeeper-api | latest | 0.41.0 | 8 | 5 | 2 | 0 | 1 | 0 | 16.4 |
| zenith-keeper | 1.1.6 | = | 5 | 2 | 1 | 1 | 1 | 0 | 23.1 |

### Totales por tipo

| Tipo | Extensiones | Archivos | KB |
|---|---|---|---|
| content | md | 70 | 278.9 |
| nav | md | 18 | 4.2 |
| spec | yaml | 3 | 29.7 |
| meta | json | 16 | 1.9 |

### Versiones alias (`latest`) resueltas vía documentationTypes.json

| Proyecto | Alias | Apunta a | ¿Esa versión también está en docs_raw? |
|---|---|---|---|
| 2p-revenue-optimizer-api | latest | 0.0.3-rc-1 | no |
| catalog-portfolio-api | latest | 0.0.1-test-bench-v2a | sí |
| demand-forecast-docs | latest | 0.1.3 | no |
| payment-promise-gateway | latest | 3.7.0 | no |
| price-engine-api | latest | 0.0.2-setting-up | no |
| traffic-gate-api | latest | 1.65.0 | no |
| vendor-stockkeeper-api | latest | 0.41.0 | no |

## 3. Tamaños (Markdown de contenido)

| Métrica | min | p25 | mediana | p90 | max | media |
|---|---|---|---|---|---|---|
| Bytes | 33 | 670 | 2892 | 8878 | 41345 | 4080 |
| Palabras útiles | 0 | 43 | 109 | 594 | 2022 | 242 |

**Los 10 más grandes**

| Archivo | Bytes | Palabras |
|---|---|---|
| demand-forecast-docs/latest/guide/overview.md | 41345 | 2022 |
| payment-promise-gateway/0.0.10-test-crc-migration/guide/README.md | 16420 | 611 |
| payment-promise-gateway/latest/guide/README.md | 16420 | 611 |
| vendor-stockkeeper-api/0.0.10-stock-consumer/guide/important.md | 10918 | 384 |
| zenith-keeper/1.1.6/guide/use-cases.md | 9542 | 54 |
| vendor-stockkeeper-api/0.0.3-paused-seller/guide/important.md | 8878 | 384 |
| vendor-stockkeeper-api/0.0.6-ep-restock-man/guide/important.md | 8878 | 384 |
| vendor-stockkeeper-api/latest/guide/important.md | 8878 | 384 |
| order-workflow-api/5.6.2-hotfix-1/guide/use-cases.md | 8085 | 65 |
| traffic-gate-api/latest/guide/sections/processes.md | 7565 | 1052 |

**Los 10 más chicos**

| Archivo | Bytes | Palabras |
|---|---|---|
| zenith-keeper/1.1.6/guide/README.md | 33 | 0 |
| price-engine-api/latest/guide/flujos.md | 93 | 4 |
| unified-transaction-configs/v0.0.2/guide/README.md | 124 | 16 |
| order-workflow-api/5.6.2-hotfix-1/guide/usage.md | 134 | 10 |
| order-workflow-api/5.6.2-hotfix-1/guide/architecture.md | 143 | 0 |
| price-engine-api/latest/guide/arquitectura.md | 206 | 0 |
| order-workflow-api/5.6.2-hotfix-1/guide/services/jobs.md | 225 | 14 |
| demand-forecast-docs/latest/guide/explicabilidad/README.md | 259 | 43 |
| price-engine-api/latest/guide/general.md | 281 | 0 |
| vendor-stockkeeper-api/latest/guide/introduction.md | 363 | 49 |

## 4. Duplicados exactos (sha256 de bytes)

| Hash | Tipo | Copias | Cruza versiones | Cruza proyectos | Archivos |
|---|---|---|---|---|---|
| `3422e2707f` | nav | 4 | sí | no | vendor-stockkeeper-api/0.0.10-stock-consumer/guide/_sidebar.md<br>vendor-stockkeeper-api/0.0.3-paused-seller/guide/_sidebar.md<br>vendor-stockkeeper-api/0.0.6-ep-restock-man/guide/_sidebar.md<br>vendor-stockkeeper-api/latest/guide/_sidebar.md |
| `192ad05714` | content | 4 | sí | no | vendor-stockkeeper-api/0.0.10-stock-consumer/guide/database.md<br>vendor-stockkeeper-api/0.0.3-paused-seller/guide/database.md<br>vendor-stockkeeper-api/0.0.6-ep-restock-man/guide/database.md<br>vendor-stockkeeper-api/latest/guide/database.md |
| `2d5b63d66e` | content | 4 | sí | no | vendor-stockkeeper-api/0.0.10-stock-consumer/guide/introduction.md<br>vendor-stockkeeper-api/0.0.3-paused-seller/guide/introduction.md<br>vendor-stockkeeper-api/0.0.6-ep-restock-man/guide/introduction.md<br>vendor-stockkeeper-api/latest/guide/introduction.md |
| `823b80efb8` | nav | 3 | sí | no | vendor-stockkeeper-api/0.0.3-paused-seller/guide/_coverpage.md<br>vendor-stockkeeper-api/0.0.6-ep-restock-man/guide/_coverpage.md<br>vendor-stockkeeper-api/latest/guide/_coverpage.md |
| `5969b94da6` | content | 3 | sí | no | vendor-stockkeeper-api/0.0.3-paused-seller/guide/api.md<br>vendor-stockkeeper-api/0.0.6-ep-restock-man/guide/api.md<br>vendor-stockkeeper-api/latest/guide/api.md |
| `d3cf4bacb0` | content | 3 | sí | no | vendor-stockkeeper-api/0.0.3-paused-seller/guide/important.md<br>vendor-stockkeeper-api/0.0.6-ep-restock-man/guide/important.md<br>vendor-stockkeeper-api/latest/guide/important.md |
| `68f3dcfa78` | content | 2 | sí | no | 2p-revenue-optimizer-api/0.2.2/guide/README.md<br>2p-revenue-optimizer-api/latest/guide/README.md |
| `a1dae64541` | meta | 2 | sí | no | catalog-portfolio-api/0.0.1-test-bench-v2a/documentationTypes.json<br>catalog-portfolio-api/latest/documentationTypes.json |
| `173c90bc9c` | content | 2 | sí | no | catalog-portfolio-api/0.0.1-test-bench-v2a/guide/README.md<br>catalog-portfolio-api/latest/guide/README.md |
| `44bbcf8021` | nav | 2 | sí | no | catalog-portfolio-api/0.0.1-test-bench-v2a/guide/_sidebar.md<br>catalog-portfolio-api/latest/guide/_sidebar.md |
| `7bbd3e021e` | content | 2 | sí | no | catalog-portfolio-api/0.0.1-test-bench-v2a/guide/api-reference/README.md<br>catalog-portfolio-api/latest/guide/api-reference/README.md |
| `c6b1f62f36` | content | 2 | sí | no | catalog-portfolio-api/0.0.1-test-bench-v2a/guide/api-reference/brands.md<br>catalog-portfolio-api/latest/guide/api-reference/brands.md |
| `4969517afa` | content | 2 | sí | no | catalog-portfolio-api/0.0.1-test-bench-v2a/guide/architecture/README.md<br>catalog-portfolio-api/latest/guide/architecture/README.md |
| `ceb67021a8` | content | 2 | sí | no | catalog-portfolio-api/0.0.1-test-bench-v2a/guide/brand-management/README.md<br>catalog-portfolio-api/latest/guide/brand-management/README.md |
| `46c97404c3` | content | 2 | sí | no | catalog-portfolio-api/0.0.1-test-bench-v2a/guide/setup/README.md<br>catalog-portfolio-api/latest/guide/setup/README.md |
| `69bc58f5cc` | content | 2 | sí | no | catalog-portfolio-api/0.0.1-test-bench-v2a/guide/setup/local-development.md<br>catalog-portfolio-api/latest/guide/setup/local-development.md |
| `b416434452` | content | 2 | sí | no | catalog-portfolio-api/0.0.1-test-bench-v2a/guide/troubleshooting/README.md<br>catalog-portfolio-api/latest/guide/troubleshooting/README.md |
| `220972a5d6` | content | 2 | sí | no | payment-promise-gateway/0.0.10-test-crc-migration/guide/README.md<br>payment-promise-gateway/latest/guide/README.md |
| `5fcedac0bd` | content | 2 | sí | no | vendor-stockkeeper-api/0.0.3-paused-seller/guide/alerts.md<br>vendor-stockkeeper-api/latest/guide/alerts.md |

**Redundancia por proyecto** (archivos que tienen al menos una copia exacta)

| Proyecto | Archivos | Con copia exacta | % |
|---|---|---|---|
| 2p-revenue-optimizer-api | 9 | 2 | 22% |
| catalog-portfolio-api | 20 | 20 | 100% |
| demand-forecast-docs | 6 | 0 | 0% |
| order-workflow-api | 10 | 0 | 0% |
| payment-promise-gateway | 4 | 2 | 50% |
| price-engine-api | 8 | 0 | 0% |
| traffic-gate-api | 9 | 0 | 0% |
| unified-transaction-configs | 4 | 0 | 0% |
| vendor-stockkeeper-api | 32 | 23 | 72% |
| zenith-keeper | 5 | 0 | 0% |

### Duplicados solo tras normalizar espacios / saltos de línea

_Ninguno adicional: las copias o son idénticas byte a byte o difieren en contenido._

## 5. Archivos vacíos, "TO DO" y stubs

| Archivo | Estado | Palabras útiles | Bytes |
|---|---|---|---|
| order-workflow-api/5.6.2-hotfix-1/guide/architecture.md | stub | 0 | 143 |
| order-workflow-api/5.6.2-hotfix-1/guide/services/jobs.md | stub | 14 | 225 |
| order-workflow-api/5.6.2-hotfix-1/guide/usage.md | stub | 10 | 134 |
| price-engine-api/latest/guide/arquitectura.md | stub | 0 | 206 |
| price-engine-api/latest/guide/flujos.md | stub | 4 | 93 |
| zenith-keeper/1.1.6/guide/README.md | stub | 0 | 33 |
| price-engine-api/latest/guide/general.md | todo_only | 0 | 281 |

### Secciones TO DO dentro de archivos

| Archivo | Secciones TO DO / total | Secciones |
|---|---|---|
| price-engine-api/latest/guide/general.md | 3 / 5 | General > Introducción<br>General > Responsabilidades > Price Engine API es responsable de:<br>General > Responsabilidades > Price Engine API no se responsabiliza por: |

## 6. Idioma detectado

Heurística de stopwords es/en sobre el texto sin código, URLs ni badges. `mixed` = el idioma dominante tiene < 70% de las stopwords; `unknown` = menos de 3 stopwords.

| Proyecto | es | en | mixed | unknown |
|---|---|---|---|---|
| 2p-revenue-optimizer-api | 0 | 7 | 0 | 0 |
| catalog-portfolio-api | 0 | 16 | 0 | 0 |
| demand-forecast-docs | 0 | 4 | 0 | 0 |
| order-workflow-api | 0 | 6 | 0 | 2 |
| payment-promise-gateway | 0 | 2 | 0 | 0 |
| price-engine-api | 2 | 0 | 0 | 2 |
| traffic-gate-api | 5 | 0 | 0 | 0 |
| unified-transaction-configs | 2 | 0 | 0 | 0 |
| vendor-stockkeeper-api | 0 | 16 | 0 | 4 |
| zenith-keeper | 0 | 0 | 0 | 2 |

<details><summary>Idioma por archivo de contenido</summary>

| Archivo | Idioma | hits es | hits en |
|---|---|---|---|
| 2p-revenue-optimizer-api/0.2.2/guide/README.md | en | 0 | 143 |
| 2p-revenue-optimizer-api/0.2.2/guide/pages/table_data_dictionary/rule_header.md | en | 0 | 17 |
| 2p-revenue-optimizer-api/0.2.2/guide/pages/table_data_dictionary/rule_row.md | en | 0 | 7 |
| 2p-revenue-optimizer-api/latest/guide/README.md | en | 0 | 143 |
| 2p-revenue-optimizer-api/latest/guide/pages/table_data_dictionary/rule_custom_field.md | en | 0 | 9 |
| 2p-revenue-optimizer-api/latest/guide/pages/table_data_dictionary/rule_header.md | en | 0 | 18 |
| 2p-revenue-optimizer-api/latest/guide/pages/table_data_dictionary/rule_row.md | en | 0 | 7 |
| catalog-portfolio-api/0.0.1-test-bench-v2a/guide/README.md | en | 0 | 39 |
| catalog-portfolio-api/0.0.1-test-bench-v2a/guide/api-reference/README.md | en | 0 | 18 |
| catalog-portfolio-api/0.0.1-test-bench-v2a/guide/api-reference/brands.md | en | 0 | 34 |
| catalog-portfolio-api/0.0.1-test-bench-v2a/guide/architecture/README.md | en | 0 | 31 |
| catalog-portfolio-api/0.0.1-test-bench-v2a/guide/brand-management/README.md | en | 0 | 68 |
| catalog-portfolio-api/0.0.1-test-bench-v2a/guide/setup/README.md | en | 0 | 19 |
| catalog-portfolio-api/0.0.1-test-bench-v2a/guide/setup/local-development.md | en | 0 | 18 |
| catalog-portfolio-api/0.0.1-test-bench-v2a/guide/troubleshooting/README.md | en | 0 | 42 |
| catalog-portfolio-api/latest/guide/README.md | en | 0 | 39 |
| catalog-portfolio-api/latest/guide/api-reference/README.md | en | 0 | 18 |
| catalog-portfolio-api/latest/guide/api-reference/brands.md | en | 0 | 34 |
| catalog-portfolio-api/latest/guide/architecture/README.md | en | 0 | 31 |
| catalog-portfolio-api/latest/guide/brand-management/README.md | en | 0 | 68 |
| catalog-portfolio-api/latest/guide/setup/README.md | en | 0 | 19 |
| catalog-portfolio-api/latest/guide/setup/local-development.md | en | 0 | 18 |
| catalog-portfolio-api/latest/guide/troubleshooting/README.md | en | 0 | 42 |
| demand-forecast-docs/latest/guide/README.md | en | 0 | 58 |
| demand-forecast-docs/latest/guide/explicabilidad/README.md | en | 0 | 15 |
| demand-forecast-docs/latest/guide/explicabilidad/diarizacion.md | en | 6 | 153 |
| demand-forecast-docs/latest/guide/overview.md | en | 1 | 735 |
| order-workflow-api/5.6.2-hotfix-1/guide/README.md | en | 0 | 26 |
| order-workflow-api/5.6.2-hotfix-1/guide/architecture.md | unknown | 0 | 0 |
| order-workflow-api/5.6.2-hotfix-1/guide/development.md | en | 0 | 19 |
| order-workflow-api/5.6.2-hotfix-1/guide/services/bigq.md | en | 0 | 7 |
| order-workflow-api/5.6.2-hotfix-1/guide/services/database.md | en | 1 | 4 |
| order-workflow-api/5.6.2-hotfix-1/guide/services/jobs.md | unknown | 0 | 1 |
| order-workflow-api/5.6.2-hotfix-1/guide/usage.md | en | 0 | 3 |
| order-workflow-api/5.6.2-hotfix-1/guide/use-cases.md | en | 0 | 15 |
| payment-promise-gateway/0.0.10-test-crc-migration/guide/README.md | en | 0 | 117 |
| payment-promise-gateway/latest/guide/README.md | en | 0 | 117 |
| price-engine-api/latest/guide/arquitectura.md | unknown | 1 | 0 |
| price-engine-api/latest/guide/contacto.md | es | 4 | 0 |
| price-engine-api/latest/guide/flujos.md | unknown | 0 | 0 |
| price-engine-api/latest/guide/general.md | es | 3 | 0 |
| traffic-gate-api/latest/guide/README.md | es | 196 | 0 |
| traffic-gate-api/latest/guide/sections/arch.md | es | 175 | 0 |
| traffic-gate-api/latest/guide/sections/database.md | es | 124 | 0 |
| traffic-gate-api/latest/guide/sections/processes.md | es | 386 | 0 |
| traffic-gate-api/latest/guide/sections/waf_config.md | es | 138 | 0 |
| unified-transaction-configs/v0.0.2/guide/README.md | es | 6 | 0 |
| unified-transaction-configs/v0.0.2/guide/howto.md | es | 61 | 0 |
| vendor-stockkeeper-api/0.0.10-stock-consumer/guide/alerts.md | en | 0 | 196 |
| vendor-stockkeeper-api/0.0.10-stock-consumer/guide/api.md | unknown | 0 | 0 |
| vendor-stockkeeper-api/0.0.10-stock-consumer/guide/database.md | en | 0 | 6 |
| vendor-stockkeeper-api/0.0.10-stock-consumer/guide/important.md | en | 0 | 137 |
| vendor-stockkeeper-api/0.0.10-stock-consumer/guide/introduction.md | en | 0 | 16 |
| vendor-stockkeeper-api/0.0.3-paused-seller/guide/alerts.md | en | 0 | 196 |
| vendor-stockkeeper-api/0.0.3-paused-seller/guide/api.md | unknown | 0 | 0 |
| vendor-stockkeeper-api/0.0.3-paused-seller/guide/database.md | en | 0 | 6 |
| vendor-stockkeeper-api/0.0.3-paused-seller/guide/important.md | en | 0 | 137 |
| vendor-stockkeeper-api/0.0.3-paused-seller/guide/introduction.md | en | 0 | 16 |
| vendor-stockkeeper-api/0.0.6-ep-restock-man/guide/alerts.md | en | 0 | 184 |
| vendor-stockkeeper-api/0.0.6-ep-restock-man/guide/api.md | unknown | 0 | 0 |
| vendor-stockkeeper-api/0.0.6-ep-restock-man/guide/database.md | en | 0 | 6 |
| vendor-stockkeeper-api/0.0.6-ep-restock-man/guide/important.md | en | 0 | 137 |
| vendor-stockkeeper-api/0.0.6-ep-restock-man/guide/introduction.md | en | 0 | 16 |
| vendor-stockkeeper-api/latest/guide/alerts.md | en | 0 | 196 |
| vendor-stockkeeper-api/latest/guide/api.md | unknown | 0 | 0 |
| vendor-stockkeeper-api/latest/guide/database.md | en | 0 | 6 |
| vendor-stockkeeper-api/latest/guide/important.md | en | 0 | 137 |
| vendor-stockkeeper-api/latest/guide/introduction.md | en | 0 | 16 |
| zenith-keeper/1.1.6/guide/README.md | unknown | 0 | 0 |
| zenith-keeper/1.1.6/guide/use-cases.md | unknown | 0 | 0 |

</details>

## 7. Headers por archivo

`H1` = cantidad de headers de nivel 1; `saltos` = transiciones que saltean niveles (p. ej. H1→H3); `mal formados` = `#Título` sin espacio (no es header en CommonMark).

| Archivo | Tipo | Headers | H1 | Prof. máx. | Saltos | Mal formados |
|---|---|---|---|---|---|---|
| 2p-revenue-optimizer-api/0.2.2/guide/README.md | content | 13 | 2 | 4 | 0 | 0 |
| 2p-revenue-optimizer-api/0.2.2/guide/pages/table_data_dictionary/rule_header.md | content | 1 | 1 | 1 | 0 | 0 |
| 2p-revenue-optimizer-api/0.2.2/guide/pages/table_data_dictionary/rule_row.md | content | 1 | 1 | 1 | 0 | 0 |
| 2p-revenue-optimizer-api/latest/guide/README.md | content | 13 | 2 | 4 | 0 | 0 |
| 2p-revenue-optimizer-api/latest/guide/pages/table_data_dictionary/rule_custom_field.md | content | 1 | 1 | 1 | 0 | 0 |
| 2p-revenue-optimizer-api/latest/guide/pages/table_data_dictionary/rule_header.md | content | 1 | 1 | 1 | 0 | 0 |
| 2p-revenue-optimizer-api/latest/guide/pages/table_data_dictionary/rule_row.md | content | 1 | 1 | 1 | 0 | 0 |
| catalog-portfolio-api/0.0.1-test-bench-v2a/guide/README.md | content | 7 | 1 | 2 | 0 | 0 |
| catalog-portfolio-api/0.0.1-test-bench-v2a/guide/_sidebar.md | nav | 0 | 0 | 0 | 0 | 0 |
| catalog-portfolio-api/0.0.1-test-bench-v2a/guide/api-reference/README.md | content | 11 | 1 | 3 | 0 | 0 |
| catalog-portfolio-api/0.0.1-test-bench-v2a/guide/api-reference/brands.md | content | 20 | 1 | 3 | 0 | 0 |
| catalog-portfolio-api/0.0.1-test-bench-v2a/guide/architecture/README.md | content | 13 | 1 | 3 | 0 | 0 |
| catalog-portfolio-api/0.0.1-test-bench-v2a/guide/brand-management/README.md | content | 15 | 1 | 3 | 0 | 0 |
| catalog-portfolio-api/0.0.1-test-bench-v2a/guide/setup/README.md | content | 5 | 1 | 2 | 0 | 0 |
| catalog-portfolio-api/0.0.1-test-bench-v2a/guide/setup/local-development.md | content | 17 | 1 | 3 | 0 | 0 |
| catalog-portfolio-api/0.0.1-test-bench-v2a/guide/troubleshooting/README.md | content | 29 | 1 | 3 | 0 | 0 |
| catalog-portfolio-api/latest/guide/README.md | content | 7 | 1 | 2 | 0 | 0 |
| catalog-portfolio-api/latest/guide/_sidebar.md | nav | 0 | 0 | 0 | 0 | 0 |
| catalog-portfolio-api/latest/guide/api-reference/README.md | content | 11 | 1 | 3 | 0 | 0 |
| catalog-portfolio-api/latest/guide/api-reference/brands.md | content | 20 | 1 | 3 | 0 | 0 |
| catalog-portfolio-api/latest/guide/architecture/README.md | content | 13 | 1 | 3 | 0 | 0 |
| catalog-portfolio-api/latest/guide/brand-management/README.md | content | 15 | 1 | 3 | 0 | 0 |
| catalog-portfolio-api/latest/guide/setup/README.md | content | 5 | 1 | 2 | 0 | 0 |
| catalog-portfolio-api/latest/guide/setup/local-development.md | content | 17 | 1 | 3 | 0 | 0 |
| catalog-portfolio-api/latest/guide/troubleshooting/README.md | content | 29 | 1 | 3 | 0 | 0 |
| demand-forecast-docs/latest/guide/README.md | content | 2 | 1 | 2 | 0 | 0 |
| demand-forecast-docs/latest/guide/_sidebar.md | nav | 0 | 0 | 0 | 0 | 0 |
| demand-forecast-docs/latest/guide/explicabilidad/README.md | content | 1 | 1 | 1 | 0 | 0 |
| demand-forecast-docs/latest/guide/explicabilidad/diarizacion.md | content | 6 | 1 | 3 | 0 | 0 |
| demand-forecast-docs/latest/guide/overview.md | content | 17 | 2 | 4 | 1 | 0 |
| order-workflow-api/5.6.2-hotfix-1/guide/README.md | content | 5 | 2 | 2 | 0 | 0 |
| order-workflow-api/5.6.2-hotfix-1/guide/_sidebar.md | nav | 0 | 0 | 0 | 0 | 0 |
| order-workflow-api/5.6.2-hotfix-1/guide/architecture.md | content | 3 | 1 | 4 | 1 | 0 |
| order-workflow-api/5.6.2-hotfix-1/guide/development.md | content | 6 | 1 | 3 | 1 | 0 |
| order-workflow-api/5.6.2-hotfix-1/guide/services/bigq.md | content | 7 | 1 | 4 | 1 | 0 |
| order-workflow-api/5.6.2-hotfix-1/guide/services/database.md | content | 7 | 1 | 4 | 2 | 0 |
| order-workflow-api/5.6.2-hotfix-1/guide/services/jobs.md | content | 4 | 1 | 4 | 1 | 0 |
| order-workflow-api/5.6.2-hotfix-1/guide/usage.md | content | 2 | 1 | 3 | 1 | 0 |
| order-workflow-api/5.6.2-hotfix-1/guide/use-cases.md | content | 6 | 1 | 4 | 1 | 0 |
| payment-promise-gateway/0.0.10-test-crc-migration/guide/README.md | content | 28 | 1 | 3 | 0 | 0 |
| payment-promise-gateway/latest/guide/README.md | content | 28 | 1 | 3 | 0 | 0 |
| price-engine-api/latest/guide/_coverpage.md | nav | 1 | 1 | 1 | 0 | 0 |
| price-engine-api/latest/guide/_sidebar.md | nav | 0 | 0 | 0 | 0 | 0 |
| price-engine-api/latest/guide/arquitectura.md | content | 3 | 1 | 3 | 0 | 0 |
| price-engine-api/latest/guide/contacto.md | content | 4 | 2 | 3 | 0 | 0 |
| price-engine-api/latest/guide/flujos.md | content | 2 | 1 | 2 | 0 | 0 |
| price-engine-api/latest/guide/general.md | content | 5 | 1 | 3 | 0 | 0 |
| traffic-gate-api/latest/guide/README.md | content | 4 | 1 | 2 | 0 | 0 |
| traffic-gate-api/latest/guide/_sidebar.md | nav | 0 | 0 | 0 | 0 | 0 |
| traffic-gate-api/latest/guide/coverpage.md | nav | 1 | 1 | 1 | 0 | 0 |
| traffic-gate-api/latest/guide/sections/arch.md | content | 4 | 1 | 2 | 0 | 0 |
| traffic-gate-api/latest/guide/sections/database.md | content | 2 | 1 | 2 | 0 | 0 |
| traffic-gate-api/latest/guide/sections/processes.md | content | 4 | 1 | 2 | 0 | 0 |
| traffic-gate-api/latest/guide/sections/waf_config.md | content | 1 | 1 | 1 | 0 | 0 |
| unified-transaction-configs/v0.0.2/guide/README.md | content | 1 | 1 | 1 | 0 | 0 |
| unified-transaction-configs/v0.0.2/guide/_sidebar.md | nav | 0 | 0 | 0 | 0 | 0 |
| unified-transaction-configs/v0.0.2/guide/howto.md | content | 4 | 0 | 2 | 0 | 0 |
| vendor-stockkeeper-api/0.0.10-stock-consumer/guide/_coverpage.md | nav | 1 | 1 | 1 | 0 | 0 |
| vendor-stockkeeper-api/0.0.10-stock-consumer/guide/_sidebar.md | nav | 0 | 0 | 0 | 0 | 0 |
| vendor-stockkeeper-api/0.0.10-stock-consumer/guide/alerts.md | content | 7 | 1 | 3 | 0 | 0 |
| vendor-stockkeeper-api/0.0.10-stock-consumer/guide/api.md | content | 6 | 2 | 3 | 0 | 0 |
| vendor-stockkeeper-api/0.0.10-stock-consumer/guide/database.md | content | 3 | 0 | 3 | 0 | 0 |
| vendor-stockkeeper-api/0.0.10-stock-consumer/guide/important.md | content | 9 | 1 | 3 | 0 | 0 |
| vendor-stockkeeper-api/0.0.10-stock-consumer/guide/introduction.md | content | 2 | 1 | 3 | 1 | 0 |
| vendor-stockkeeper-api/0.0.3-paused-seller/guide/_coverpage.md | nav | 1 | 1 | 1 | 0 | 0 |
| vendor-stockkeeper-api/0.0.3-paused-seller/guide/_sidebar.md | nav | 0 | 0 | 0 | 0 | 0 |
| vendor-stockkeeper-api/0.0.3-paused-seller/guide/alerts.md | content | 7 | 1 | 3 | 0 | 0 |
| vendor-stockkeeper-api/0.0.3-paused-seller/guide/api.md | content | 5 | 2 | 3 | 0 | 0 |
| vendor-stockkeeper-api/0.0.3-paused-seller/guide/database.md | content | 3 | 0 | 3 | 0 | 0 |
| vendor-stockkeeper-api/0.0.3-paused-seller/guide/important.md | content | 9 | 1 | 3 | 0 | 0 |
| vendor-stockkeeper-api/0.0.3-paused-seller/guide/introduction.md | content | 2 | 1 | 3 | 1 | 0 |
| vendor-stockkeeper-api/0.0.6-ep-restock-man/guide/_coverpage.md | nav | 1 | 1 | 1 | 0 | 0 |
| vendor-stockkeeper-api/0.0.6-ep-restock-man/guide/_sidebar.md | nav | 0 | 0 | 0 | 0 | 0 |
| vendor-stockkeeper-api/0.0.6-ep-restock-man/guide/alerts.md | content | 7 | 1 | 3 | 0 | 0 |
| vendor-stockkeeper-api/0.0.6-ep-restock-man/guide/api.md | content | 5 | 2 | 3 | 0 | 0 |
| vendor-stockkeeper-api/0.0.6-ep-restock-man/guide/database.md | content | 3 | 0 | 3 | 0 | 0 |
| vendor-stockkeeper-api/0.0.6-ep-restock-man/guide/important.md | content | 9 | 1 | 3 | 0 | 0 |
| vendor-stockkeeper-api/0.0.6-ep-restock-man/guide/introduction.md | content | 2 | 1 | 3 | 1 | 0 |
| vendor-stockkeeper-api/latest/guide/_coverpage.md | nav | 1 | 1 | 1 | 0 | 0 |
| vendor-stockkeeper-api/latest/guide/_sidebar.md | nav | 0 | 0 | 0 | 0 | 0 |
| vendor-stockkeeper-api/latest/guide/alerts.md | content | 7 | 1 | 3 | 0 | 0 |
| vendor-stockkeeper-api/latest/guide/api.md | content | 5 | 2 | 3 | 0 | 0 |
| vendor-stockkeeper-api/latest/guide/database.md | content | 3 | 0 | 3 | 0 | 0 |
| vendor-stockkeeper-api/latest/guide/important.md | content | 9 | 1 | 3 | 0 | 0 |
| vendor-stockkeeper-api/latest/guide/introduction.md | content | 2 | 1 | 3 | 1 | 0 |
| zenith-keeper/1.1.6/guide/README.md | content | 1 | 1 | 1 | 0 | 1 |
| zenith-keeper/1.1.6/guide/_sidebar.md | nav | 0 | 0 | 0 | 0 | 0 |
| zenith-keeper/1.1.6/guide/use-cases.md | content | 1 | 1 | 1 | 0 | 1 |

**Headers mal formados**

| Archivo | Línea | Texto |
|---|---|---|
| zenith-keeper/1.1.6/guide/README.md | 1 | API FRESH PRODUCTS DOCUMENTATION |
| zenith-keeper/1.1.6/guide/use-cases.md | 1 | Use cases |

<details><summary>Outline completo por archivo</summary>

**2p-revenue-optimizer-api/0.2.2/guide/README.md**

```text
H1 2p-revenue-optimizer-api
H1 Spring Boot App model for Java 17
  H2 Usage
    H3 SCOPE
    H3 Web Server
    H3 Main
    H3 Error Handling
  H2 API Documentation
    H3 VendorFlow Specs Hub
      H4 Usage guide fast reference
  H2 [Release Process](https://release-process.vendorflow-cloud.io/#/)
    H3 Usage
    H3 Questions
```

**2p-revenue-optimizer-api/0.2.2/guide/pages/table_data_dictionary/rule_header.md**

```text
H1 rule_header Table
```

**2p-revenue-optimizer-api/0.2.2/guide/pages/table_data_dictionary/rule_row.md**

```text
H1 rule_row Table
```

**2p-revenue-optimizer-api/latest/guide/README.md**

```text
H1 2p-revenue-optimizer-api
H1 Spring Boot App model for Java 17
  H2 Usage
    H3 SCOPE
    H3 Web Server
    H3 Main
    H3 Error Handling
  H2 API Documentation
    H3 VendorFlow Specs Hub
      H4 Usage guide fast reference
  H2 [Release Process](https://release-process.vendorflow-cloud.io/#/)
    H3 Usage
    H3 Questions
```

**2p-revenue-optimizer-api/latest/guide/pages/table_data_dictionary/rule_custom_field.md**

```text
H1 rule_custom_field Table
```

**2p-revenue-optimizer-api/latest/guide/pages/table_data_dictionary/rule_header.md**

```text
H1 rule_header Table
```

**2p-revenue-optimizer-api/latest/guide/pages/table_data_dictionary/rule_row.md**

```text
H1 rule_row Table
```

**catalog-portfolio-api/0.0.1-test-bench-v2a/guide/README.md**

```text
H1 Catalog Portfolio API Documentation
  H2 🚀 Getting Started
  H2 📚 Documentation Sections
  H2 🛠️ Quick Actions
  H2 🔍 What You'll Find Here
  H2 🛠️ Local Development
  H2 📖 Documentation Features
```

**catalog-portfolio-api/0.0.1-test-bench-v2a/guide/_sidebar.md**

_(sin headers)_

**catalog-portfolio-api/0.0.1-test-bench-v2a/guide/api-reference/README.md**

```text
H1 API Reference
  H2 Authentication
  H2 Quick Reference
    H3 Core Endpoints
    H3 Logo Endpoints
    H3 Collector Endpoints
    H3 Resource Endpoints
  H2 Response Format
  H2 Error Format
  H2 Rate Limiting
  H2 Testing
```

**catalog-portfolio-api/0.0.1-test-bench-v2a/guide/api-reference/brands.md**

```text
H1 Brand Endpoints
  H2 Base URL
  H2 Search Brands
    H3 `GET /`
  H2 Create Brand
    H3 `POST /`
  H2 Get Brand
    H3 `GET /{brandId}`
  H2 Update Brand
    H3 `PUT /{brandId}`
  H2 Delete Brand
    H3 `DELETE /{brandId}`
  H2 Activate Brand
    H3 `PUT /{brandId}/activate`
  H2 Check Brand Activable
    H3 `GET /{brandId}/activable`
  H2 Error Responses
    H3 Common Error Codes
    H3 Error Response Format
  H2 Rate Limiting
```

**catalog-portfolio-api/0.0.1-test-bench-v2a/guide/architecture/README.md**

```text
H1 Architecture Overview
  H2 System Overview
  H2 Architecture Diagram
  H2 Technology Stack
  H2 Key Architectural Principles
    H3 1. Layered Architecture
    H3 2. Separation of Concerns
    H3 3. Scalability
    H3 4. Reliability
  H2 Component Interactions
    H3 Brand Lifecycle Flow
    H3 External Integrations
  H2 Performance Characteristics
```

**catalog-portfolio-api/0.0.1-test-bench-v2a/guide/brand-management/README.md**

```text
H1 Brand Management
  H2 Overview
  H2 Brand Model
  H2 Brand States
    H3 State Descriptions
  H2 Key Business Rules
    H3 Brand Creation Requirements
    H3 Brand Activation Requirements
    H3 Brand Deletion Permissions
  H2 Common Operations
    H3 Creating a Brand
    H3 Updating a Brand
    H3 Activating a Brand
  H2 Validation Rules
  H2 Error Handling
```

**catalog-portfolio-api/0.0.1-test-bench-v2a/guide/setup/README.md**

```text
H1 Setup & Installation
  H2 Overview
  H2 Quick Start
  H2 Prerequisites Summary
  H2 Next Steps
```

**catalog-portfolio-api/0.0.1-test-bench-v2a/guide/setup/local-development.md**

```text
H1 Local Development Setup
  H2 Prerequisites
  H2 Step 1: Clone Repository
  H2 Step 2: Build and Run
    H3 Build the Project
    H3 Run the Service
  H2 Development Workflow
    H3 Code Structure
    H3 Running Tests
    H3 Code Quality Checks
  H2 IDE Configuration
    H3 IntelliJ IDEA
    H3 VS Code
  H2 Troubleshooting
    H3 Common Issues
    H3 Useful Commands
  H2 Next Steps
```

**catalog-portfolio-api/0.0.1-test-bench-v2a/guide/troubleshooting/README.md**

```text
H1 Troubleshooting
  H2 Overview
  H2 Quick Diagnostic
    H3 Health Check
    H3 Database Connection
    H3 Configuration Check
  H2 Common Error Categories
    H3 🔧 Startup Issues
    H3 🌐 API Request Issues
    H3 🗄️ Database Issues
  H2 Error Code Reference
    H3 HTTP Status Codes
    H3 Application Error Codes
  H2 Debug Strategies
    H3 Logging Configuration
    H3 Database Debugging
    H3 API Testing
  H2 Performance Issues
    H3 Slow API Responses
    H3 Memory Issues
  H2 Environment-Specific Issues
    H3 Local Development
    H3 Production Deployment
  H2 Monitoring and Alerts
    H3 Key Metrics to Monitor
  H2 Getting Help
    H3 Log Analysis
    H3 Support Channels
    H3 Escalation Process
```

**catalog-portfolio-api/latest/guide/README.md**

```text
H1 Catalog Portfolio API Documentation
  H2 🚀 Getting Started
  H2 📚 Documentation Sections
  H2 🛠️ Quick Actions
  H2 🔍 What You'll Find Here
  H2 🛠️ Local Development
  H2 📖 Documentation Features
```

**catalog-portfolio-api/latest/guide/_sidebar.md**

_(sin headers)_

**catalog-portfolio-api/latest/guide/api-reference/README.md**

```text
H1 API Reference
  H2 Authentication
  H2 Quick Reference
    H3 Core Endpoints
    H3 Logo Endpoints
    H3 Collector Endpoints
    H3 Resource Endpoints
  H2 Response Format
  H2 Error Format
  H2 Rate Limiting
  H2 Testing
```

**catalog-portfolio-api/latest/guide/api-reference/brands.md**

```text
H1 Brand Endpoints
  H2 Base URL
  H2 Search Brands
    H3 `GET /`
  H2 Create Brand
    H3 `POST /`
  H2 Get Brand
    H3 `GET /{brandId}`
  H2 Update Brand
    H3 `PUT /{brandId}`
  H2 Delete Brand
    H3 `DELETE /{brandId}`
  H2 Activate Brand
    H3 `PUT /{brandId}/activate`
  H2 Check Brand Activable
    H3 `GET /{brandId}/activable`
  H2 Error Responses
    H3 Common Error Codes
    H3 Error Response Format
  H2 Rate Limiting
```

**catalog-portfolio-api/latest/guide/architecture/README.md**

```text
H1 Architecture Overview
  H2 System Overview
  H2 Architecture Diagram
  H2 Technology Stack
  H2 Key Architectural Principles
    H3 1. Layered Architecture
    H3 2. Separation of Concerns
    H3 3. Scalability
    H3 4. Reliability
  H2 Component Interactions
    H3 Brand Lifecycle Flow
    H3 External Integrations
  H2 Performance Characteristics
```

**catalog-portfolio-api/latest/guide/brand-management/README.md**

```text
H1 Brand Management
  H2 Overview
  H2 Brand Model
  H2 Brand States
    H3 State Descriptions
  H2 Key Business Rules
    H3 Brand Creation Requirements
    H3 Brand Activation Requirements
    H3 Brand Deletion Permissions
  H2 Common Operations
    H3 Creating a Brand
    H3 Updating a Brand
    H3 Activating a Brand
  H2 Validation Rules
  H2 Error Handling
```

**catalog-portfolio-api/latest/guide/setup/README.md**

```text
H1 Setup & Installation
  H2 Overview
  H2 Quick Start
  H2 Prerequisites Summary
  H2 Next Steps
```

**catalog-portfolio-api/latest/guide/setup/local-development.md**

```text
H1 Local Development Setup
  H2 Prerequisites
  H2 Step 1: Clone Repository
  H2 Step 2: Build and Run
    H3 Build the Project
    H3 Run the Service
  H2 Development Workflow
    H3 Code Structure
    H3 Running Tests
    H3 Code Quality Checks
  H2 IDE Configuration
    H3 IntelliJ IDEA
    H3 VS Code
  H2 Troubleshooting
    H3 Common Issues
    H3 Useful Commands
  H2 Next Steps
```

**catalog-portfolio-api/latest/guide/troubleshooting/README.md**

```text
H1 Troubleshooting
  H2 Overview
  H2 Quick Diagnostic
    H3 Health Check
    H3 Database Connection
    H3 Configuration Check
  H2 Common Error Categories
    H3 🔧 Startup Issues
    H3 🌐 API Request Issues
    H3 🗄️ Database Issues
  H2 Error Code Reference
    H3 HTTP Status Codes
    H3 Application Error Codes
  H2 Debug Strategies
    H3 Logging Configuration
    H3 Database Debugging
    H3 API Testing
  H2 Performance Issues
    H3 Slow API Responses
    H3 Memory Issues
  H2 Environment-Specific Issues
    H3 Local Development
    H3 Production Deployment
  H2 Monitoring and Alerts
    H3 Key Metrics to Monitor
  H2 Getting Help
    H3 Log Analysis
    H3 Support Channels
    H3 Escalation Process
```

**demand-forecast-docs/latest/guide/README.md**

```text
H1 Welcome to marketplace forecasting technical documentation!
  H2 How to contribute to this documentation
```

**demand-forecast-docs/latest/guide/_sidebar.md**

_(sin headers)_

**demand-forecast-docs/latest/guide/explicabilidad/README.md**

```text
H1 Explicabilidad
```

**demand-forecast-docs/latest/guide/explicabilidad/diarizacion.md**

```text
H1 Diarización
  H2 Notation
  H2 Motivation
  H2 Approach
    H3 Forecast proportions for temporal hierarchies
  H2 Implementation
```

**demand-forecast-docs/latest/guide/overview.md**

```text
H1 Overview
H1 Getting to know our tooling
  H2 **Git**
  H2 Poetry
    H3 Installing current project
    H3 Updating dependencies
    H3 Poetry is awesome
  H2 **Retail Data Framework**
    H3 **Retail Data Application (RDA)**
    H3 Development environments
    H3 Creating tasks
    H3 Creating workflows
  H2 The data pipelines
      H4 A more detailed view of the data pipeline
      H4 Explicabilidad pipeline
    H3 Using the pipelines from notebook
  H2 A deeper dive in how retailpipes is used with Retail Data Framework
```

**order-workflow-api/5.6.2-hotfix-1/guide/README.md**

```text
H1 Getting started
H1 Components
  H2 Database
  H2 BigQ
  H2 Jobs
```

**order-workflow-api/5.6.2-hotfix-1/guide/_sidebar.md**

_(sin headers)_

**order-workflow-api/5.6.2-hotfix-1/guide/architecture.md**

```text
H1 Architecture
      H4 Production
      H4 Test
```

**order-workflow-api/5.6.2-hotfix-1/guide/development.md**

```text
H1 Development
    H3 Requirements
    H3 Clone
    H3 Install
    H3 Testing
    H3 Running
```

**order-workflow-api/5.6.2-hotfix-1/guide/services/bigq.md**

```text
H1 BigQ
  H2 Scopes
      H4 Production
      H4 Test
  H2 Messages
    H3 Validate a pipeline
    H3 Protect branch
```

**order-workflow-api/5.6.2-hotfix-1/guide/services/database.md**

```text
H1 Database
  H2 Scopes
      H4 Production
      H4 Test
  H2 Objects stored
      H4 Workflows
      H4 Cron History
```

**order-workflow-api/5.6.2-hotfix-1/guide/services/jobs.md**

```text
H1 Jobs
  H2 Scopes
      H4 Production
      H4 Test
```

**order-workflow-api/5.6.2-hotfix-1/guide/usage.md**

```text
H1 Usage
    H3 API
```

**order-workflow-api/5.6.2-hotfix-1/guide/use-cases.md**

```text
H1 Use cases
  H2 Workflow
  H2 Pipeline
      H4 Admin
      H4 Branches
      H4 Cron
```

**payment-promise-gateway/0.0.10-test-crc-migration/guide/README.md**

```text
H1 Payment Promise Gateway
  H2 Architecture Overview
  H2 Technical Stack
  H2 Project Structure
  H2 Design Patterns
  H2 Main Features
    H3 Payment Promises
    H3 Late Fee Management
    H3 Offers Management
  H2 API Documentation
  H2 Sequence Diagrams
    H3 1. GET /payment_promise/form
    H3 2. GET /payment_promise/active
    H3 3. GET /offers
    H3 4. POST /payment_promise
    H3 5. POST /forgiveness_proposal
    H3 6. PUT /forgiveness_proposal
    H3 7. GET /forgiveness_proposal/{promiseId}
    H3 Endpoint Summary
  H2 API Examples
  H2 Example Responses
  H2 Running the app
  H2 Setup and Installation
  H2 Testing
  H2 Metrics and Monitoring
  H2 Error Handling
  H2 Contributing
  H2 License
```

**payment-promise-gateway/latest/guide/README.md**

```text
H1 Payment Promise Gateway
  H2 Architecture Overview
  H2 Technical Stack
  H2 Project Structure
  H2 Design Patterns
  H2 Main Features
    H3 Payment Promises
    H3 Late Fee Management
    H3 Offers Management
  H2 API Documentation
  H2 Sequence Diagrams
    H3 1. GET /payment_promise/form
    H3 2. GET /payment_promise/active
    H3 3. GET /offers
    H3 4. POST /payment_promise
    H3 5. POST /forgiveness_proposal
    H3 6. PUT /forgiveness_proposal
    H3 7. GET /forgiveness_proposal/{promiseId}
    H3 Endpoint Summary
  H2 API Examples
  H2 Example Responses
  H2 Running the app
  H2 Setup and Installation
  H2 Testing
  H2 Metrics and Monitoring
  H2 Error Handling
  H2 Contributing
  H2 License
```

**price-engine-api/latest/guide/_coverpage.md**

```text
H1 Price Engine API
```

**price-engine-api/latest/guide/_sidebar.md**

_(sin headers)_

**price-engine-api/latest/guide/arquitectura.md**

```text
H1 Arquitectura
  H2 Diagramas de Flujo
    H3 [Link al diagrama](https://app.diagrams.net/#G2jK5yP8-dqFn3Tp4mLwB9xR6hS2uV0c1#%7B%22pageId%22%3A%22S5pL9mR2-bqNx4Cd7zFv2Hj8kT1uW3e6%22%7D)
```

**price-engine-api/latest/guide/contacto.md**

```text
H1 Contacto
  H2 Equipo
    H3 Commerce Operations & Support
H1 Canales de Comunicación
```

**price-engine-api/latest/guide/flujos.md**

```text
H1 Flujos
  H2 Flujo 1 (endpoint)
```

**price-engine-api/latest/guide/general.md**

```text
H1 General
  H2 Introducción
  H2 Responsabilidades
    H3 Price Engine API es responsable de:
    H3 Price Engine API no se responsabiliza por:
```

**traffic-gate-api/latest/guide/README.md**

```text
H1 Traffic Gate
  H2 Criterios de Whitelist por Scope
  H2 Monitores y Alertas
  H2 Preguntas?
```

**traffic-gate-api/latest/guide/_sidebar.md**

_(sin headers)_

**traffic-gate-api/latest/guide/coverpage.md**

```text
H1 **Traffic Gate**
```

**traffic-gate-api/latest/guide/sections/arch.md**

```text
H1 Arquitectura
  H2 Módulos de la Aplicación
  H2 Jobs
  H2 Diagrama Arquitectura
```

**traffic-gate-api/latest/guide/sections/database.md**

```text
H1 Base de datos
  H2 Diagrama Entidad Relación
```

**traffic-gate-api/latest/guide/sections/processes.md**

```text
H1 Procesos de Whitelist y Purga
  H2 Encolamiento de IPs Bloqueadas por Ratelimit
  H2 Procesamiento de IPs y Whitelist
  H2 Proceso de purga
```

**traffic-gate-api/latest/guide/sections/waf_config.md**

```text
H1 Configuración WAF AWS
```

**unified-transaction-configs/v0.0.2/guide/README.md**

```text
H1 Unified transaction configs
```

**unified-transaction-configs/v0.0.2/guide/_sidebar.md**

_(sin headers)_

**unified-transaction-configs/v0.0.2/guide/howto.md**

```text
  H2 Carga de configuracion
  H2 Carga de grupo de usuarios
  H2 Consideraciones
  H2 Actualizacion de configuraciones en mobile-flow-manager
```

**vendor-stockkeeper-api/0.0.10-stock-consumer/guide/_coverpage.md**

```text
H1 VENDOR STOCKKEEPER API
```

**vendor-stockkeeper-api/0.0.10-stock-consumer/guide/_sidebar.md**

_(sin headers)_

**vendor-stockkeeper-api/0.0.10-stock-consumer/guide/alerts.md**

```text
H1 Alerts
  H2 Alerts
  H2 How to resolve
    H3 [IMPORTANT] Error restock in vendor-stockkeeper-api
    H3 [IMPORTANT] Stockkeeper-api - Error restocking item (negative quantity)
    H3 [LOW PRIORITY] Validation stock (publication has more stock than warehouse&#39;s stock
    H3 Validation stock ERROR updating item
```

**vendor-stockkeeper-api/0.0.10-stock-consumer/guide/api.md**

```text
H1 API
H1 Domain
  H2 Services
    H3 Restock Consumer
    H3 Feed Consumer
    H3 Operation Validation Consumer
```

**vendor-stockkeeper-api/0.0.10-stock-consumer/guide/database.md**

```text
    H3 Test: inventtest
    H3 Stage: inventstg
    H3 Prod: inventprd
```

**vendor-stockkeeper-api/0.0.10-stock-consumer/guide/important.md**

```text
H1 Verification of Items in Inventory Flows
  H2 Introduction
  H2 Inventory Flows
  H2 Importance of Verification
  H2 Verification Procedure
  H2 Conclusion
  H2 How can we do it?
    H3 Restock Flow
    H3 Feed Flow
```

**vendor-stockkeeper-api/0.0.10-stock-consumer/guide/introduction.md**

```text
H1 VENDOR STOCKKEEPER API
    H3 About
```

**vendor-stockkeeper-api/0.0.3-paused-seller/guide/_coverpage.md**

```text
H1 VENDOR STOCKKEEPER API
```

**vendor-stockkeeper-api/0.0.3-paused-seller/guide/_sidebar.md**

_(sin headers)_

**vendor-stockkeeper-api/0.0.3-paused-seller/guide/alerts.md**

```text
H1 Alerts
  H2 Alerts
  H2 How to resolve
    H3 [IMPORTANT] Error restock in vendor-stockkeeper-api
    H3 [IMPORTANT] Stockkeeper-api - Error restocking item (negative quantity)
    H3 [LOW PRIORITY] Validation stock (publication has more stock than warehouse's stock
    H3 Validation stock ERROR updating item
```

**vendor-stockkeeper-api/0.0.3-paused-seller/guide/api.md**

```text
H1 API
H1 Domain
  H2 Services
    H3 Restock Consumer
    H3 Feed Consumer
```

**vendor-stockkeeper-api/0.0.3-paused-seller/guide/database.md**

```text
    H3 Test: inventtest
    H3 Stage: inventstg
    H3 Prod: inventprd
```

**vendor-stockkeeper-api/0.0.3-paused-seller/guide/important.md**

```text
H1 Verification of Items in Inventory Flows
  H2 Introduction
  H2 Inventory Flows
  H2 Importance of Verification
  H2 Verification Procedure
  H2 Conclusion
  H2 How can we do it?
    H3 Restock Flow
    H3 Feed Flow
```

**vendor-stockkeeper-api/0.0.3-paused-seller/guide/introduction.md**

```text
H1 VENDOR STOCKKEEPER API
    H3 About
```

**vendor-stockkeeper-api/0.0.6-ep-restock-man/guide/_coverpage.md**

```text
H1 VENDOR STOCKKEEPER API
```

**vendor-stockkeeper-api/0.0.6-ep-restock-man/guide/_sidebar.md**

_(sin headers)_

**vendor-stockkeeper-api/0.0.6-ep-restock-man/guide/alerts.md**

```text
H1 Alerts
  H2 Alerts
  H2 How to resolve
    H3 Error restock in vendor-stockkeeper-api
    H3 Stockkeeper-api - Error restocking item (negative quantity)
    H3 Validation stock (publication has more stock than warehouse's stock
    H3 Validation stock ERROR updating item
```

**vendor-stockkeeper-api/0.0.6-ep-restock-man/guide/api.md**

```text
H1 API
H1 Domain
  H2 Services
    H3 Restock Consumer
    H3 Feed Consumer
```

**vendor-stockkeeper-api/0.0.6-ep-restock-man/guide/database.md**

```text
    H3 Test: inventtest
    H3 Stage: inventstg
    H3 Prod: inventprd
```

**vendor-stockkeeper-api/0.0.6-ep-restock-man/guide/important.md**

```text
H1 Verification of Items in Inventory Flows
  H2 Introduction
  H2 Inventory Flows
  H2 Importance of Verification
  H2 Verification Procedure
  H2 Conclusion
  H2 How can we do it?
    H3 Restock Flow
    H3 Feed Flow
```

**vendor-stockkeeper-api/0.0.6-ep-restock-man/guide/introduction.md**

```text
H1 VENDOR STOCKKEEPER API
    H3 About
```

**vendor-stockkeeper-api/latest/guide/_coverpage.md**

```text
H1 VENDOR STOCKKEEPER API
```

**vendor-stockkeeper-api/latest/guide/_sidebar.md**

_(sin headers)_

**vendor-stockkeeper-api/latest/guide/alerts.md**

```text
H1 Alerts
  H2 Alerts
  H2 How to resolve
    H3 [IMPORTANT] Error restock in vendor-stockkeeper-api
    H3 [IMPORTANT] Stockkeeper-api - Error restocking item (negative quantity)
    H3 [LOW PRIORITY] Validation stock (publication has more stock than warehouse's stock
    H3 Validation stock ERROR updating item
```

**vendor-stockkeeper-api/latest/guide/api.md**

```text
H1 API
H1 Domain
  H2 Services
    H3 Restock Consumer
    H3 Feed Consumer
```

**vendor-stockkeeper-api/latest/guide/database.md**

```text
    H3 Test: inventtest
    H3 Stage: inventstg
    H3 Prod: inventprd
```

**vendor-stockkeeper-api/latest/guide/important.md**

```text
H1 Verification of Items in Inventory Flows
  H2 Introduction
  H2 Inventory Flows
  H2 Importance of Verification
  H2 Verification Procedure
  H2 Conclusion
  H2 How can we do it?
    H3 Restock Flow
    H3 Feed Flow
```

**vendor-stockkeeper-api/latest/guide/introduction.md**

```text
H1 VENDOR STOCKKEEPER API
    H3 About
```

**zenith-keeper/1.1.6/guide/README.md**

```text
H1 API FRESH PRODUCTS DOCUMENTATION
```

**zenith-keeper/1.1.6/guide/_sidebar.md**

_(sin headers)_

**zenith-keeper/1.1.6/guide/use-cases.md**

```text
H1 Use cases
```

</details>

## 8. Specs y metadatos

| Archivo | Formato | Título | Versión API | Paths | Operaciones |
|---|---|---|---|---|---|
| price-engine-api/latest/specs/swagger.yaml | openapi 3.0.3 | Price Engine API | 0.1.0 | 1 | 1 |
| traffic-gate-api/latest/specs/swagger.yaml | openapi 3.0.1 | traffic-gate-api | 1.7.0 | 8 | 8 |
| zenith-keeper/1.1.6/specs/swagger.yaml | openapi 3.0.1 | fresh-products-api | 0.0.1 | 12 | 14 |

| Archivo | Tipos | URL de origen (guide) |
|---|---|---|
| 2p-revenue-optimizer-api/0.2.2/documentationTypes.json | guide | https://vendorflow-docs.s3.amazonaws.com/2p-revenue-optimizer-api/0.2.2/guide/index.html |
| 2p-revenue-optimizer-api/latest/documentationTypes.json | guide | https://vendorflow-docs.s3.amazonaws.com/2p-revenue-optimizer-api/0.0.3-rc-1/guide/index.html |
| catalog-portfolio-api/0.0.1-test-bench-v2a/documentationTypes.json | guide | https://docstore.s3.amazonaws.com/catalog-portfolio-api/0.0.1-test-bench-v2a/guide/index.html |
| catalog-portfolio-api/latest/documentationTypes.json | guide | https://docstore.s3.amazonaws.com/catalog-portfolio-api/0.0.1-test-bench-v2a/guide/index.html |
| demand-forecast-docs/latest/documentationTypes.json | guide | https://retaildocs.s3.amazonaws.com/demand-forecast-docs/0.1.3/guide/index.html |
| order-workflow-api/5.6.2-hotfix-1/documentationTypes.json | guide | https://retailcorp-docs.s3.amazonaws.com/order-workflow-api/5.6.2-hotfix-1/guide/index.html |
| payment-promise-gateway/0.0.10-test-crc-migration/documentationTypes.json | guide | https://workflowdocs.s3.amazonaws.com/payment-promise-gateway/0.0.10-test-crc-migration/guide/index.html |
| payment-promise-gateway/latest/documentationTypes.json | guide | https://workflowdocs.s3.amazonaws.com/payment-promise-gateway/3.7.0/guide/index.html |
| price-engine-api/latest/documentationTypes.json | guide, specifications | https://commerce-hub-docs.s3.amazonaws.com/price-engine-api/0.0.2-setting-up/guide/index.html |
| traffic-gate-api/latest/documentationTypes.json | guide, specifications | https://retailhubdocs.s3.amazonaws.com/traffic-gate-api/1.65.0/guide/index.html |
| unified-transaction-configs/v0.0.2/documentationTypes.json | guide | https://globalpaydocs.s3.amazonaws.com/unified-transaction-configs/v0.0.2/guide/index.html |
| vendor-stockkeeper-api/0.0.10-stock-consumer/documentationTypes.json | guide | https://techzone-docs.s3.amazonaws.com/vendor-stockkeeper-api/0.0.10-stock-consumer/guide/index.html |
| vendor-stockkeeper-api/0.0.3-paused-seller/documentationTypes.json | guide | https://techzone-docs.s3.amazonaws.com/vendor-stockkeeper-api/0.0.3-paused-seller/guide/index.html |
| vendor-stockkeeper-api/0.0.6-ep-restock-man/documentationTypes.json | guide | https://techzone-docs.s3.amazonaws.com/vendor-stockkeeper-api/0.0.6-ep-restock-man/guide/index.html |
| vendor-stockkeeper-api/latest/documentationTypes.json | guide | https://techzone-docs.s3.amazonaws.com/vendor-stockkeeper-api/0.41.0/guide/index.html |
| zenith-keeper/1.1.6/documentationTypes.json | guide, specifications | https://nimbuslib-docs.s3.amazonaws.com/zenith-keeper/1.1.6/guide/index.html |

## Notas metodológicas

- **Tipo**: `nav` = archivos de navegación docsify; `meta` = documentationTypes.json; `spec` = YAML/JSON de API; `content` = el resto del Markdown.
- **Palabras útiles**: tras quitar bloques de código, inline code, comentarios HTML, imágenes/badges, URLs, tags HTML, headers y marcadores TO DO.
- **Estados**: `empty` = sin texto tras limpiar; `todo_only` = solo marcadores TO DO; `stub` = menos de 15 palabras útiles (`stub_max_words`). Es un diagnóstico de prosa: el filtro real del corpus está en la etapa `normalize` (ver `reports/dedup.md`), que también cuenta código y tablas.
- **Duplicados**: aquí solo exactos. Los casi duplicados (MinHash/shingles) se tratan en la etapa `dedup`.
- El inventario completo está en `inventory.jsonl` dentro de `processed_dir`.
