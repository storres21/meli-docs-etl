# Revisión de pares casi-duplicados

Cada par compara dos secciones del corpus normalizado (A y B). Completá la columna `label`
de `near_dup_labels.csv` con el `pair_id` correspondiente:

- `same`: es la misma sección en otra versión/edición (debería agruparse).
- `diff`: son secciones distintas aunque compartan plantilla.
- `unsure`: no estoy segura.

La columna `nota` es libre. Cómo leer el diff: las líneas sin prefijo están en A y en B,
las que empiezan con `-` solo en A y las que empiezan con `+` solo en B. Así cada texto se
lee completo una sola vez. Los pares están en orden aleatorio.

Pares: 64.

---

### 1 · np-7677c1e8

- **A**: catalog-portfolio-api › 0.0.1-test-bench-v2a/guide/api-reference/brands.md › Brand Endpoints › Get Brand › `GET /{brandId}`
- **B**: catalog-portfolio-api › 0.0.1-test-bench-v2a/guide/api-reference/brands.md › Brand Endpoints › Activate Brand › `PUT /{brandId}/activate`

````diff
-### `GET /{brandId}`
+### `PUT /{brandId}/activate`
 
 **Path Parameters:**
 
 | Parameter | Type | Required | Description |
 | --- | --- | --- | --- |
 | `brandId` | integer | Yes | Brand ID |
 
 **Example Request:**
 
 ```bash
-curl "https://api.mp.internal.retailflow.com/catalog/brands/123"
+curl -X PUT "https://api.mp.internal.retailflow.com/catalog/brands/123/activate"
 ```
 
 **Example Response:**
 
 ```json
 {
   "id": 123,
   "name": "Example Brand",
-  "soft_descriptor": "EXAMPLE",
-  "site": "MLA",
-  "category": 5611201,
-  "subcategories": [],
-  "type": "lighthouse",
-  "tags": [],
-  "logos": [
-    {
-      "id": 456,
-      "brand_id": 123,
-      "type": "main",
-      "picture_id": "ML123456789"
-    }
-  ],
-  "resources": [],
-  "priority": 5,
-  "status": "STAND_BY",
-  "date_created": "2024-01-15T10:30:00.000-03:00",
-  "date_last_updated": "2024-01-15T10:30:00.000-03:00"
+  "status": "ACTIVE",
+  "date_last_updated": "2024-01-15T11:00:00.000-03:00"
 }
 ```
````

---

### 2 · np-877c03fa

- **A**: 2p-revenue-optimizer-api › 0.2.2/guide/pages/table_data_dictionary/rule_row.md › rule_row Table
- **B**: 2p-revenue-optimizer-api › latest/guide/pages/table_data_dictionary/rule_header.md › rule_header Table

```diff
-# rule_row Table
+# rule_header Table
 
-The `rule_row` table stores , receiving data from PME.
+The `rule_header` table stores , receiving data from PME.
 
 The table has the following columns:
 
 | Field | Type | Constraints | Description | Extra |
 | --- | --- | --- | --- | --- |
 | id | bigint | Not null | Auto-increment primary key |  |
-| rule_id | bigint | Not null | Foreign | REFERENCES rule_header(id) |
-| site_id | json | Null | Sites Ids |  |
-| seller_id | json | Null | Sellers Ids |  |
-| domain | json | Null | Domains |  |
-| brand | json | Null | Brands |  |
-| item | json | Null | Items |  |
-| custom_fields | json | Null | Custom Fields |  |
+| type | varchar(180) | Not null |  |  |
+| date | timestamp | Not null | Date timestamp when was created | DEFAULT_GENERATED |
+| username | varchar(180) | Not null | Username who created rule |  |
+| name | varchar(180) | Not null | Name of rule |  |
+| description | varchar(180) | Not null | Description |  |
+| productive | boolean | Not null | Is productive |  |
+| version | int | Not null | Version |  |
```

---

### 3 · np-1ee14afd

- **A**: payment-promise-gateway › 0.0.10-test-crc-migration/guide/README.md › Payment Promise Gateway › Sequence Diagrams › 5. POST /forgiveness_proposal
- **B**: payment-promise-gateway › 0.0.10-test-crc-migration/guide/README.md › Payment Promise Gateway › Sequence Diagrams › 6. PUT /forgiveness_proposal

````diff
-### 5. POST /forgiveness_proposal
+### 6. PUT /forgiveness_proposal
 
-**Description**: Creates a late fee forgiveness proposal. Allows initiating the process of forgiving late payment interest.
+**Description**: Confirms an existing late fee forgiveness proposal. Finalizes the forgiveness process previously initiated.
 
 ```mermaid
 sequenceDiagram
     actor User
     participant Controller as PaymentPromiseController
     participant Service as PaymentPromiseService
     participant PromiseService as PromiseService
 
-    User->>Controller: POST /forgiveness_proposal
-    Note over User,Controller: Body: LateFeeForgivenessPromiseCommand
+    User->>Controller: PUT /forgiveness_proposal
+    Note over User,Controller: Body: LateFeeForgivenessProposalCommand
     Controller->>Controller: validateRequestBody(command)
-    Controller->>Service: createLateFeeForgivenessProposal(command)
-    Service->>PromiseService: createLateFeeForgivenessProposal(command)
-    PromiseService-->>Service: LateFeeForgivenessProposalDTO
-    Service-->>Controller: Proposal details
-    Controller-->>User: Proposal creation result (JSON)
+    Controller->>Service: confirmLateFeeForgivenessProposal(command)
+    Service->>PromiseService: confirmProposal(borrowerId, proposalId)
+    PromiseService-->>Service: LateFeeForgivenessConfirmDTO
+    Service-->>Controller: Confirmation result
+    Controller-->>User: Confirmation status (JSON)
 ```
````

---

### 4 · np-7020b29a

- **A**: catalog-portfolio-api › 0.0.1-test-bench-v2a/guide/api-reference/brands.md › Brand Endpoints › Get Brand › `GET /{brandId}`
- **B**: catalog-portfolio-api › 0.0.1-test-bench-v2a/guide/api-reference/brands.md › Brand Endpoints › Delete Brand › `DELETE /{brandId}`

````diff
-### `GET /{brandId}`
+### `DELETE /{brandId}`
 
 **Path Parameters:**
 
 | Parameter | Type | Required | Description |
 | --- | --- | --- | --- |
 | `brandId` | integer | Yes | Brand ID |
 
+**Headers:**
+
+| Header | Type | Required | Description |
+| --- | --- | --- | --- |
+| `X-Client-Id` | string | Yes | Client ID (must be whitelisted) |
+
 **Example Request:**
 
 ```bash
-curl "https://api.mp.internal.retailflow.com/catalog/brands/123"
+curl -X DELETE "https://api.mp.internal.retailflow.com/catalog/brands/123" \
+  -H "X-Client-Id: your-client-id"
 ```
 
 **Example Response:**
 
 ```json
 {
-  "id": 123,
-  "name": "Example Brand",
-  "soft_descriptor": "EXAMPLE",
-  "site": "MLA",
-  "category": 5611201,
-  "subcategories": [],
-  "type": "lighthouse",
-  "tags": [],
-  "logos": [
-    {
-      "id": 456,
-      "brand_id": 123,
-      "type": "main",
-      "picture_id": "ML123456789"
-    }
-  ],
-  "resources": [],
-  "priority": 5,
-  "status": "STAND_BY",
-  "date_created": "2024-01-15T10:30:00.000-03:00",
-  "date_last_updated": "2024-01-15T10:30:00.000-03:00"
+  "message": "Brand deleted successfully",
+  "status": 200
 }
 ```
````

---

### 5 · np-ca925fab

- **A**: catalog-portfolio-api › 0.0.1-test-bench-v2a/guide/api-reference/brands.md › Brand Endpoints › Delete Brand › `DELETE /{brandId}`
- **B**: catalog-portfolio-api › 0.0.1-test-bench-v2a/guide/api-reference/brands.md › Brand Endpoints › Check Brand Activable › `GET /{brandId}/activable`

````diff
-### `DELETE /{brandId}`
+### `GET /{brandId}/activable`
 
 **Path Parameters:**
 
 | Parameter | Type | Required | Description |
 | --- | --- | --- | --- |
 | `brandId` | integer | Yes | Brand ID |
 
-**Headers:**
-
-| Header | Type | Required | Description |
-| --- | --- | --- | --- |
-| `X-Client-Id` | string | Yes | Client ID (must be whitelisted) |
-
 **Example Request:**
 
 ```bash
-curl -X DELETE "https://api.mp.internal.retailflow.com/catalog/brands/123" \
-  -H "X-Client-Id: your-client-id"
+curl "https://api.mp.internal.retailflow.com/catalog/brands/123/activable"
 ```
 
 **Example Response:**
 
 ```json
 {
-  "message": "Brand deleted successfully",
-  "status": 200
+  "valid": false,
+  "validationDetails": [
+    "Main logo is missing",
+    "Category validation failed"
+  ]
 }
 ```
````

---

### 6 · np-9b35eb83

- **A**: catalog-portfolio-api › 0.0.1-test-bench-v2a/guide/api-reference/brands.md › Brand Endpoints › Delete Brand › `DELETE /{brandId}`
- **B**: catalog-portfolio-api › 0.0.1-test-bench-v2a/guide/api-reference/brands.md › Brand Endpoints › Activate Brand › `PUT /{brandId}/activate`

````diff
-### `DELETE /{brandId}`
+### `PUT /{brandId}/activate`
 
 **Path Parameters:**
 
 | Parameter | Type | Required | Description |
 | --- | --- | --- | --- |
 | `brandId` | integer | Yes | Brand ID |
 
-**Headers:**
-
-| Header | Type | Required | Description |
-| --- | --- | --- | --- |
-| `X-Client-Id` | string | Yes | Client ID (must be whitelisted) |
-
 **Example Request:**
 
 ```bash
-curl -X DELETE "https://api.mp.internal.retailflow.com/catalog/brands/123" \
-  -H "X-Client-Id: your-client-id"
+curl -X PUT "https://api.mp.internal.retailflow.com/catalog/brands/123/activate"
 ```
 
 **Example Response:**
 
 ```json
 {
-  "message": "Brand deleted successfully",
-  "status": 200
+  "id": 123,
+  "name": "Example Brand",
+  "status": "ACTIVE",
+  "date_last_updated": "2024-01-15T11:00:00.000-03:00"
 }
 ```
````

---

### 7 · np-696ecdb7

- **A**: vendor-stockkeeper-api › 0.0.10-stock-consumer/guide/alerts.md › Alerts › How to resolve › Validation stock ERROR updating item
- **B**: vendor-stockkeeper-api › 0.0.6-ep-restock-man/guide/alerts.md › Alerts › How to resolve › Error restock in vendor-stockkeeper-api

```diff
-### Validation stock ERROR updating item
+### Error restock in vendor-stockkeeper-api
 
-This alert happens when something goes wrong while trying to update the quantity of stock into the publication
+This alert happens when something goes wrong while trying to restock
+This error can be generated by any really rare case that has not been controlled in the code, so it is important to check the logs to identify the problem.
 
 To resolve this alert, you need to do the following:
-1. Identify in the **vendor-stockkeeper-api** logs the item whose status could not be updated and determine why it could not be done (e.g., due to a status that does not allow updating the item such as under\_review, deleted...).
-2. If the item has available units and the status allows sales without stock (any status other than deleted), a ticket should be raised in Shield to request the publication be blocked to prevent potential out-of-stock sales.
+1. Identify in the **vendor-stockkeeper-api** logs which item could not be restocked correctly and determine the reason for this.
+2. Resolve the issue.
+3. It may be necessary to perform a manual restock via the database or, in the most extreme case, release a new version.
```

---

### 8 · np-ed330ede

- **A**: vendor-stockkeeper-api › 0.0.10-stock-consumer/guide/alerts.md › Alerts › How to resolve › [IMPORTANT] Error restock in vendor-stockkeeper-api
- **B**: vendor-stockkeeper-api › 0.0.6-ep-restock-man/guide/alerts.md › Alerts › How to resolve › Error restock in vendor-stockkeeper-api

```diff
-### [IMPORTANT] Error restock in vendor-stockkeeper-api
+### Error restock in vendor-stockkeeper-api
 
 This alert happens when something goes wrong while trying to restock
 This error can be generated by any really rare case that has not been controlled in the code, so it is important to check the logs to identify the problem.
 
 To resolve this alert, you need to do the following:
 1. Identify in the **vendor-stockkeeper-api** logs which item could not be restocked correctly and determine the reason for this.
 2. Resolve the issue.
 3. It may be necessary to perform a manual restock via the database or, in the most extreme case, release a new version.
```

---

### 9 · np-cb4f4f56

- **A**: vendor-stockkeeper-api › 0.0.10-stock-consumer/guide/alerts.md › Alerts › Alerts
- **B**: vendor-stockkeeper-api › 0.0.10-stock-consumer/guide/alerts.md › Alerts › How to resolve › Validation stock ERROR updating item

```diff
-## Alerts
+### Validation stock ERROR updating item
 
-| Alert | Description | url |
-| --- | --- | --- |
-| Error restock in vendor-stockkeeper-api | This alert happens when something goes wrong while trying to restock | [Link](https://app.datadoghq.com/monitors/116772629) |
-| Stockkeeper-api - Error restocking item (negative quantity) | This alert happens when something goes wrong while trying to restock publications and this publication has negative quantity | [Link](https://app.datadoghq.com/monitors/150073893) |
-| Validation stock (publication has more stock than warehouse's stock | This alert happens when something goes wrong while trying to sell a publication without stocK into 3PL facilities | [Link](https://app.datadoghq.com/monitors/158654468) |
-| Validation stock ERROR updating item | This alert happens when something goes wrong while trying to update the quantity of stock into the publication | [Link](https://app.datadoghq.com/monitors/160761475) |
+This alert happens when something goes wrong while trying to update the quantity of stock into the publication
+
+To resolve this alert, you need to do the following:
+1. Identify in the **vendor-stockkeeper-api** logs the item whose status could not be updated and determine why it could not be done (e.g., due to a status that does not allow updating the item such as under\_review, deleted...).
+2. If the item has available units and the status allows sales without stock (any status other than deleted), a ticket should be raised in Shield to request the publication be blocked to prevent potential out-of-stock sales.
```

---

### 10 · np-27fbc195

- **A**: vendor-stockkeeper-api › 0.0.10-stock-consumer/guide/alerts.md › Alerts › Alerts
- **B**: vendor-stockkeeper-api › 0.0.6-ep-restock-man/guide/alerts.md › Alerts › How to resolve › Validation stock (publication has more stock than warehouse's stock

```diff
-## Alerts
+### Validation stock (publication has more stock than warehouse's stock
 
-| Alert | Description | url |
-| --- | --- | --- |
-| Error restock in vendor-stockkeeper-api | This alert happens when something goes wrong while trying to restock | [Link](https://app.datadoghq.com/monitors/116772629) |
-| Stockkeeper-api - Error restocking item (negative quantity) | This alert happens when something goes wrong while trying to restock publications and this publication has negative quantity | [Link](https://app.datadoghq.com/monitors/150073893) |
-| Validation stock (publication has more stock than warehouse's stock | This alert happens when something goes wrong while trying to sell a publication without stocK into 3PL facilities | [Link](https://app.datadoghq.com/monitors/158654468) |
-| Validation stock ERROR updating item | This alert happens when something goes wrong while trying to update the quantity of stock into the publication | [Link](https://app.datadoghq.com/monitors/160761475) |
+This alert happens when something goes wrong while trying to sell a publication without stocK into 3PL facilities
+
+To resolve this alert, you need to do the following:
+1. You should review the **vendor-stockkeeper-api** logs with the **stream-prod** scope to easily identify the item and SKU associated with the potential out-of-stock sale.
+2. You should confirm that the item was correctly paused by **checking the item's status**. If the item was not correctly paused, you should raise a ticket in Shield to request the publication be blocked to prevent potential out-of-stock sales.
+3. Additionally, you should identify the item to monitor it in case of future out-of-stock sales.
```

---

### 11 · np-c3b993a0

- **A**: vendor-stockkeeper-api › 0.0.10-stock-consumer/guide/alerts.md › Alerts › How to resolve › [IMPORTANT] Error restock in vendor-stockkeeper-api
- **B**: vendor-stockkeeper-api › 0.0.10-stock-consumer/guide/alerts.md › Alerts › How to resolve › [IMPORTANT] Stockkeeper-api - Error restocking item (negative quantity)

```diff
-### [IMPORTANT] Error restock in vendor-stockkeeper-api
+### [IMPORTANT] Stockkeeper-api - Error restocking item (negative quantity)
 
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
```

---

### 12 · np-56c010cf

- **A**: vendor-stockkeeper-api › 0.0.10-stock-consumer/guide/api.md › Domain › Services › Restock Consumer
- **B**: vendor-stockkeeper-api › 0.0.10-stock-consumer/guide/api.md › Domain › Services › Feed Consumer

````diff
-### Restock Consumer
+### Feed Consumer
 
 ```bash
-curl --location 'https://vendor-stockkeeper-test.techzoneoffice.com/fp/inventory/operations/restock-new' \
+curl --location 'https://vendor-stockkeeper-test.techzoneoffice.com/fp/inventory/operations/feed' \
 --header 'Content-Type: application/json' \
 --data '{
-    "msg": {
-        "inbound_shipment_id": "900000734"
+
+    "msg" : {
+        "id": 389
     }
 }'
 ```
+
 `200 OK`
````

---

### 13 · np-c6dc48a7

- **A**: catalog-portfolio-api › 0.0.1-test-bench-v2a/guide/api-reference/brands.md › Brand Endpoints › Update Brand › `PUT /{brandId}`
- **B**: catalog-portfolio-api › 0.0.1-test-bench-v2a/guide/api-reference/brands.md › Brand Endpoints › Check Brand Activable › `GET /{brandId}/activable`

````diff
-### `PUT /{brandId}`
+### `GET /{brandId}/activable`
 
 **Path Parameters:**
 
 | Parameter | Type | Required | Description |
 | --- | --- | --- | --- |
 | `brandId` | integer | Yes | Brand ID |
 
-**Request Body:**
+**Example Request:**
+
+```bash
+curl "https://api.mp.internal.retailflow.com/catalog/brands/123/activable"
+```
+
+**Example Response:**
 
 ```json
 {
-  "name": "Updated Brand Name",
-  "soft_descriptor": "UPDATED",
-  "category": 5611201,
-  "subcategories": [789],
-  "tags": ["new_tag"],
-  "priority": 8,
-  "business_description": "Updated description"
+  "valid": false,
+  "validationDetails": [
+    "Main logo is missing",
+    "Category validation failed"
+  ]
 }
 ```
-
-**Example Request:**
-
-```bash
-curl -X PUT "https://api.mp.internal.retailflow.com/catalog/brands/123" \
-  -H "Content-Type: application/json" \
-  -d '{
-    "name": "Updated Brand Name",
-    "priority": 8
-  }'
-```
````

---

### 14 · np-97635b5a

- **A**: payment-promise-gateway › 0.0.10-test-crc-migration/guide/README.md › Payment Promise Gateway › Sequence Diagrams › 5. POST /forgiveness_proposal
- **B**: payment-promise-gateway › 0.0.10-test-crc-migration/guide/README.md › Payment Promise Gateway › Sequence Diagrams › 7. GET /forgiveness_proposal/{promiseId}

````diff
-### 5. POST /forgiveness_proposal
+### 7. GET /forgiveness_proposal/{promiseId}
 
-**Description**: Creates a late fee forgiveness proposal. Allows initiating the process of forgiving late payment interest.
+**Description**: Retrieves the details of a specific late fee forgiveness. Allows querying the status and details of an existing forgiveness.
 
 ```mermaid
 sequenceDiagram
     actor User
     participant Controller as PaymentPromiseController
     participant Service as PaymentPromiseService
     participant PromiseService as PromiseService
 
-    User->>Controller: POST /forgiveness_proposal
-    Note over User,Controller: Body: LateFeeForgivenessPromiseCommand
-    Controller->>Controller: validateRequestBody(command)
-    Controller->>Service: createLateFeeForgivenessProposal(command)
-    Service->>PromiseService: createLateFeeForgivenessProposal(command)
-    PromiseService-->>Service: LateFeeForgivenessProposalDTO
-    Service-->>Controller: Proposal details
-    Controller-->>User: Proposal creation result (JSON)
+    User->>Controller: GET /forgiveness_proposal/{promiseId}
+    Note over User,Controller: Path param: promiseId (numeric)
+    Controller->>Controller: Validate promiseId format
+    Controller->>Service: getLateFeeForgiveness(promiseId)
+    Service->>PromiseService: getPaymentPromiseById(promiseId)
+    PromiseService-->>Service: PaymentPromiseDTO
+    Service->>Service: Extract lateFeeForgiveness
+    Service-->>Controller: LateFeeForgivenessDTO
+    Controller-->>User: Forgiveness details (JSON)
 ```
````

---

### 15 · np-46e4894a

- **A**: payment-promise-gateway › 0.0.10-test-crc-migration/guide/README.md › Payment Promise Gateway › Sequence Diagrams › 2. GET /payment_promise/active
- **B**: payment-promise-gateway › 0.0.10-test-crc-migration/guide/README.md › Payment Promise Gateway › Sequence Diagrams › 7. GET /forgiveness_proposal/{promiseId}

````diff
-### 2. GET /payment_promise/active
+### 7. GET /forgiveness_proposal/{promiseId}
 
-**Description**: Retrieves the user's active payment promise. Returns the promise details if an active one exists.
+**Description**: Retrieves the details of a specific late fee forgiveness. Allows querying the status and details of an existing forgiveness.
 
 ```mermaid
 sequenceDiagram
     actor User
     participant Controller as PaymentPromiseController
     participant Service as PaymentPromiseService
     participant PromiseService as PromiseService
 
-    User->>Controller: GET /payment_promise/active
-    Note over User,Controller: Headers: x-caller-id
-    Controller->>Controller: Extract userId from request
-    Controller->>Service: getActivePromise(userId)
-    Service->>PromiseService: getUserDebt(userId)
-    PromiseService-->>Service: UserDebtDTO
-    Service->>PromiseService: getUserPromises(userId)
-    PromiseService-->>Service: UserPromiseDTO
-    Service-->>Controller: ActivePromiseBO
-    Controller-->>User: Active promise details (JSON)
+    User->>Controller: GET /forgiveness_proposal/{promiseId}
+    Note over User,Controller: Path param: promiseId (numeric)
+    Controller->>Controller: Validate promiseId format
+    Controller->>Service: getLateFeeForgiveness(promiseId)
+    Service->>PromiseService: getPaymentPromiseById(promiseId)
+    PromiseService-->>Service: PaymentPromiseDTO
+    Service->>Service: Extract lateFeeForgiveness
+    Service-->>Controller: LateFeeForgivenessDTO
+    Controller-->>User: Forgiveness details (JSON)
 ```
````

---

### 16 · np-6a6560a3

- **A**: vendor-stockkeeper-api › 0.0.10-stock-consumer/guide/alerts.md › Alerts › How to resolve › [IMPORTANT] Stockkeeper-api - Error restocking item (negative quantity)
- **B**: vendor-stockkeeper-api › 0.0.6-ep-restock-man/guide/alerts.md › Alerts › How to resolve › Stockkeeper-api - Error restocking item (negative quantity)

```diff
-### [IMPORTANT] Stockkeeper-api - Error restocking item (negative quantity)
+### Stockkeeper-api - Error restocking item (negative quantity)
 
 This alert happens when something goes wrong while trying to restock publications and this publication has negative quantity
 This case does not have a specific process defined as it is a very rare case that has not been controlled in the code, so it is important to check the logs to identify the problem.
 
 To resolve this alert, you need to do the following:
 1. Identify in the **vendor-stockkeeper-api** logs which item is associated with the negative restock attempt.
 2. Notify to **Envio Pack** that the restock could not be completed correctly.
 3. Proceed to identify what happened (why a restock is executed that leaves the available quantities below 0).
 4. Resolve the issue.
 5. It may be necessary to perform a manual restock via the database or, in the most extreme case, release a new version.
```

---

### 17 · np-a696f64a

- **A**: vendor-stockkeeper-api › 0.0.6-ep-restock-man/guide/alerts.md › Alerts › How to resolve › Error restock in vendor-stockkeeper-api
- **B**: vendor-stockkeeper-api › 0.0.6-ep-restock-man/guide/alerts.md › Alerts › How to resolve › Stockkeeper-api - Error restocking item (negative quantity)

```diff
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
```

---

### 18 · np-c448d07f

- **A**: payment-promise-gateway › 0.0.10-test-crc-migration/guide/README.md › Payment Promise Gateway › Sequence Diagrams › 3. GET /offers
- **B**: payment-promise-gateway › 0.0.10-test-crc-migration/guide/README.md › Payment Promise Gateway › Sequence Diagrams › 5. POST /forgiveness_proposal

````diff
-### 3. GET /offers
+### 5. POST /forgiveness_proposal
 
-**Description**: Retrieves the offers or remedies available to the user. Shows the different options the user has to regularize their debt.
+**Description**: Creates a late fee forgiveness proposal. Allows initiating the process of forgiving late payment interest.
 
 ```mermaid
 sequenceDiagram
     actor User
     participant Controller as PaymentPromiseController
     participant Service as PaymentPromiseService
     participant PromiseService as PromiseService
 
-    User->>Controller: GET /offers
-    Note over User,Controller: Parameters: caller.id, site_id, vertical
-    Controller->>Controller: Extract userId from request
-    Controller->>Controller: Extract siteId from request
-    Controller->>Controller: Extract userType from request
-    Controller->>Service: getOffer(userId, siteId, userType)
-    Service->>PromiseService: getConditions(userId)
-    PromiseService-->>Service: ConditionDTO
-    Service-->>Controller: UserOfferBO
-    Controller-->>User: Available offers (JSON)
+    User->>Controller: POST /forgiveness_proposal
+    Note over User,Controller: Body: LateFeeForgivenessPromiseCommand
+    Controller->>Controller: validateRequestBody(command)
+    Controller->>Service: createLateFeeForgivenessProposal(command)
+    Service->>PromiseService: createLateFeeForgivenessProposal(command)
+    PromiseService-->>Service: LateFeeForgivenessProposalDTO
+    Service-->>Controller: Proposal details
+    Controller-->>User: Proposal creation result (JSON)
 ```
````

---

### 19 · np-95ff3bfd

- **A**: 2p-revenue-optimizer-api › latest/guide/pages/table_data_dictionary/rule_header.md › rule_header Table
- **B**: 2p-revenue-optimizer-api › latest/guide/pages/table_data_dictionary/rule_row.md › rule_row Table

```diff
-# rule_header Table
+# rule_row Table
 
-The `rule_header` table stores , receiving data from PME.
+The `rule_row` table stores , receiving data from PME.
 
 The table has the following columns:
 
 | Field | Type | Constraints | Description | Extra |
 | --- | --- | --- | --- | --- |
 | id | bigint | Not null | Auto-increment primary key |  |
-| type | varchar(180) | Not null |  |  |
-| date | timestamp | Not null | Date timestamp when was created | DEFAULT_GENERATED |
-| username | varchar(180) | Not null | Username who created rule |  |
-| name | varchar(180) | Not null | Name of rule |  |
-| description | varchar(180) | Not null | Description |  |
-| productive | boolean | Not null | Is productive |  |
-| version | int | Not null | Version |  |
+| rule_id | bigint | Not null | Foreign | REFERENCES rule_header(id) |
+| site_id | json | Null | Sites Ids |  |
+| seller_id | json | Null | Sellers Ids |  |
+| domain | json | Null | Domains |  |
+| brand | json | Null | Brands |  |
+| item | json | Null | Items |  |
```

---

### 20 · np-69ba0eb8

- **A**: vendor-stockkeeper-api › 0.0.10-stock-consumer/guide/alerts.md › Alerts › How to resolve › [IMPORTANT] Stockkeeper-api - Error restocking item (negative quantity)
- **B**: vendor-stockkeeper-api › 0.0.6-ep-restock-man/guide/alerts.md › Alerts › How to resolve › Error restock in vendor-stockkeeper-api

```diff
-### [IMPORTANT] Stockkeeper-api - Error restocking item (negative quantity)
+### Error restock in vendor-stockkeeper-api
 
-This alert happens when something goes wrong while trying to restock publications and this publication has negative quantity
-This case does not have a specific process defined as it is a very rare case that has not been controlled in the code, so it is important to check the logs to identify the problem.
+This alert happens when something goes wrong while trying to restock
+This error can be generated by any really rare case that has not been controlled in the code, so it is important to check the logs to identify the problem.
 
 To resolve this alert, you need to do the following:
-1. Identify in the **vendor-stockkeeper-api** logs which item is associated with the negative restock attempt.
-2. Notify to **Envio Pack** that the restock could not be completed correctly.
-3. Proceed to identify what happened (why a restock is executed that leaves the available quantities below 0).
-4. Resolve the issue.
-5. It may be necessary to perform a manual restock via the database or, in the most extreme case, release a new version.
+1. Identify in the **vendor-stockkeeper-api** logs which item could not be restocked correctly and determine the reason for this.
+2. Resolve the issue.
+3. It may be necessary to perform a manual restock via the database or, in the most extreme case, release a new version.
```

---

### 21 · np-34601e62

- **A**: payment-promise-gateway › 0.0.10-test-crc-migration/guide/README.md › Payment Promise Gateway › Sequence Diagrams › 6. PUT /forgiveness_proposal
- **B**: payment-promise-gateway › 0.0.10-test-crc-migration/guide/README.md › Payment Promise Gateway › Sequence Diagrams › 7. GET /forgiveness_proposal/{promiseId}

````diff
-### 6. PUT /forgiveness_proposal
+### 7. GET /forgiveness_proposal/{promiseId}
 
-**Description**: Confirms an existing late fee forgiveness proposal. Finalizes the forgiveness process previously initiated.
+**Description**: Retrieves the details of a specific late fee forgiveness. Allows querying the status and details of an existing forgiveness.
 
 ```mermaid
 sequenceDiagram
     actor User
     participant Controller as PaymentPromiseController
     participant Service as PaymentPromiseService
     participant PromiseService as PromiseService
 
-    User->>Controller: PUT /forgiveness_proposal
-    Note over User,Controller: Body: LateFeeForgivenessProposalCommand
-    Controller->>Controller: validateRequestBody(command)
-    Controller->>Service: confirmLateFeeForgivenessProposal(command)
-    Service->>PromiseService: confirmProposal(borrowerId, proposalId)
-    PromiseService-->>Service: LateFeeForgivenessConfirmDTO
-    Service-->>Controller: Confirmation result
-    Controller-->>User: Confirmation status (JSON)
+    User->>Controller: GET /forgiveness_proposal/{promiseId}
+    Note over User,Controller: Path param: promiseId (numeric)
+    Controller->>Controller: Validate promiseId format
+    Controller->>Service: getLateFeeForgiveness(promiseId)
+    Service->>PromiseService: getPaymentPromiseById(promiseId)
+    PromiseService-->>Service: PaymentPromiseDTO
+    Service->>Service: Extract lateFeeForgiveness
+    Service-->>Controller: LateFeeForgivenessDTO
+    Controller-->>User: Forgiveness details (JSON)
 ```
````

---

### 22 · np-d71e1977

- **A**: 2p-revenue-optimizer-api › 0.2.2/guide/pages/table_data_dictionary/rule_header.md › rule_header Table
- **B**: 2p-revenue-optimizer-api › latest/guide/pages/table_data_dictionary/rule_row.md › rule_row Table

```diff
-# rule_header Table
+# rule_row Table
 
-The `rule_header` table stores , receiving data from PME.
+The `rule_row` table stores , receiving data from PME.
 
 The table has the following columns:
 
 | Field | Type | Constraints | Description | Extra |
 | --- | --- | --- | --- | --- |
 | id | bigint | Not null | Auto-increment primary key |  |
-| type | varchar(180) | Not null |  |  |
-| created_date | timestamp | Not null | Date timestamp when was created | DEFAULT_GENERATED |
-| username | varchar(180) | Not null | Username who created rule |  |
-| name | varchar(180) | Not null | Name of rule |  |
-| description | varchar(180) | Not null | Description |  |
-| productive | boolean | Not null | Is productive |  |
-| productive_date | timestamp | null | productive date |  |
+| rule_id | bigint | Not null | Foreign | REFERENCES rule_header(id) |
+| site_id | json | Null | Sites Ids |  |
+| seller_id | json | Null | Sellers Ids |  |
+| domain | json | Null | Domains |  |
+| brand | json | Null | Brands |  |
+| item | json | Null | Items |  |
```

---

### 23 · np-af2cfebe

- **A**: vendor-stockkeeper-api › 0.0.10-stock-consumer/guide/alerts.md › Alerts › How to resolve › [LOW PRIORITY] Validation stock (publication has more stock than warehouse's stock
- **B**: vendor-stockkeeper-api › 0.0.6-ep-restock-man/guide/alerts.md › Alerts › How to resolve › Validation stock (publication has more stock than warehouse's stock

```diff
-### [LOW PRIORITY] Validation stock (publication has more stock than warehouse's stock
+### Validation stock (publication has more stock than warehouse's stock
 
-This alert is to verify that item was correctly paused.
-It happens when something goes wrong while trying to sell a publication without stock into 3PL facilities
+This alert happens when something goes wrong while trying to sell a publication without stocK into 3PL facilities
 
 To resolve this alert, you need to do the following:
 1. You should review the **vendor-stockkeeper-api** logs with the **stream-prod** scope to easily identify the item and SKU associated with the potential out-of-stock sale.
-2. You should confirm that the item was correctly paused by **checking the item's status**. You need to use api core item endpoint with item_id and check "status" If the item was not correctly paused, you should raise a ticket in Shield to request the publication be blocked to prevent potential out-of-stock sales.
+2. You should confirm that the item was correctly paused by **checking the item's status**. If the item was not correctly paused, you should raise a ticket in Shield to request the publication be blocked to prevent potential out-of-stock sales.
 3. Additionally, you should identify the item to monitor it in case of future out-of-stock sales.
-
-PS: This alert is just to check item was correctly paused, it may be works automatically
```

---

### 24 · np-cee20420

- **A**: payment-promise-gateway › 0.0.10-test-crc-migration/guide/README.md › Payment Promise Gateway › Sequence Diagrams › 4. POST /payment_promise
- **B**: payment-promise-gateway › 0.0.10-test-crc-migration/guide/README.md › Payment Promise Gateway › Sequence Diagrams › 7. GET /forgiveness_proposal/{promiseId}

````diff
-### 4. POST /payment_promise
+### 7. GET /forgiveness_proposal/{promiseId}
 
-**Description**: Creates a new payment promise. Allows the user to establish a payment commitment with a specific date and method.
+**Description**: Retrieves the details of a specific late fee forgiveness. Allows querying the status and details of an existing forgiveness.
 
 ```mermaid
 sequenceDiagram
     actor User
     participant Controller as PaymentPromiseController
     participant Service as PaymentPromiseService
     participant PromiseService as PromiseService
 
-    User->>Controller: POST /payment_promise
-    Note over User,Controller: Body: PromiseCommand
-    Controller->>Controller: validateRequestBody(promiseCommand)
-    Controller->>Service: createPromise(promiseCommand)
-    Service->>Service: Calculate dateCreated
-    Service->>PromiseService: createPaymentPromise(paymentPromiseCommand)
+    User->>Controller: GET /forgiveness_proposal/{promiseId}
+    Note over User,Controller: Path param: promiseId (numeric)
+    Controller->>Controller: Validate promiseId format
+    Controller->>Service: getLateFeeForgiveness(promiseId)
+    Service->>PromiseService: getPaymentPromiseById(promiseId)
     PromiseService-->>Service: PaymentPromiseDTO
-    Service-->>Controller: ActivePromiseBO
-    Controller-->>User: Promise creation result (JSON)
+    Service->>Service: Extract lateFeeForgiveness
+    Service-->>Controller: LateFeeForgivenessDTO
+    Controller-->>User: Forgiveness details (JSON)
 ```
````

---

### 25 · np-10ca9884

- **A**: catalog-portfolio-api › 0.0.1-test-bench-v2a/guide/brand-management/README.md › Brand Management › Common Operations › Creating a Brand
- **B**: catalog-portfolio-api › 0.0.1-test-bench-v2a/guide/brand-management/README.md › Brand Management › Common Operations › Updating a Brand

````diff
-### Creating a Brand
+### Updating a Brand
 
 ```bash
-curl -X POST "https://api.mp.internal.retailflow.com/catalog/brands" \
+curl -X PUT "https://api.mp.internal.retailflow.com/catalog/brands/123" \
   -H "Content-Type: application/json" \
   -d '{
-    "name": "Example Brand",
-    "site": "MLA",
-    "category": 5611201,
-    "type": "lighthouse"
+    "name": "Updated Brand Name",
+    "priority": 10
   }'
 ```
````

---

### 26 · np-9698e081

- **A**: payment-promise-gateway › 0.0.10-test-crc-migration/guide/README.md › Payment Promise Gateway › Sequence Diagrams › 2. GET /payment_promise/active
- **B**: payment-promise-gateway › 0.0.10-test-crc-migration/guide/README.md › Payment Promise Gateway › Sequence Diagrams › 6. PUT /forgiveness_proposal

````diff
-### 2. GET /payment_promise/active
+### 6. PUT /forgiveness_proposal
 
-**Description**: Retrieves the user's active payment promise. Returns the promise details if an active one exists.
+**Description**: Confirms an existing late fee forgiveness proposal. Finalizes the forgiveness process previously initiated.
 
 ```mermaid
 sequenceDiagram
     actor User
     participant Controller as PaymentPromiseController
     participant Service as PaymentPromiseService
     participant PromiseService as PromiseService
 
-    User->>Controller: GET /payment_promise/active
-    Note over User,Controller: Headers: x-caller-id
-    Controller->>Controller: Extract userId from request
-    Controller->>Service: getActivePromise(userId)
-    Service->>PromiseService: getUserDebt(userId)
-    PromiseService-->>Service: UserDebtDTO
-    Service->>PromiseService: getUserPromises(userId)
-    PromiseService-->>Service: UserPromiseDTO
-    Service-->>Controller: ActivePromiseBO
-    Controller-->>User: Active promise details (JSON)
+    User->>Controller: PUT /forgiveness_proposal
+    Note over User,Controller: Body: LateFeeForgivenessProposalCommand
+    Controller->>Controller: validateRequestBody(command)
+    Controller->>Service: confirmLateFeeForgivenessProposal(command)
+    Service->>PromiseService: confirmProposal(borrowerId, proposalId)
+    PromiseService-->>Service: LateFeeForgivenessConfirmDTO
+    Service-->>Controller: Confirmation result
+    Controller-->>User: Confirmation status (JSON)
 ```
````

---

### 27 · np-85266a10

- **A**: catalog-portfolio-api › 0.0.1-test-bench-v2a/guide/api-reference/brands.md › Brand Endpoints › Create Brand › `POST /`
- **B**: catalog-portfolio-api › 0.0.1-test-bench-v2a/guide/api-reference/brands.md › Brand Endpoints › Get Brand › `GET /{brandId}`

````diff
-### `POST /`
+### `GET /{brandId}`
 
-**Request Body:**
+**Path Parameters:**
 
-```json
-{
-  "name": "Example Brand",
-  "soft_descriptor": "EXAMPLE",
-  "site": "MLA",
-  "category": 5611201,
-  "subcategories": [123, 456],
-  "type": "lighthouse",
-  "tags": ["tag1", "tag2"],
-  "priority": 5,
-  "business_description": "Business description text"
-}
-```
-
-**Required Fields:**
-- `name`: Brand name (must be unique within site)
-- `site`: RetailFlow site code
-- `category`: Primary category ID
-- `type`: Brand type (lighthouse or standard)
+| Parameter | Type | Required | Description |
+| --- | --- | --- | --- |
+| `brandId` | integer | Yes | Brand ID |
 
 **Example Request:**
 
 ```bash
-curl -X POST "https://api.mp.internal.retailflow.com/catalog/brands/" \
-  -H "Content-Type: application/json" \
-  -d '{
-    "name": "Example Brand",
-    "site": "MLA",
-    "category": 5611201,
-    "type": "lighthouse"
-  }'
+curl "https://api.mp.internal.retailflow.com/catalog/brands/123"
 ```
 
 **Example Response:**
 
 ```json
 {
   "id": 123,
   "name": "Example Brand",
+  "soft_descriptor": "EXAMPLE",
   "site": "MLA",
   "category": 5611201,
+  "subcategories": [],
   "type": "lighthouse",
+  "tags": [],
+  "logos": [
+    {
+      "id": 456,
+      "brand_id": 123,
+      "type": "main",
+      "picture_id": "ML123456789"
+    }
+  ],
+  "resources": [],
+  "priority": 5,
   "status": "STAND_BY",
   "date_created": "2024-01-15T10:30:00.000-03:00",
   "date_last_updated": "2024-01-15T10:30:00.000-03:00"
 }
 ```
````

---

### 28 · np-dd7f0697

- **A**: catalog-portfolio-api › 0.0.1-test-bench-v2a/guide/api-reference/brands.md › Brand Endpoints › Activate Brand › `PUT /{brandId}/activate`
- **B**: catalog-portfolio-api › 0.0.1-test-bench-v2a/guide/api-reference/brands.md › Brand Endpoints › Check Brand Activable › `GET /{brandId}/activable`

````diff
-### `PUT /{brandId}/activate`
+### `GET /{brandId}/activable`
 
 **Path Parameters:**
 
 | Parameter | Type | Required | Description |
 | --- | --- | --- | --- |
 | `brandId` | integer | Yes | Brand ID |
 
 **Example Request:**
 
 ```bash
-curl -X PUT "https://api.mp.internal.retailflow.com/catalog/brands/123/activate"
+curl "https://api.mp.internal.retailflow.com/catalog/brands/123/activable"
 ```
 
 **Example Response:**
 
 ```json
 {
-  "id": 123,
-  "name": "Example Brand",
-  "status": "ACTIVE",
-  "date_last_updated": "2024-01-15T11:00:00.000-03:00"
+  "valid": false,
+  "validationDetails": [
+    "Main logo is missing",
+    "Category validation failed"
+  ]
 }
 ```
````

---

### 29 · np-11aa22ad

- **A**: payment-promise-gateway › 0.0.10-test-crc-migration/guide/README.md › Payment Promise Gateway › Sequence Diagrams › 4. POST /payment_promise
- **B**: payment-promise-gateway › 0.0.10-test-crc-migration/guide/README.md › Payment Promise Gateway › Sequence Diagrams › 5. POST /forgiveness_proposal

````diff
-### 4. POST /payment_promise
+### 5. POST /forgiveness_proposal
 
-**Description**: Creates a new payment promise. Allows the user to establish a payment commitment with a specific date and method.
+**Description**: Creates a late fee forgiveness proposal. Allows initiating the process of forgiving late payment interest.
 
 ```mermaid
 sequenceDiagram
     actor User
     participant Controller as PaymentPromiseController
     participant Service as PaymentPromiseService
     participant PromiseService as PromiseService
 
-    User->>Controller: POST /payment_promise
-    Note over User,Controller: Body: PromiseCommand
-    Controller->>Controller: validateRequestBody(promiseCommand)
-    Controller->>Service: createPromise(promiseCommand)
-    Service->>Service: Calculate dateCreated
-    Service->>PromiseService: createPaymentPromise(paymentPromiseCommand)
-    PromiseService-->>Service: PaymentPromiseDTO
-    Service-->>Controller: ActivePromiseBO
-    Controller-->>User: Promise creation result (JSON)
+    User->>Controller: POST /forgiveness_proposal
+    Note over User,Controller: Body: LateFeeForgivenessPromiseCommand
+    Controller->>Controller: validateRequestBody(command)
+    Controller->>Service: createLateFeeForgivenessProposal(command)
+    Service->>PromiseService: createLateFeeForgivenessProposal(command)
+    PromiseService-->>Service: LateFeeForgivenessProposalDTO
+    Service-->>Controller: Proposal details
+    Controller-->>User: Proposal creation result (JSON)
 ```
````

---

### 30 · np-e30cbc93

- **A**: payment-promise-gateway › 0.0.10-test-crc-migration/guide/README.md › Payment Promise Gateway › Main Features › Offers Management
- **B**: payment-promise-gateway › 0.0.10-test-crc-migration/guide/README.md › Payment Promise Gateway › Sequence Diagrams › 3. GET /offers

````diff
-### Offers Management
+### 3. GET /offers
 
-- Retrieves the offers or remedies available to the user. Shows the different options the user has to regularize their debt.
+**Description**: Retrieves the offers or remedies available to the user. Shows the different options the user has to regularize their debt.
+
+```mermaid
+sequenceDiagram
+    actor User
+    participant Controller as PaymentPromiseController
+    participant Service as PaymentPromiseService
+    participant PromiseService as PromiseService
+
+    User->>Controller: GET /offers
+    Note over User,Controller: Parameters: caller.id, site_id, vertical
+    Controller->>Controller: Extract userId from request
+    Controller->>Controller: Extract siteId from request
+    Controller->>Controller: Extract userType from request
+    Controller->>Service: getOffer(userId, siteId, userType)
+    Service->>PromiseService: getConditions(userId)
+    PromiseService-->>Service: ConditionDTO
+    Service-->>Controller: UserOfferBO
+    Controller-->>User: Available offers (JSON)
+```
````

---

### 31 · np-dd0cc7f1

- **A**: traffic-gate-api › latest/guide/README.md › Traffic Gate › Criterios de Whitelist por Scope
- **B**: traffic-gate-api › latest/guide/sections/arch.md › Arquitectura › Jobs

```diff
-## Criterios de Whitelist por Scope
+## Jobs
+
+RetailHub provee un servicio de [Jobs](https://retailhubdocs.io/docs/3.3.5/guide/#/lang-es/services/jobs/jobs) que se personalizan mediante una expresión de cron, para que realicen el llamado periódico de servicios web expuestos por nuestras aplicaciones, para la ejecución de algún proceso. Estos llamados se hacen mediante solicitudes HTTP tipo POST únicamente y no está soportado el envío de un body en la solicitud, por lo que cualquier información o parámetro que se requiera entregar al servicio web, debe ser enviado por medio de query params.
 
 Las reglas de ratelimit que limitan el tráfico hacia RetailHub según la región, tienen asociado un scope. El scope es un parámetro que determina el tipo de aplicaciones que están siendo protegidas por un conjunto de reglas de ratelimit, es decir, si son aplicaciones tipo GUI o frontend, APIs o apps de retailhubpay. Se tienen 4 posibles valores para el scope: front, api, pci, pci_global. Los dos últimos valores están relacionados a RetailHub Pay.
 
-Traffic Gate se encarga de evaluar cada cierto tiempo, si las direcciones IP afectadas por ratelimit cumplen algún criterio que determine que alguna de ellas se deba enviar a whitelist o no. Para ello, traffic gate enriquece la metadata de la IP, con información consultada desde las Knowledge APIs del ecosistema de Anomaly (isBot, isRetailHub, isCloud, users-analysis, users-behind, mobile-applications-behind).
+Traffic Gate expone dos servicios web que se requieren ejecutar de manera periódica:
 
-<details><summary><strong> SCOPE FRONT</strong></summary>
+- **POST /whitelist?scope=x** Este servicio consulta las direcciones IPs bloqueadas por reglas de ratelimit asociadas al scope x, y las envía a una cola de mensajes para su posterior análisis
 
-Una dirección IP bloqueada por un ratelimit aplicado al scope front, se debe enviar a whitelist si cumple alguno de los siguientes criterios:
+- **POST /whitelist/purge?scope=x** Este servicio consulta las direcciones IPs que han sido agregadas a una whitelist para el scope x, y evalúa seguir autorizando el tráfico a tales IPs o eliminarlas de la whitelist
 
-- La dirección IP tuvo más de un usuario detrás en la última hora
-- La dirección IP tiene asociado un BigSeller
-- La dirección IP tiene asociado un CBT.
-- La dirección IP pertenece a infraestructura RetailHub.
-- La dirección IP pertenece a un bot bueno.
-
-</details>
-
-<details><summary><strong>SCOPE API</strong></summary>
-
-Una dirección IP bloqueada por un ratelimit aplicado al scope api, se debe enviar a whitelist si cumple alguno de los siguientes criterios:
-- La dirección IP tuvo más de un usuario detrás en la última hora
-- Si el usuario detrás de la dirección IP es un usuario considerado confiable por User Reputation
-- La dirección IP tiene asociado un BigSeller
-- La dirección IP tiene asociado un CBT.
-- La dirección IP pertenece a infraestructura RetailHub.
-- La dirección IP tiene una aplicación certificada o privada detrás
-- La dirección IP pertenece a un bot bueno.
-</details>
-
-<details><summary><strong>SCOPE PCI</strong></summary>
-
-Una dirección IP bloqueada por un ratelimit aplicado al scope pci, se debe enviar a whitelist si cumple alguno de los siguientes criterios:
-- La dirección IP tuvo más de un usuario detrás en la última hora
-- Si el usuario detrás de la dirección IP es un usuario considerado confiable por User Reputation
-- La dirección IP tiene asociado un BigSeller
-- La dirección IP tiene asociado un CBT.
-- La dirección IP pertenece a infraestructura RetailHub.
-- La dirección IP tiene una aplicación certificada o privada detrás
-- La dirección IP pertenece a un bot bueno.
-</details>
-
-<details><summary><strong>SCOPE PCI GLOBAL</strong></summary>
-
-Una dirección IP bloqueada por un ratelimit aplicado al scope pci-global, se debe enviar a whitelist si cumple alguno de los siguientes criterios:
-- La dirección IP tuvo más de un usuario detrás en la última hora
-- Si el usuario detrás de la dirección IP es un usuario considerado confiable por User Reputation
-- La dirección IP tiene asociado un BigSeller
-s- La dirección IP pertenece a infraestructura RetailHub.
-- La dirección IP tiene una aplicación certificada o privada detrás
-- La dirección IP pertenece a un bot bueno.
-</details>
+Teniendo en cuenta que Traffic Gate requiere la ejecución periódica de los anteriores servicios web (uno para enviar a whitelist, otro para purgar) por cada uno de los scopes, esta aplicación tiene configurados en RetailHub 8 jobs, dos por cada uno de los 4 scopes (front, api, pci y pci_global).
+Todos los 4 jobs que llaman el proceso de whitelist, se ejecutan cada minuto. Por su parte, los 4 jobs que llaman el proceso de purga de las whitelist, se ejecutan cada hora. En conclusión, para todos los scopes, cada minuto se está evaluando qué IPs bloqueadas se deben agregar a whitelist, y cada hora se evalúa cuales IPs en whitelist, ya pueden ser removidas.
```

---

### 32 · np-d2a111ef

- **A**: vendor-stockkeeper-api › 0.0.10-stock-consumer/guide/alerts.md › Alerts › How to resolve › [IMPORTANT] Error restock in vendor-stockkeeper-api
- **B**: vendor-stockkeeper-api › 0.0.10-stock-consumer/guide/alerts.md › Alerts › How to resolve › Validation stock ERROR updating item

```diff
-### [IMPORTANT] Error restock in vendor-stockkeeper-api
+### Validation stock ERROR updating item
 
-This alert happens when something goes wrong while trying to restock
-This error can be generated by any really rare case that has not been controlled in the code, so it is important to check the logs to identify the problem.
+This alert happens when something goes wrong while trying to update the quantity of stock into the publication
 
 To resolve this alert, you need to do the following:
-1. Identify in the **vendor-stockkeeper-api** logs which item could not be restocked correctly and determine the reason for this.
-2. Resolve the issue.
-3. It may be necessary to perform a manual restock via the database or, in the most extreme case, release a new version.
+1. Identify in the **vendor-stockkeeper-api** logs the item whose status could not be updated and determine why it could not be done (e.g., due to a status that does not allow updating the item such as under\_review, deleted...).
+2. If the item has available units and the status allows sales without stock (any status other than deleted), a ticket should be raised in Shield to request the publication be blocked to prevent potential out-of-stock sales.
```

---

### 33 · np-302b27dc

- **A**: vendor-stockkeeper-api › 0.0.10-stock-consumer/guide/api.md › Domain › Services
- **B**: vendor-stockkeeper-api › 0.0.3-paused-seller/guide/api.md › Domain › Services

```diff
 ## Services
 
 | METHOD | OPERATION | PATH |
 | --- | --- | --- |
 | POST | [Feed Consumer](#vendor-branch-search) | `/fp/inventory/operations/feed` |
 | POST | [Restock Consumer](#get-branches-by-vendor-id) | `/fp/inventory/operations/restock-new` |
 | GET | [Get Detail](#Get-Detail) | `/fp/inventory/item/detail/{identifierRegister}` |
 | GET | [Internal Item Detail](#internal-item-detail) | `/internal/stock-operations/3pl/{identifierRegister}` |
 | GET | [Get Detail Doma](#item-detail) | `/stock-operations/3pl/{identifierRegister}` |
-| GET | [Operation Validation Consumer](#) | `/stock-operations/3pl/validation/restock-consumer` |
```

---

### 34 · np-014b39dd

- **A**: catalog-portfolio-api › 0.0.1-test-bench-v2a/guide/api-reference/brands.md › Brand Endpoints › Get Brand › `GET /{brandId}`
- **B**: catalog-portfolio-api › 0.0.1-test-bench-v2a/guide/api-reference/brands.md › Brand Endpoints › Check Brand Activable › `GET /{brandId}/activable`

````diff
-### `GET /{brandId}`
+### `GET /{brandId}/activable`
 
 **Path Parameters:**
 
 | Parameter | Type | Required | Description |
 | --- | --- | --- | --- |
 | `brandId` | integer | Yes | Brand ID |
 
 **Example Request:**
 
 ```bash
-curl "https://api.mp.internal.retailflow.com/catalog/brands/123"
+curl "https://api.mp.internal.retailflow.com/catalog/brands/123/activable"
 ```
 
 **Example Response:**
 
 ```json
 {
-  "id": 123,
-  "name": "Example Brand",
-  "soft_descriptor": "EXAMPLE",
-  "site": "MLA",
-  "category": 5611201,
-  "subcategories": [],
-  "type": "lighthouse",
-  "tags": [],
-  "logos": [
-    {
-      "id": 456,
-      "brand_id": 123,
-      "type": "main",
-      "picture_id": "ML123456789"
-    }
-  ],
-  "resources": [],
-  "priority": 5,
-  "status": "STAND_BY",
-  "date_created": "2024-01-15T10:30:00.000-03:00",
-  "date_last_updated": "2024-01-15T10:30:00.000-03:00"
+  "valid": false,
+  "validationDetails": [
+    "Main logo is missing",
+    "Category validation failed"
+  ]
 }
 ```
````

---

### 35 · np-f2a4bef0

- **A**: catalog-portfolio-api › 0.0.1-test-bench-v2a/guide/api-reference/brands.md › Brand Endpoints › Update Brand › `PUT /{brandId}`
- **B**: catalog-portfolio-api › 0.0.1-test-bench-v2a/guide/api-reference/brands.md › Brand Endpoints › Delete Brand › `DELETE /{brandId}`

````diff
-### `PUT /{brandId}`
+### `DELETE /{brandId}`
 
 **Path Parameters:**
 
 | Parameter | Type | Required | Description |
 | --- | --- | --- | --- |
 | `brandId` | integer | Yes | Brand ID |
 
-**Request Body:**
+**Headers:**
 
-```json
-{
-  "name": "Updated Brand Name",
-  "soft_descriptor": "UPDATED",
-  "category": 5611201,
-  "subcategories": [789],
-  "tags": ["new_tag"],
-  "priority": 8,
-  "business_description": "Updated description"
-}
-```
+| Header | Type | Required | Description |
+| --- | --- | --- | --- |
+| `X-Client-Id` | string | Yes | Client ID (must be whitelisted) |
 
 **Example Request:**
 
 ```bash
-curl -X PUT "https://api.mp.internal.retailflow.com/catalog/brands/123" \
-  -H "Content-Type: application/json" \
-  -d '{
-    "name": "Updated Brand Name",
-    "priority": 8
-  }'
+curl -X DELETE "https://api.mp.internal.retailflow.com/catalog/brands/123" \
+  -H "X-Client-Id: your-client-id"
 ```
+
+**Example Response:**
+
+```json
+{
+  "message": "Brand deleted successfully",
+  "status": 200
+}
+```
````

---

### 36 · np-912a7255

- **A**: 2p-revenue-optimizer-api › 0.2.2/guide/pages/table_data_dictionary/rule_row.md › rule_row Table
- **B**: 2p-revenue-optimizer-api › latest/guide/pages/table_data_dictionary/rule_custom_field.md › rule_custom_field Table

```diff
-# rule_row Table
+# rule_custom_field Table
 
-The `rule_row` table stores , receiving data from PME.
+The `rule_custom_field` table stores , receiving data from PME.
 
 The table has the following columns:
 
 | Field | Type | Constraints | Description | Extra |
 | --- | --- | --- | --- | --- |
 | id | bigint | Not null | Auto-increment primary key |  |
-| rule_id | bigint | Not null | Foreign | REFERENCES rule_header(id) |
-| site_id | json | Null | Sites Ids |  |
-| seller_id | json | Null | Sellers Ids |  |
-| domain | json | Null | Domains |  |
-| brand | json | Null | Brands |  |
-| item | json | Null | Items |  |
-| custom_fields | json | Null | Custom Fields |  |
+| rule_row_id | bigint | Not null | Foreign | REFERENCES rule_row(id) |
+| name | varchar(180) | Not null | Name |  |
+| value_info | varchar(180) | Not null | Values |  |
```

---

### 37 · np-ca00c092

- **A**: payment-promise-gateway › 0.0.10-test-crc-migration/guide/README.md › Payment Promise Gateway › Sequence Diagrams › 1. GET /payment_promise/form
- **B**: payment-promise-gateway › 0.0.10-test-crc-migration/guide/README.md › Payment Promise Gateway › Sequence Diagrams › 5. POST /forgiveness_proposal

````diff
-### 1. GET /payment_promise/form
+### 5. POST /forgiveness_proposal
 
-**Description**: Retrieves the form options for payment promises. This endpoint allows querying available payment methods and permitted amounts.
+**Description**: Creates a late fee forgiveness proposal. Allows initiating the process of forgiving late payment interest.
 
 ```mermaid
 sequenceDiagram
     actor User
     participant Controller as PaymentPromiseController
     participant Service as PaymentPromiseService
     participant PromiseService as PromiseService
 
-    User->>Controller: GET /payment_promise/form
-    Note over User,Controller: Parameters: caller.id, site_id
-    Controller->>Controller: Extract userId from request
-    Controller->>Controller: Extract siteId from request
-    Controller->>Service: getPromiseForm(userId, siteId)
-    Service->>PromiseService: getUserDebt(userId)
-    PromiseService-->>Service: UserDebtDTO
-    Service->>PromiseService: getPaymentMethods()
-    PromiseService-->>Service: PaymentMethodSearchDTO
-    Service-->>Controller: PaymentPromiseFormBO
-    Controller-->>User: Form options (JSON)
+    User->>Controller: POST /forgiveness_proposal
+    Note over User,Controller: Body: LateFeeForgivenessPromiseCommand
+    Controller->>Controller: validateRequestBody(command)
+    Controller->>Service: createLateFeeForgivenessProposal(command)
+    Service->>PromiseService: createLateFeeForgivenessProposal(command)
+    PromiseService-->>Service: LateFeeForgivenessProposalDTO
+    Service-->>Controller: Proposal details
+    Controller-->>User: Proposal creation result (JSON)
 ```
````

---

### 38 · np-877f85c0

- **A**: catalog-portfolio-api › 0.0.1-test-bench-v2a/guide/api-reference/brands.md › Brand Endpoints › Activate Brand › `PUT /{brandId}/activate`
- **B**: catalog-portfolio-api › 0.0.1-test-bench-v2a/guide/brand-management/README.md › Brand Management › Common Operations › Updating a Brand

````diff
-### `PUT /{brandId}/activate`
-
-**Path Parameters:**
-
-| Parameter | Type | Required | Description |
-| --- | --- | --- | --- |
-| `brandId` | integer | Yes | Brand ID |
-
-**Example Request:**
+### Updating a Brand
 
 ```bash
-curl -X PUT "https://api.mp.internal.retailflow.com/catalog/brands/123/activate"
+curl -X PUT "https://api.mp.internal.retailflow.com/catalog/brands/123" \
+  -H "Content-Type: application/json" \
+  -d '{
+    "name": "Updated Brand Name",
+    "priority": 10
+  }'
 ```
-
-**Example Response:**
-
-```json
-{
-  "id": 123,
-  "name": "Example Brand",
-  "status": "ACTIVE",
-  "date_last_updated": "2024-01-15T11:00:00.000-03:00"
-}
-```
````

---

### 39 · np-da487f76

- **A**: payment-promise-gateway › 0.0.10-test-crc-migration/guide/README.md › Payment Promise Gateway › Sequence Diagrams › 3. GET /offers
- **B**: payment-promise-gateway › 0.0.10-test-crc-migration/guide/README.md › Payment Promise Gateway › Sequence Diagrams › 6. PUT /forgiveness_proposal

````diff
-### 3. GET /offers
+### 6. PUT /forgiveness_proposal
 
-**Description**: Retrieves the offers or remedies available to the user. Shows the different options the user has to regularize their debt.
+**Description**: Confirms an existing late fee forgiveness proposal. Finalizes the forgiveness process previously initiated.
 
 ```mermaid
 sequenceDiagram
     actor User
     participant Controller as PaymentPromiseController
     participant Service as PaymentPromiseService
     participant PromiseService as PromiseService
 
-    User->>Controller: GET /offers
-    Note over User,Controller: Parameters: caller.id, site_id, vertical
-    Controller->>Controller: Extract userId from request
-    Controller->>Controller: Extract siteId from request
-    Controller->>Controller: Extract userType from request
-    Controller->>Service: getOffer(userId, siteId, userType)
-    Service->>PromiseService: getConditions(userId)
-    PromiseService-->>Service: ConditionDTO
-    Service-->>Controller: UserOfferBO
-    Controller-->>User: Available offers (JSON)
+    User->>Controller: PUT /forgiveness_proposal
+    Note over User,Controller: Body: LateFeeForgivenessProposalCommand
+    Controller->>Controller: validateRequestBody(command)
+    Controller->>Service: confirmLateFeeForgivenessProposal(command)
+    Service->>PromiseService: confirmProposal(borrowerId, proposalId)
+    PromiseService-->>Service: LateFeeForgivenessConfirmDTO
+    Service-->>Controller: Confirmation result
+    Controller-->>User: Confirmation status (JSON)
 ```
````

---

### 40 · np-3db81f4d

- **A**: catalog-portfolio-api › 0.0.1-test-bench-v2a/guide/api-reference/brands.md › Brand Endpoints › Get Brand › `GET /{brandId}`
- **B**: catalog-portfolio-api › 0.0.1-test-bench-v2a/guide/api-reference/brands.md › Brand Endpoints › Update Brand › `PUT /{brandId}`

````diff
-### `GET /{brandId}`
+### `PUT /{brandId}`
 
 **Path Parameters:**
 
 | Parameter | Type | Required | Description |
 | --- | --- | --- | --- |
 | `brandId` | integer | Yes | Brand ID |
 
+**Request Body:**
+
+```json
+{
+  "name": "Updated Brand Name",
+  "soft_descriptor": "UPDATED",
+  "category": 5611201,
+  "subcategories": [789],
+  "tags": ["new_tag"],
+  "priority": 8,
+  "business_description": "Updated description"
+}
+```
+
 **Example Request:**
 
 ```bash
-curl "https://api.mp.internal.retailflow.com/catalog/brands/123"
+curl -X PUT "https://api.mp.internal.retailflow.com/catalog/brands/123" \
+  -H "Content-Type: application/json" \
+  -d '{
+    "name": "Updated Brand Name",
+    "priority": 8
+  }'
 ```
-
-**Example Response:**
-
-```json
-{
-  "id": 123,
-  "name": "Example Brand",
-  "soft_descriptor": "EXAMPLE",
-  "site": "MLA",
-  "category": 5611201,
-  "subcategories": [],
-  "type": "lighthouse",
-  "tags": [],
-  "logos": [
-    {
-      "id": 456,
-      "brand_id": 123,
-      "type": "main",
-      "picture_id": "ML123456789"
-    }
-  ],
-  "resources": [],
-  "priority": 5,
-  "status": "STAND_BY",
-  "date_created": "2024-01-15T10:30:00.000-03:00",
-  "date_last_updated": "2024-01-15T10:30:00.000-03:00"
-}
-```
````

---

### 41 · np-a5539705

- **A**: order-workflow-api › 5.6.2-hotfix-1/guide/services/bigq.md › BigQ › Scopes › Production
- **B**: order-workflow-api › 5.6.2-hotfix-1/guide/services/bigq.md › BigQ › Scopes › Test

```diff
-#### Production
+#### Test
 
 | BigQ Scope | Topic | Consumer | Path |
 | --- | --- | --- | --- |
-| order-orchestrator | batesting-orchestrator.order-orchestrator-api | order-orchestrator-consumer | /pipeline/validate |
-| order-workflow-collector-webhooks | gh-webhooks.workflow-collector-proxy | workflow-collector-webhooks | /branches/protect |
+| order-orchestrator-test | batesting-orchestrator-testing.order-orchestrator-api | order-workflow-test-consumer | /pipeline/validate |
+| order-workflow-collector-webhooks | gh-webhooks-test.workflow-collector-proxy | workflow-collector-webhooks-test | /branches/protect |
```

---

### 42 · np-dc11451b

- **A**: 2p-revenue-optimizer-api › latest/guide/pages/table_data_dictionary/rule_custom_field.md › rule_custom_field Table
- **B**: 2p-revenue-optimizer-api › latest/guide/pages/table_data_dictionary/rule_header.md › rule_header Table

```diff
-# rule_custom_field Table
+# rule_header Table
 
-The `rule_custom_field` table stores , receiving data from PME.
+The `rule_header` table stores , receiving data from PME.
 
 The table has the following columns:
 
 | Field | Type | Constraints | Description | Extra |
 | --- | --- | --- | --- | --- |
 | id | bigint | Not null | Auto-increment primary key |  |
-| rule_row_id | bigint | Not null | Foreign | REFERENCES rule_row(id) |
-| name | varchar(180) | Not null | Name |  |
-| value_info | varchar(180) | Not null | Values |  |
+| type | varchar(180) | Not null |  |  |
+| date | timestamp | Not null | Date timestamp when was created | DEFAULT_GENERATED |
+| username | varchar(180) | Not null | Username who created rule |  |
+| name | varchar(180) | Not null | Name of rule |  |
+| description | varchar(180) | Not null | Description |  |
+| productive | boolean | Not null | Is productive |  |
+| version | int | Not null | Version |  |
```

---

### 43 · np-aec27f74

- **A**: payment-promise-gateway › 0.0.10-test-crc-migration/guide/README.md › Payment Promise Gateway › Sequence Diagrams › 1. GET /payment_promise/form
- **B**: payment-promise-gateway › 0.0.10-test-crc-migration/guide/README.md › Payment Promise Gateway › Sequence Diagrams › 3. GET /offers

````diff
-### 1. GET /payment_promise/form
+### 3. GET /offers
 
-**Description**: Retrieves the form options for payment promises. This endpoint allows querying available payment methods and permitted amounts.
+**Description**: Retrieves the offers or remedies available to the user. Shows the different options the user has to regularize their debt.
 
 ```mermaid
 sequenceDiagram
     actor User
     participant Controller as PaymentPromiseController
     participant Service as PaymentPromiseService
     participant PromiseService as PromiseService
 
-    User->>Controller: GET /payment_promise/form
-    Note over User,Controller: Parameters: caller.id, site_id
+    User->>Controller: GET /offers
+    Note over User,Controller: Parameters: caller.id, site_id, vertical
     Controller->>Controller: Extract userId from request
     Controller->>Controller: Extract siteId from request
-    Controller->>Service: getPromiseForm(userId, siteId)
-    Service->>PromiseService: getUserDebt(userId)
-    PromiseService-->>Service: UserDebtDTO
-    Service->>PromiseService: getPaymentMethods()
-    PromiseService-->>Service: PaymentMethodSearchDTO
-    Service-->>Controller: PaymentPromiseFormBO
-    Controller-->>User: Form options (JSON)
+    Controller->>Controller: Extract userType from request
+    Controller->>Service: getOffer(userId, siteId, userType)
+    Service->>PromiseService: getConditions(userId)
+    PromiseService-->>Service: ConditionDTO
+    Service-->>Controller: UserOfferBO
+    Controller-->>User: Available offers (JSON)
 ```
````

---

### 44 · np-9892d723

- **A**: catalog-portfolio-api › 0.0.1-test-bench-v2a/guide/setup/README.md › Setup & Installation › Prerequisites Summary
- **B**: catalog-portfolio-api › 0.0.1-test-bench-v2a/guide/setup/local-development.md › Local Development Setup › Prerequisites

```diff
-## Prerequisites Summary
+## Prerequisites
 
-- **Java**: JDK 17 or higher
-- **Gradle**: 7.3 or higher
-- **MySQL**: 8.0 or higher
-- **RetailFlow CLI**: Latest version
-- **Git**: For version control
+Before starting, ensure you have the following installed:
+
+- **Java JDK 17** or higher
+- **Gradle 7.3** or higher (or use the wrapper)
+- **MySQL 8.0** or higher
+- **RetailFlow CLI** (latest version)
+- **Git** for version control
+
+  <i class="fas fa-download"></i> Download Setup Template
```

---

### 45 · np-eb236b02

- **A**: payment-promise-gateway › 0.0.10-test-crc-migration/guide/README.md › Payment Promise Gateway › Sequence Diagrams › 1. GET /payment_promise/form
- **B**: payment-promise-gateway › 0.0.10-test-crc-migration/guide/README.md › Payment Promise Gateway › Sequence Diagrams › 7. GET /forgiveness_proposal/{promiseId}

````diff
-### 1. GET /payment_promise/form
+### 7. GET /forgiveness_proposal/{promiseId}
 
-**Description**: Retrieves the form options for payment promises. This endpoint allows querying available payment methods and permitted amounts.
+**Description**: Retrieves the details of a specific late fee forgiveness. Allows querying the status and details of an existing forgiveness.
 
 ```mermaid
 sequenceDiagram
     actor User
     participant Controller as PaymentPromiseController
     participant Service as PaymentPromiseService
     participant PromiseService as PromiseService
 
-    User->>Controller: GET /payment_promise/form
-    Note over User,Controller: Parameters: caller.id, site_id
-    Controller->>Controller: Extract userId from request
-    Controller->>Controller: Extract siteId from request
-    Controller->>Service: getPromiseForm(userId, siteId)
-    Service->>PromiseService: getUserDebt(userId)
-    PromiseService-->>Service: UserDebtDTO
-    Service->>PromiseService: getPaymentMethods()
-    PromiseService-->>Service: PaymentMethodSearchDTO
-    Service-->>Controller: PaymentPromiseFormBO
-    Controller-->>User: Form options (JSON)
+    User->>Controller: GET /forgiveness_proposal/{promiseId}
+    Note over User,Controller: Path param: promiseId (numeric)
+    Controller->>Controller: Validate promiseId format
+    Controller->>Service: getLateFeeForgiveness(promiseId)
+    Service->>PromiseService: getPaymentPromiseById(promiseId)
+    PromiseService-->>Service: PaymentPromiseDTO
+    Service->>Service: Extract lateFeeForgiveness
+    Service-->>Controller: LateFeeForgivenessDTO
+    Controller-->>User: Forgiveness details (JSON)
 ```
````

---

### 46 · np-3e26ddbe

- **A**: payment-promise-gateway › 0.0.10-test-crc-migration/guide/README.md › Payment Promise Gateway › Sequence Diagrams › 2. GET /payment_promise/active
- **B**: payment-promise-gateway › 0.0.10-test-crc-migration/guide/README.md › Payment Promise Gateway › Sequence Diagrams › 3. GET /offers

````diff
-### 2. GET /payment_promise/active
+### 3. GET /offers
 
-**Description**: Retrieves the user's active payment promise. Returns the promise details if an active one exists.
+**Description**: Retrieves the offers or remedies available to the user. Shows the different options the user has to regularize their debt.
 
 ```mermaid
 sequenceDiagram
     actor User
     participant Controller as PaymentPromiseController
     participant Service as PaymentPromiseService
     participant PromiseService as PromiseService
 
-    User->>Controller: GET /payment_promise/active
-    Note over User,Controller: Headers: x-caller-id
+    User->>Controller: GET /offers
+    Note over User,Controller: Parameters: caller.id, site_id, vertical
     Controller->>Controller: Extract userId from request
-    Controller->>Service: getActivePromise(userId)
-    Service->>PromiseService: getUserDebt(userId)
-    PromiseService-->>Service: UserDebtDTO
-    Service->>PromiseService: getUserPromises(userId)
-    PromiseService-->>Service: UserPromiseDTO
-    Service-->>Controller: ActivePromiseBO
-    Controller-->>User: Active promise details (JSON)
+    Controller->>Controller: Extract siteId from request
+    Controller->>Controller: Extract userType from request
+    Controller->>Service: getOffer(userId, siteId, userType)
+    Service->>PromiseService: getConditions(userId)
+    PromiseService-->>Service: ConditionDTO
+    Service-->>Controller: UserOfferBO
+    Controller-->>User: Available offers (JSON)
 ```
````

---

### 47 · np-d9ac57e1

- **A**: 2p-revenue-optimizer-api › latest/guide/pages/table_data_dictionary/rule_custom_field.md › rule_custom_field Table
- **B**: 2p-revenue-optimizer-api › latest/guide/pages/table_data_dictionary/rule_row.md › rule_row Table

```diff
-# rule_custom_field Table
+# rule_row Table
 
-The `rule_custom_field` table stores , receiving data from PME.
+The `rule_row` table stores , receiving data from PME.
 
 The table has the following columns:
 
 | Field | Type | Constraints | Description | Extra |
 | --- | --- | --- | --- | --- |
 | id | bigint | Not null | Auto-increment primary key |  |
-| rule_row_id | bigint | Not null | Foreign | REFERENCES rule_row(id) |
-| name | varchar(180) | Not null | Name |  |
-| value_info | varchar(180) | Not null | Values |  |
+| rule_id | bigint | Not null | Foreign | REFERENCES rule_header(id) |
+| site_id | json | Null | Sites Ids |  |
+| seller_id | json | Null | Sellers Ids |  |
+| domain | json | Null | Domains |  |
+| brand | json | Null | Brands |  |
+| item | json | Null | Items |  |
```

---

### 48 · np-fbb82234

- **A**: payment-promise-gateway › 0.0.10-test-crc-migration/guide/README.md › Payment Promise Gateway › Sequence Diagrams › 1. GET /payment_promise/form
- **B**: payment-promise-gateway › 0.0.10-test-crc-migration/guide/README.md › Payment Promise Gateway › Sequence Diagrams › 2. GET /payment_promise/active

````diff
-### 1. GET /payment_promise/form
+### 2. GET /payment_promise/active
 
-**Description**: Retrieves the form options for payment promises. This endpoint allows querying available payment methods and permitted amounts.
+**Description**: Retrieves the user's active payment promise. Returns the promise details if an active one exists.
 
 ```mermaid
 sequenceDiagram
     actor User
     participant Controller as PaymentPromiseController
     participant Service as PaymentPromiseService
     participant PromiseService as PromiseService
 
-    User->>Controller: GET /payment_promise/form
-    Note over User,Controller: Parameters: caller.id, site_id
+    User->>Controller: GET /payment_promise/active
+    Note over User,Controller: Headers: x-caller-id
     Controller->>Controller: Extract userId from request
-    Controller->>Controller: Extract siteId from request
-    Controller->>Service: getPromiseForm(userId, siteId)
+    Controller->>Service: getActivePromise(userId)
     Service->>PromiseService: getUserDebt(userId)
     PromiseService-->>Service: UserDebtDTO
-    Service->>PromiseService: getPaymentMethods()
-    PromiseService-->>Service: PaymentMethodSearchDTO
-    Service-->>Controller: PaymentPromiseFormBO
-    Controller-->>User: Form options (JSON)
+    Service->>PromiseService: getUserPromises(userId)
+    PromiseService-->>Service: UserPromiseDTO
+    Service-->>Controller: ActivePromiseBO
+    Controller-->>User: Active promise details (JSON)
 ```
````

---

### 49 · np-0ba4a05b

- **A**: vendor-stockkeeper-api › 0.0.10-stock-consumer/guide/alerts.md › Alerts › How to resolve › [IMPORTANT] Error restock in vendor-stockkeeper-api
- **B**: vendor-stockkeeper-api › 0.0.6-ep-restock-man/guide/alerts.md › Alerts › How to resolve › Stockkeeper-api - Error restocking item (negative quantity)

```diff
-### [IMPORTANT] Error restock in vendor-stockkeeper-api
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
```

---

### 50 · np-90c11162

- **A**: vendor-stockkeeper-api › 0.0.10-stock-consumer/guide/alerts.md › Alerts › How to resolve › Validation stock ERROR updating item
- **B**: vendor-stockkeeper-api › 0.0.6-ep-restock-man/guide/alerts.md › Alerts › How to resolve › Validation stock (publication has more stock than warehouse's stock

```diff
-### Validation stock ERROR updating item
+### Validation stock (publication has more stock than warehouse's stock
 
-This alert happens when something goes wrong while trying to update the quantity of stock into the publication
+This alert happens when something goes wrong while trying to sell a publication without stocK into 3PL facilities
 
 To resolve this alert, you need to do the following:
-1. Identify in the **vendor-stockkeeper-api** logs the item whose status could not be updated and determine why it could not be done (e.g., due to a status that does not allow updating the item such as under\_review, deleted...).
-2. If the item has available units and the status allows sales without stock (any status other than deleted), a ticket should be raised in Shield to request the publication be blocked to prevent potential out-of-stock sales.
+1. You should review the **vendor-stockkeeper-api** logs with the **stream-prod** scope to easily identify the item and SKU associated with the potential out-of-stock sale.
+2. You should confirm that the item was correctly paused by **checking the item's status**. If the item was not correctly paused, you should raise a ticket in Shield to request the publication be blocked to prevent potential out-of-stock sales.
+3. Additionally, you should identify the item to monitor it in case of future out-of-stock sales.
```

---

### 51 · np-a79b8bac

- **A**: catalog-portfolio-api › 0.0.1-test-bench-v2a/guide/api-reference/brands.md › Brand Endpoints › Create Brand › `POST /`
- **B**: catalog-portfolio-api › 0.0.1-test-bench-v2a/guide/brand-management/README.md › Brand Management › Common Operations › Creating a Brand

````diff
-### `POST /`
-
-**Request Body:**
-
-```json
-{
-  "name": "Example Brand",
-  "soft_descriptor": "EXAMPLE",
-  "site": "MLA",
-  "category": 5611201,
-  "subcategories": [123, 456],
-  "type": "lighthouse",
-  "tags": ["tag1", "tag2"],
-  "priority": 5,
-  "business_description": "Business description text"
-}
-```
-
-**Required Fields:**
-- `name`: Brand name (must be unique within site)
-- `site`: RetailFlow site code
-- `category`: Primary category ID
-- `type`: Brand type (lighthouse or standard)
-
-**Example Request:**
+### Creating a Brand
 
 ```bash
-curl -X POST "https://api.mp.internal.retailflow.com/catalog/brands/" \
+curl -X POST "https://api.mp.internal.retailflow.com/catalog/brands" \
   -H "Content-Type: application/json" \
   -d '{
     "name": "Example Brand",
     "site": "MLA",
     "category": 5611201,
     "type": "lighthouse"
   }'
 ```
-
-**Example Response:**
-
-```json
-{
-  "id": 123,
-  "name": "Example Brand",
-  "site": "MLA",
-  "category": 5611201,
-  "type": "lighthouse",
-  "status": "STAND_BY",
-  "date_created": "2024-01-15T10:30:00.000-03:00",
-  "date_last_updated": "2024-01-15T10:30:00.000-03:00"
-}
-```
````

---

### 52 · np-18c91934

- **A**: 2p-revenue-optimizer-api › 0.2.2/guide/pages/table_data_dictionary/rule_header.md › rule_header Table
- **B**: 2p-revenue-optimizer-api › latest/guide/pages/table_data_dictionary/rule_custom_field.md › rule_custom_field Table

```diff
-# rule_header Table
+# rule_custom_field Table
 
-The `rule_header` table stores , receiving data from PME.
+The `rule_custom_field` table stores , receiving data from PME.
 
 The table has the following columns:
 
 | Field | Type | Constraints | Description | Extra |
 | --- | --- | --- | --- | --- |
 | id | bigint | Not null | Auto-increment primary key |  |
-| type | varchar(180) | Not null |  |  |
-| created_date | timestamp | Not null | Date timestamp when was created | DEFAULT_GENERATED |
-| username | varchar(180) | Not null | Username who created rule |  |
-| name | varchar(180) | Not null | Name of rule |  |
-| description | varchar(180) | Not null | Description |  |
-| productive | boolean | Not null | Is productive |  |
-| productive_date | timestamp | null | productive date |  |
+| rule_row_id | bigint | Not null | Foreign | REFERENCES rule_row(id) |
+| name | varchar(180) | Not null | Name |  |
+| value_info | varchar(180) | Not null | Values |  |
```

---

### 53 · np-9fa6501d

- **A**: 2p-revenue-optimizer-api › 0.2.2/guide/pages/table_data_dictionary/rule_row.md › rule_row Table
- **B**: 2p-revenue-optimizer-api › latest/guide/pages/table_data_dictionary/rule_row.md › rule_row Table

```diff
 # rule_row Table
 
 The `rule_row` table stores , receiving data from PME.
 
 The table has the following columns:
 
 | Field | Type | Constraints | Description | Extra |
 | --- | --- | --- | --- | --- |
 | id | bigint | Not null | Auto-increment primary key |  |
 | rule_id | bigint | Not null | Foreign | REFERENCES rule_header(id) |
 | site_id | json | Null | Sites Ids |  |
 | seller_id | json | Null | Sellers Ids |  |
 | domain | json | Null | Domains |  |
 | brand | json | Null | Brands |  |
 | item | json | Null | Items |  |
-| custom_fields | json | Null | Custom Fields |  |
```

---

### 54 · np-ddd4a13e

- **A**: payment-promise-gateway › 0.0.10-test-crc-migration/guide/README.md › Payment Promise Gateway › Sequence Diagrams › 3. GET /offers
- **B**: payment-promise-gateway › 0.0.10-test-crc-migration/guide/README.md › Payment Promise Gateway › Sequence Diagrams › 7. GET /forgiveness_proposal/{promiseId}

````diff
-### 3. GET /offers
+### 7. GET /forgiveness_proposal/{promiseId}
 
-**Description**: Retrieves the offers or remedies available to the user. Shows the different options the user has to regularize their debt.
+**Description**: Retrieves the details of a specific late fee forgiveness. Allows querying the status and details of an existing forgiveness.
 
 ```mermaid
 sequenceDiagram
     actor User
     participant Controller as PaymentPromiseController
     participant Service as PaymentPromiseService
     participant PromiseService as PromiseService
 
-    User->>Controller: GET /offers
-    Note over User,Controller: Parameters: caller.id, site_id, vertical
-    Controller->>Controller: Extract userId from request
-    Controller->>Controller: Extract siteId from request
-    Controller->>Controller: Extract userType from request
-    Controller->>Service: getOffer(userId, siteId, userType)
-    Service->>PromiseService: getConditions(userId)
-    PromiseService-->>Service: ConditionDTO
-    Service-->>Controller: UserOfferBO
-    Controller-->>User: Available offers (JSON)
+    User->>Controller: GET /forgiveness_proposal/{promiseId}
+    Note over User,Controller: Path param: promiseId (numeric)
+    Controller->>Controller: Validate promiseId format
+    Controller->>Service: getLateFeeForgiveness(promiseId)
+    Service->>PromiseService: getPaymentPromiseById(promiseId)
+    PromiseService-->>Service: PaymentPromiseDTO
+    Service->>Service: Extract lateFeeForgiveness
+    Service-->>Controller: LateFeeForgivenessDTO
+    Controller-->>User: Forgiveness details (JSON)
 ```
````

---

### 55 · np-c82b1c19

- **A**: payment-promise-gateway › 0.0.10-test-crc-migration/guide/README.md › Payment Promise Gateway › Sequence Diagrams › 2. GET /payment_promise/active
- **B**: payment-promise-gateway › 0.0.10-test-crc-migration/guide/README.md › Payment Promise Gateway › Sequence Diagrams › 4. POST /payment_promise

````diff
-### 2. GET /payment_promise/active
+### 4. POST /payment_promise
 
-**Description**: Retrieves the user's active payment promise. Returns the promise details if an active one exists.
+**Description**: Creates a new payment promise. Allows the user to establish a payment commitment with a specific date and method.
 
 ```mermaid
 sequenceDiagram
     actor User
     participant Controller as PaymentPromiseController
     participant Service as PaymentPromiseService
     participant PromiseService as PromiseService
 
-    User->>Controller: GET /payment_promise/active
-    Note over User,Controller: Headers: x-caller-id
-    Controller->>Controller: Extract userId from request
-    Controller->>Service: getActivePromise(userId)
-    Service->>PromiseService: getUserDebt(userId)
-    PromiseService-->>Service: UserDebtDTO
-    Service->>PromiseService: getUserPromises(userId)
-    PromiseService-->>Service: UserPromiseDTO
+    User->>Controller: POST /payment_promise
+    Note over User,Controller: Body: PromiseCommand
+    Controller->>Controller: validateRequestBody(promiseCommand)
+    Controller->>Service: createPromise(promiseCommand)
+    Service->>Service: Calculate dateCreated
+    Service->>PromiseService: createPaymentPromise(paymentPromiseCommand)
+    PromiseService-->>Service: PaymentPromiseDTO
     Service-->>Controller: ActivePromiseBO
-    Controller-->>User: Active promise details (JSON)
+    Controller-->>User: Promise creation result (JSON)
 ```
````

---

### 56 · np-1bbd0a27

- **A**: catalog-portfolio-api › 0.0.1-test-bench-v2a/guide/api-reference/brands.md › Brand Endpoints › Update Brand › `PUT /{brandId}`
- **B**: catalog-portfolio-api › 0.0.1-test-bench-v2a/guide/brand-management/README.md › Brand Management › Common Operations › Updating a Brand

````diff
-### `PUT /{brandId}`
-
-**Path Parameters:**
-
-| Parameter | Type | Required | Description |
-| --- | --- | --- | --- |
-| `brandId` | integer | Yes | Brand ID |
-
-**Request Body:**
-
-```json
-{
-  "name": "Updated Brand Name",
-  "soft_descriptor": "UPDATED",
-  "category": 5611201,
-  "subcategories": [789],
-  "tags": ["new_tag"],
-  "priority": 8,
-  "business_description": "Updated description"
-}
-```
-
-**Example Request:**
+### Updating a Brand
 
 ```bash
 curl -X PUT "https://api.mp.internal.retailflow.com/catalog/brands/123" \
   -H "Content-Type: application/json" \
   -d '{
     "name": "Updated Brand Name",
-    "priority": 8
+    "priority": 10
   }'
 ```
````

---

### 57 · np-f3b091a2

- **A**: payment-promise-gateway › 0.0.10-test-crc-migration/guide/README.md › Payment Promise Gateway › Sequence Diagrams › 1. GET /payment_promise/form
- **B**: payment-promise-gateway › 0.0.10-test-crc-migration/guide/README.md › Payment Promise Gateway › Sequence Diagrams › 6. PUT /forgiveness_proposal

````diff
-### 1. GET /payment_promise/form
+### 6. PUT /forgiveness_proposal
 
-**Description**: Retrieves the form options for payment promises. This endpoint allows querying available payment methods and permitted amounts.
+**Description**: Confirms an existing late fee forgiveness proposal. Finalizes the forgiveness process previously initiated.
 
 ```mermaid
 sequenceDiagram
     actor User
     participant Controller as PaymentPromiseController
     participant Service as PaymentPromiseService
     participant PromiseService as PromiseService
 
-    User->>Controller: GET /payment_promise/form
-    Note over User,Controller: Parameters: caller.id, site_id
-    Controller->>Controller: Extract userId from request
-    Controller->>Controller: Extract siteId from request
-    Controller->>Service: getPromiseForm(userId, siteId)
-    Service->>PromiseService: getUserDebt(userId)
-    PromiseService-->>Service: UserDebtDTO
-    Service->>PromiseService: getPaymentMethods()
-    PromiseService-->>Service: PaymentMethodSearchDTO
-    Service-->>Controller: PaymentPromiseFormBO
-    Controller-->>User: Form options (JSON)
+    User->>Controller: PUT /forgiveness_proposal
+    Note over User,Controller: Body: LateFeeForgivenessProposalCommand
+    Controller->>Controller: validateRequestBody(command)
+    Controller->>Service: confirmLateFeeForgivenessProposal(command)
+    Service->>PromiseService: confirmProposal(borrowerId, proposalId)
+    PromiseService-->>Service: LateFeeForgivenessConfirmDTO
+    Service-->>Controller: Confirmation result
+    Controller-->>User: Confirmation status (JSON)
 ```
````

---

### 58 · np-233f37d4

- **A**: catalog-portfolio-api › 0.0.1-test-bench-v2a/guide/api-reference/brands.md › Brand Endpoints › Search Brands › `GET /`
- **B**: catalog-portfolio-api › 0.0.1-test-bench-v2a/guide/brand-management/README.md › Brand Management › Brand Model

````diff
-### `GET /`
+## Brand Model
 
-**Parameters:**
+  <i class="fas fa-download"></i> Download Brand Model Template
 
-| Parameter | Type | Required | Description |
-| --- | --- | --- | --- |
-| `collector_id` | integer | No | Filter by collector ID |
-| `brand_name` | string | No | Filter by brand name |
-| `site` | string | No | Filter by site (MLA, MLB, MLC, etc.) |
-| `tag` | string | No | Filter by tag (can be used multiple times) |
-| `owner_id` | integer | No | Filter by owner ID |
-| `type` | string | No | Filter by type (lighthouse, standard) |
-| `status` | string | No | Filter by status (ACTIVE, STAND_BY) |
-| `offset` | integer | No | Number of items to skip (default: 0) |
-| `limit` | integer | No | Number of items to return (default: 50, max: 200) |
-
-**Example Request:**
-
-```bash
-curl "https://api.mp.internal.retailflow.com/catalog/brands/?site=MLA&status=ACTIVE&limit=10"
-```
-
-**Example Response:**
+A brand represents a merchant or company in the curated portfolio with the following structure:
 
 ```json
 {
-  "results": [
-    {
-      "id": 2,
-      "name": "McDonald's",
-      "soft_descriptor": "MCDONALDS",
-      "site": "MLB",
-      "category": 5611201,
-      "subcategories": [],
-      "type": "lighthouse",
-      "tags": ["611724878", "bf_mlb_2020"],
-      "priority": 9,
-      "status": "ACTIVE",
-      "date_created": "2019-11-25T17:17:24.000-04:00",
-      "date_last_updated": "2021-06-10T13:17:10.000-04:00"
-    }
-  ],
-  "paging": {
-    "total": 1,
-    "offset": 0,
-    "limit": 10
-  }
+    "id": 2,
+    "name": "McDonald's",
+    "soft_descriptor": "MCDONALDS",
+    "site": "MLB",
+    "category": 5611201,
+    "subcategories": [],
+    "type": "lighthouse",
+    "tags": [
+        "611724878",
+        "bf_mlb_2020"
+    ],
+    "logos": [
+        {
+            "id": 1290,
+            "brand_id": 2,
+            "type": "cover",
+            "picture_id": "620688-MLA45741117352_042021"
+        },
+        {
+            "id": 23,
+            "brand_id": 2,
+            "type": "main",
+            "picture_id": "979677-MLA43159708639_082020"
+        }
+    ],
+    "resources": [
+        {
+            "type": "card",
+            "url": "https://http2.retailflow-static.com/storage/api-instore-resource/brand-041299f0-a3e0-4faa-a41f-8dd06784b5e3-card.png"
+        },
+        {
+            "type": "pin",
+            "url": "https://http2.retailflow-static.com/storage/api-instore-resource/brand-041299f0-a3e0-4faa-a41f-8dd06784b5e3-pin.png"
+        }
+    ],
+    "priority": 9,
+    "status": "ACTIVE",
+    "date_created": "2019-11-25T17:17:24.000-04:00",
+    "date_last_updated": "2021-06-10T13:17:10.000-04:00"
 }
 ```
````

---

### 59 · np-fd64cd62

- **A**: catalog-portfolio-api › 0.0.1-test-bench-v2a/guide/architecture/README.md › Architecture Overview › Architecture Diagram
- **B**: catalog-portfolio-api › 0.0.1-test-bench-v2a/guide/brand-management/README.md › Brand Management › Brand States

````diff
-## Architecture Diagram
+## Brand States
 
-  <i class="fas fa-download"></i> Download Architecture Template
+Brands can exist in three possible states:
 
 ```mermaid
 %%{init: {
   'theme': 'base',
   'themeVariables': {
     'primaryColor': '#ADD8E6',
     'primaryTextColor': '#000080',
     'primaryBorderColor': '#000',
     'lineColor': '#ff9800',
     'secondaryColor': '#006064',
     'tertiaryColor': '#fff',
     'noteTextColor': '#333',
     'textColor': '#fff'
   }
 }}%%
-graph TB
-    Client[Client Applications] --> LB[Load Balancer]
-    LB --> API[Catalog Portfolio API]
+graph TD
+    A[New Brand] --> B[STAND_BY]
+    B --> C[ACTIVE]
+    C --> B
+    B --> D[DELETED]
+    C --> D
 
-    API --> Controller[Controllers Layer]
-    Controller --> Service[Service Layer]
-    Service --> DAO[DAO Layer]
-    DAO --> DB[(MySQL Database)]
+    B --> E[Logo Required]
+    E --> B
 
-    Service --> PicturesAPI[Pictures API]
-    Service --> RegulationsAPI[Regulations API]
-    Service --> BigQ[BigQuery Events]
-
-    API --> Metrics[Metrics Collection]
-    Metrics --> DataDog[DataDog Dashboard]
-
-    Controller --> BrandController[Brand Controller]
-    Controller --> LogoController[Logo Controller]
-    Controller --> CollectorController[Collector Controller]
-    Controller --> ResourceController[Resource Controller]
-
-    Service --> BrandService[Brand Service]
-    Service --> LogoService[Logo Service]
-    Service --> CollectorService[Collector Service]
-    Service --> ResourceService[Resource Service]
-
-    DAO --> BrandDAO[Brand DAO]
-    DAO --> LogoDAO[Logo DAO]
-    DAO --> CollectorDAO[Collector DAO]
-    DAO --> ResourceDAO[Resource DAO]
+    style A fill:#ffc66d
+    style B fill:#6897bb
+    style C fill:#4CAF50
+    style D fill:#f44336
 ```
````

---

### 60 · np-43430ef0

- **A**: payment-promise-gateway › 0.0.10-test-crc-migration/guide/README.md › Payment Promise Gateway › Sequence Diagrams › 4. POST /payment_promise
- **B**: payment-promise-gateway › 0.0.10-test-crc-migration/guide/README.md › Payment Promise Gateway › Sequence Diagrams › 6. PUT /forgiveness_proposal

````diff
-### 4. POST /payment_promise
+### 6. PUT /forgiveness_proposal
 
-**Description**: Creates a new payment promise. Allows the user to establish a payment commitment with a specific date and method.
+**Description**: Confirms an existing late fee forgiveness proposal. Finalizes the forgiveness process previously initiated.
 
 ```mermaid
 sequenceDiagram
     actor User
     participant Controller as PaymentPromiseController
     participant Service as PaymentPromiseService
     participant PromiseService as PromiseService
 
-    User->>Controller: POST /payment_promise
-    Note over User,Controller: Body: PromiseCommand
-    Controller->>Controller: validateRequestBody(promiseCommand)
-    Controller->>Service: createPromise(promiseCommand)
-    Service->>Service: Calculate dateCreated
-    Service->>PromiseService: createPaymentPromise(paymentPromiseCommand)
-    PromiseService-->>Service: PaymentPromiseDTO
-    Service-->>Controller: ActivePromiseBO
-    Controller-->>User: Promise creation result (JSON)
+    User->>Controller: PUT /forgiveness_proposal
+    Note over User,Controller: Body: LateFeeForgivenessProposalCommand
+    Controller->>Controller: validateRequestBody(command)
+    Controller->>Service: confirmLateFeeForgivenessProposal(command)
+    Service->>PromiseService: confirmProposal(borrowerId, proposalId)
+    PromiseService-->>Service: LateFeeForgivenessConfirmDTO
+    Service-->>Controller: Confirmation result
+    Controller-->>User: Confirmation status (JSON)
 ```
````

---

### 61 · np-4f69f3cf

- **A**: 2p-revenue-optimizer-api › 0.2.2/guide/pages/table_data_dictionary/rule_header.md › rule_header Table
- **B**: 2p-revenue-optimizer-api › 0.2.2/guide/pages/table_data_dictionary/rule_row.md › rule_row Table

```diff
-# rule_header Table
+# rule_row Table
 
-The `rule_header` table stores , receiving data from PME.
+The `rule_row` table stores , receiving data from PME.
 
 The table has the following columns:
 
 | Field | Type | Constraints | Description | Extra |
 | --- | --- | --- | --- | --- |
 | id | bigint | Not null | Auto-increment primary key |  |
-| type | varchar(180) | Not null |  |  |
-| created_date | timestamp | Not null | Date timestamp when was created | DEFAULT_GENERATED |
-| username | varchar(180) | Not null | Username who created rule |  |
-| name | varchar(180) | Not null | Name of rule |  |
-| description | varchar(180) | Not null | Description |  |
-| productive | boolean | Not null | Is productive |  |
-| productive_date | timestamp | null | productive date |  |
+| rule_id | bigint | Not null | Foreign | REFERENCES rule_header(id) |
+| site_id | json | Null | Sites Ids |  |
+| seller_id | json | Null | Sellers Ids |  |
+| domain | json | Null | Domains |  |
+| brand | json | Null | Brands |  |
+| item | json | Null | Items |  |
+| custom_fields | json | Null | Custom Fields |  |
```

---

### 62 · np-cde275b2

- **A**: 2p-revenue-optimizer-api › 0.2.2/guide/pages/table_data_dictionary/rule_header.md › rule_header Table
- **B**: 2p-revenue-optimizer-api › latest/guide/pages/table_data_dictionary/rule_header.md › rule_header Table

```diff
 # rule_header Table
 
 The `rule_header` table stores , receiving data from PME.
 
 The table has the following columns:
 
 | Field | Type | Constraints | Description | Extra |
 | --- | --- | --- | --- | --- |
 | id | bigint | Not null | Auto-increment primary key |  |
 | type | varchar(180) | Not null |  |  |
-| created_date | timestamp | Not null | Date timestamp when was created | DEFAULT_GENERATED |
+| date | timestamp | Not null | Date timestamp when was created | DEFAULT_GENERATED |
 | username | varchar(180) | Not null | Username who created rule |  |
 | name | varchar(180) | Not null | Name of rule |  |
 | description | varchar(180) | Not null | Description |  |
 | productive | boolean | Not null | Is productive |  |
-| productive_date | timestamp | null | productive date |  |
+| version | int | Not null | Version |  |
```

---

### 63 · np-0399a0ab

- **A**: catalog-portfolio-api › 0.0.1-test-bench-v2a/guide/api-reference/brands.md › Brand Endpoints › Update Brand › `PUT /{brandId}`
- **B**: catalog-portfolio-api › 0.0.1-test-bench-v2a/guide/api-reference/brands.md › Brand Endpoints › Activate Brand › `PUT /{brandId}/activate`

````diff
-### `PUT /{brandId}`
+### `PUT /{brandId}/activate`
 
 **Path Parameters:**
 
 | Parameter | Type | Required | Description |
 | --- | --- | --- | --- |
 | `brandId` | integer | Yes | Brand ID |
 
-**Request Body:**
+**Example Request:**
+
+```bash
+curl -X PUT "https://api.mp.internal.retailflow.com/catalog/brands/123/activate"
+```
+
+**Example Response:**
 
 ```json
 {
-  "name": "Updated Brand Name",
-  "soft_descriptor": "UPDATED",
-  "category": 5611201,
-  "subcategories": [789],
-  "tags": ["new_tag"],
-  "priority": 8,
-  "business_description": "Updated description"
+  "id": 123,
+  "name": "Example Brand",
+  "status": "ACTIVE",
+  "date_last_updated": "2024-01-15T11:00:00.000-03:00"
 }
 ```
-
-**Example Request:**
-
-```bash
-curl -X PUT "https://api.mp.internal.retailflow.com/catalog/brands/123" \
-  -H "Content-Type: application/json" \
-  -d '{
-    "name": "Updated Brand Name",
-    "priority": 8
-  }'
-```
````

---

### 64 · np-42069ccf

- **A**: payment-promise-gateway › 0.0.10-test-crc-migration/guide/README.md › Payment Promise Gateway › Sequence Diagrams › 2. GET /payment_promise/active
- **B**: payment-promise-gateway › 0.0.10-test-crc-migration/guide/README.md › Payment Promise Gateway › Sequence Diagrams › 5. POST /forgiveness_proposal

````diff
-### 2. GET /payment_promise/active
+### 5. POST /forgiveness_proposal
 
-**Description**: Retrieves the user's active payment promise. Returns the promise details if an active one exists.
+**Description**: Creates a late fee forgiveness proposal. Allows initiating the process of forgiving late payment interest.
 
 ```mermaid
 sequenceDiagram
     actor User
     participant Controller as PaymentPromiseController
     participant Service as PaymentPromiseService
     participant PromiseService as PromiseService
 
-    User->>Controller: GET /payment_promise/active
-    Note over User,Controller: Headers: x-caller-id
-    Controller->>Controller: Extract userId from request
-    Controller->>Service: getActivePromise(userId)
-    Service->>PromiseService: getUserDebt(userId)
-    PromiseService-->>Service: UserDebtDTO
-    Service->>PromiseService: getUserPromises(userId)
-    PromiseService-->>Service: UserPromiseDTO
-    Service-->>Controller: ActivePromiseBO
-    Controller-->>User: Active promise details (JSON)
+    User->>Controller: POST /forgiveness_proposal
+    Note over User,Controller: Body: LateFeeForgivenessPromiseCommand
+    Controller->>Controller: validateRequestBody(command)
+    Controller->>Service: createLateFeeForgivenessProposal(command)
+    Service->>PromiseService: createLateFeeForgivenessProposal(command)
+    PromiseService-->>Service: LateFeeForgivenessProposalDTO
+    Service-->>Controller: Proposal details
+    Controller-->>User: Proposal creation result (JSON)
 ```
````
