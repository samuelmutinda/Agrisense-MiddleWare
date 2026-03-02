## API Design Philosophy

1. __API mirrors business intent, not tables__ - The client should interact with arrivals,
transfers, collections and inventory views, not raw ledger rows or internal joins.
The Ledger is an internal implementation detail.


2. __Read APIs ≠ Write APIs__ - Write APIs map closely to business events
(e.g. “create transfer”, “confirm transfer”) while Read APIs expose views
(e.g. “current inventory”, “transfer history”). Read APIs and Write APIs are not 
symmetric.


3. __ChirpStack events are ingest, not business APIs__ - The HTTP endpoint for ChirpStack
connects to the middleware while the middleware relays ChirpStack data to the client
over websockets. Under no circumstances shall the client talk to ChirpStack directly.

## ORM Modeling
As a design principle, SQLAlchemy models and pydantic models __MUST__ remain separated.  
SQLAlchemy models are responsible for database truth. Example:  

    class HarvestArrival(Base):
        __tablename__ = "harvest_arrival"
    
        intake_id = Column(UUID, primary_key=True)
        customer_id = Column(UUID, ForeignKey("customer.customer_id"))
        crop_id = Column(UUID, ForeignKey("crop.crop_id"))
        arrived_at = Column(DateTime)
        inspected_by_user_id = Column(UUID)

Pydantic models are responsible for API contracts. Example:  

    class HarvestArrivalCreate(BaseModel):
        customer_id: UUID
        crop_id: UUID
        arrived_at: datetime

    class HarvestArrivalResponse(BaseModel):
        intake_id: UUID
        customer_name: str
        crop_name: str
        arrived_at: datetime

## API Surface Design
The API will be split into 3 surfaces:
* Business APIs (REST) - These will map directly to business events. 
Examples: `POST   /arrivals, GET    /arrivals, GET    /arrivals/{intake_id}`

* Read / View APIs (derived data) - These APIs are read-only and aggregate ledger data.
Internally, they query the ledger, but externally they look like normal resources.
Examples: `GET /inventory/arrivals/{intake_id}, GET /inventory/cold-storage/{cs_id},
GET /inventory/summary`

* ChirpStack ingest + WebSockets - These APIs receive payload from ChirpStack and push
it to the client over websockets. Ingestion will be done on
`POST /integrations/chirpstack/events` while the client will listen to events on 
`WS /ws/tenant`

## File structure

The file structure is organized as follows:
* **core** - Constitutes all cross-cutting infrastructure (modules that are used everywhere).
These models include:
  * `config.py` - Handles Environment variables, DB URLs, secrets, feature flags
  * `security.py` - Handles authentication, token validation, user identity extraction.
  * `tenant_context.py` - Resolves tenant_id and user_id per request and
  injects tenant context into DB sessions (for RLS).
* **db** - This is pure data representation. It includes the following modules and directories:
  * `base.py` - SQLAlchemy Base, metadata, naming conventions.
  * `session.py` - DB session creation, attaches tenant context to session, handles transactions
  * `modules/` directory containing independent modules for each table e.g., `arrivals.py`
* **api** - This is the transport layer. It includes the following modules and directories:
  * `deps.py` - Dependency injection, Get DB session, Get authenticated user, Resolve tenant context.
  * `routes/` directory containing independent modules for each route, e.g., `arrivals.py`, `transfers.py`,
  `inventory.py`, `chirpstack.py`.
* **ws** - Defines WebSocket event types, serializes outbound messages, 
applies filtering logic before emitting
  * **schemas** - Dedines 
* **services** - The authoritative layer for enforcing business rules and invariants. Responsibilities:
  * Validate business workflows
  * Write business event records
  * Create inventory ledger entries
  * Enforce transactional consistency 
  * Emit WebSocket events  
Examples: `arrival_service.py, transfer_service.py, inventory_service.py, chirpstack_service.py`
* `migrations` - Database migration scripts

```
app/
├── main.py
│
├── core/
│   ├── config.py
│   ├── security.py
│   ├── tenant_context.py
│   └── websocket_manager.py
│
├── db/
│   ├── base.py
│   ├── session.py
│   └── models/
│       ├── tenant.py
│       ├── customer.py
│       ├── user.py
│       ├── user_role.py
│       ├── device.py
│       ├── sensor_type.py
│       ├── device_sensor_capability.py
│       ├── cold_storage_unit.py
│       ├── crop.py
│       ├── harvest_arrival.py
│       ├── harvest_transfer.py
│       ├── harvest_collection.py
│       ├── harvest_loss.py
│       ├── harvest_spoilage.py
│       └── harvest_inventory_ledger.py
│
├── schemas/
│   ├── arrival.py
│   ├── transfer.py
│   ├── collection.py
│   ├── inventory.py
│   ├── loss.py
│   ├── spoilage.py
│   ├── sensor.py
│   └── common.py
│
├── services/
│   ├── arrival_service.py
│   ├── transfer_service.py
│   ├── collection_service.py
│   ├── inventory_service.py
│   ├── loss_service.py
│   ├── spoilage_service.py
│   └── chirpstack_service.py
│
├── api/
│   ├── deps.py
│   └── routes/
│       ├── arrivals.py
│       ├── transfers.py
│       ├── collections.py
│       ├── inventory.py
│       ├── losses.py
│       ├── spoilages.py
│       └── chirpstack.py
│
├── ws/
│   ├── manager.py
│   ├── events.py
│   └── schemas.py
│
├── migrations/
│   ├── env.py
│   └── versions/
│       └── xxxx_initial_schema.py
│
└── tests/
    ├── unit/
    ├── integration/
    └── conftest.py
```
