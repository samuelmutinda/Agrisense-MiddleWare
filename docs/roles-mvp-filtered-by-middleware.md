# Roles & Privileges — Filtered by Middleware Capabilities

**Source:** Client analysis (AgriSense web client)  
**Filter:** Only what the Agrisense Middleware APIs and WebSocket support.

---

## Middleware Capabilities (Summary)

The middleware provides **tenant-scoped** REST APIs and a **WebSocket** for real-time events. Auth is token-based (`tenant_id`, `user_id`, `customer_ids`, `device_ids`). **There is no RBAC in the middleware**; all authenticated users have the same API access within their tenant. Role-based restrictions (e.g. read-only) must be enforced **client-side**.

| Area | Middleware support |
|------|--------------------|
| **Arrivals** | Create, list, get by id |
| **Transfers** | Initiate, cancel, complete; list, get by id |
| **Collections** | Record; list, get by id |
| **Losses** | Record (transfer / storage); list, get by id |
| **Spoilages** | Record; list, get by id |
| **Inventory** | Current (by intake/crop/customer/cold storage), summary (by cold storage) |
| **Crops** | CRUD (global, not tenant-scoped) |
| **Customers** | CRUD (tenant-scoped) |
| **Real-time** | WebSocket: arrival, transfer, spoilage, loss, collection events |
| **Device/sensors** | Chirpstack webhook ingests uplinks; no device control or maintenance APIs |

**Not supported:** maintenance logs, user/team management, financial or predictive analytics, system configuration, API key management, billing, or rate limits.

---

## Roles Retained for MVP

Only roles whose **permissions and features** align with the above are kept. Operator, manager, and admin are **dropped**; their distinctive capabilities are not supported by the middleware.

---

### 1. `cultivator`

| Field | Value |
|-------|--------|
| **canonicalRole** | `cultivator` |
| **displayName** | CULTIVATOR |
| **description** | Post-harvest and farmer workflows: crop management, storage tracking, consignment visibility, basic inventory view. |

**Permissions (middleware-backed only):**

- `view_own_data` — View tenant-scoped arrivals, transfers, collections, losses, spoilages, inventory, customers.
- `track_consignment` — List/get arrivals and transfers (consignment-style tracking).
- `access_basic_analytics` — Inventory current + summary (aggregates by intake, crop, cold storage).
- `receive_realtime_events` — WebSocket events for arrival, transfer, spoilage, loss, collection.

**Features (middleware-backed only):**

- **Crop tracking** — Crops CRUD; arrivals linked to crop/customer.
- **Storage monitoring** — Inventory endpoints; cold storage in ledger.
- **Basic analytics** — Inventory summary and current inventory.
- **Real-time alerts** — WebSocket business events (no device control).

**Example actions (middleware-only):**

- View own arrivals, transfers, collections, losses, spoilages.
- View inventory (current and summary).
- Record arrival, initiate/cancel/complete transfer, record collection, record spoilage, record transfer or storage loss.
- Manage crops and customers (within tenant for customers).
- Receive WebSocket alerts for new arrivals, transfers, spoilages, losses, collections.

**Notes:**

- Billing, support tiers, and API rate limits are **out of scope** for the middleware; omit or handle in client/gateway.
- “AI Engine” recommendations are client-side; middleware does not provide them.

---

### 2. `read_only`

| Field | Value |
|-------|--------|
| **canonicalRole** | `read_only` |
| **displayName** | READ ONLY |
| **description** | View-only access for auditors or reviewers; no create/update/delete. |

**Permissions (middleware-backed only):**

- `view_only_access` — Same GET endpoints as cultivator (tenant-scoped).
- `no_modifications` — No POST/PUT/DELETE; **enforced by client**, not middleware.

**Features (middleware-backed only):**

- **Data viewing** — List/get arrivals, transfers, collections, losses, spoilages, inventory, crops, customers.
- **Report-style access** — Inventory current + summary.

**Example actions (middleware-only):**

- View arrivals, transfers, collections, losses, spoilages, inventory, crops, customers.
- Optionally subscribe to WebSocket for read-only real-time updates.

**Notes:**

- Middleware does **not** enforce read-only; the client must restrict UI and API calls to GET (and possibly WebSocket subscribe only).
- Dedicated audit trail or compliance export APIs are not provided; “audit” = view-only access to existing data.

---

### 3. `customer` (optional)

| Field | Value |
|-------|--------|
| **canonicalRole** | `customer` |
| **displayName** | CUSTOMER |
| **description** | Optional limited-access role; exact scope TBD. Token includes `customer_ids`; WebSocket can filter by `customer_id`. |

**Permissions (middleware-backed only):**

- `view_own_data` — Intended: restrict to “own” data. **Middleware does not yet filter REST APIs by `customer_ids`**; data is tenant-wide. Client could restrict views by customer when backend adds support.

**Features (middleware-backed only):**

- Same **view** capabilities as cultivator, but client may limit to customer-specific context when middleware supports it.

**Example actions (middleware-only):**

- View own consignments/batches (arrivals, transfers) **if** client applies customer-based filtering (future middleware support).

**Notes:**

- **Recommendation:** Treat as optional. Keep in schema only if client will use `customer_ids` for filtering or future middleware work will add customer-scoped APIs.
- Standardise with other roles (e.g. casing, usage in data loaders).

---

## Roles Dropped for Middleware MVP

| Role | Reason |
|------|--------|
| **operator** | Device control, maintenance logs, and setpoint management are not in the middleware. Real-time monitoring could use WebSocket, but operator-specific features are absent. |
| **manager** | Team management, financial views, predictive reports, advanced reporting—none are provided by the middleware. |
| **admin** | User management, system configuration, full system access, API key management—middleware has no such APIs. |

---

## Suggested Canonical Set for MVP Client

```text
cultivator
read_only
customer (optional)
```

**Rationale:** The middleware only supports data and workflows that fit **cultivator** (full) and **read_only** (view-only, client-enforced). **Customer** is optional until customer-scoped APIs or client-side filtering based on `customer_ids` is clearly defined.

---

## Implementation Notes

1. **RBAC:** Enforce roles in the **client** (and/or API gateway). Middleware continues to perform tenant-scoped auth only.
2. **Read-only:** Implement by having the client call only GET endpoints (and optionally WebSocket); no POST/PUT/DELETE.
3. **Billing / rate limits / support:** Handle outside the middleware (e.g. gateway, separate services).
4. **Future:** If middleware adds customer-scoped queries, device control, or audit APIs, roles can be extended accordingly.
