# Core Directory Documentation

## Overview

The `app/core/` directory contains cross-cutting infrastructure modules that are used throughout the application. These modules provide foundational functionality for configuration management, authentication, security, and tenant isolation.

## Directory Structure

```
app/core/
├── __pycache__/          # Python bytecode cache (auto-generated)
├── config.py             # Environment configuration and settings
├── security.py           # Authentication and authorization
└── tenant_context.py     # Tenant isolation and context management
```

---

## File Documentation

### `config.py`

**Purpose**: Centralized configuration management using environment variables. It ensures that all
environment variables are validated and loaded before the application starts.

**Key Components**:

#### `Settings` Class
A Pydantic `BaseSettings` class that loads configuration from environment variables (via `.env` file).
Inheriting from the `BaseSettings` class provides automated machinery for connecting to the `.env` file

**Configuration Fields**:

- **Application Settings**:
  - `app_name` (str): Application name, defaults to "Agrisense Middleware"
  - `api_prefix` (str): API route prefix, defaults to "/api"
  - `cors_origins` (Optional[str]): CORS allowed origins as string (parsed to list)

- **Database**:
  - `database_url` (str): PostgreSQL async connection string (required)

- **Authentication**:
  - `auth_public_key` (Optional[str]): JWT public key for token validation
  - `auth_algorithm` (str): JWT algorithm, defaults to "RS256"

- **ChirpStack Integration**:
  - `chirpstack_base_url` (str): ChirpStack API base URL (required)
  - `chirpstack_api_token` (str): Token for ChirpStack API calls (required)
  - `chirpstack_webhook_token` (str): Token for validating incoming ChirpStack webhooks (optional, defaults to empty string)

- **WebSocket**:
  - `websocket_max_connections` (int): Maximum WebSocket connections per tenant, defaults to 1000

**Methods**:

- `parse_cors_origins()`: Field validator that normalizes CORS origins from various formats (JSON array, comma-separated string, or list) into a string format
- `cors_origins_list` (property): Parses the `cors_origins` string into a list of `AnyUrl` objects, supporting both JSON array format (`["http://localhost:8081"]`) and comma-separated values (`http://localhost:8081,http://localhost:3000`)

**Functions**:

- `get_settings()`: Returns a cached `Settings` instance using `@lru_cache` decorator for singleton-like behavior

**Usage**:
```python
from app.core.config import get_settings

settings = get_settings()
database_url = settings.database_url
```

---

### `security.py`

**Purpose**: Authentication and authorization infrastructure for the application.

**Key Components**:

#### `AuthContext` Dataclass
Represents an authenticated principal with their authorization scope.

**Fields**:
- `tenant_id` (uuid.UUID): The tenant the user belongs to
- `user_id` (uuid.UUID): The authenticated user's identifier
- `customer_ids` (List[uuid.UUID]): List of customer IDs the user has access to
- `device_ids` (List[str]): List of device IDs the user has access to

#### `oauth2_scheme`
FastAPI `OAuth2PasswordBearer` instance for extracting bearer tokens from requests. Configured with `auto_error=False` to allow optional authentication.

**Functions**:

- `_parse_uuid(value: str) -> uuid.UUID`:
  - Helper function to parse UUID strings
  - Raises `HTTPException` with 401 status if parsing fails

- `decode_token(token: str) -> AuthContext`:
  - **Purpose**: Decodes and validates a bearer token
  - **Current Implementation**: Lightweight stub that parses a custom token format
  - **Token Format**: `tenant:<uuid>|user:<uuid>|customers:<csv>|devices:<csv>`
  - **Example**: `tenant:123e4567-e89b-12d3-a456-426614174000|user:987fcdeb-51a2-43f1-9c8d-123456789abc|customers:abc,def|devices:dev1,dev2`
  - **Note**: This is a placeholder implementation. In production, this should be replaced with proper JWT validation using the configured public key
  - **Raises**: `HTTPException` (401) if token is missing or invalid

- `get_current_principal(token, x_tenant_id) -> AuthContext`:
  - **Purpose**: FastAPI dependency that resolves the authenticated principal
  - **Parameters**:
    - `token` (Optional[str]): Bearer token extracted from Authorization header
    - `x_tenant_id` (Optional[str]): Optional X-Tenant-ID header for admin tooling
  - **Behavior**:
    - Decodes the bearer token to extract tenant, user, customers, and devices
    - If `X-Tenant-ID` header is provided, validates it matches the token's tenant
    - Allows tenant override for admin tooling (must match token tenant)
  - **Raises**: 
    - `HTTPException` (401) if token is missing or invalid
    - `HTTPException` (403) if tenant override doesn't match token tenant
  - **Usage**: Used as a FastAPI dependency in route handlers

**Usage**:
```python
from app.core.security import get_current_principal, AuthContext
from fastapi import Depends

@router.get("/example")
async def example_route(auth: AuthContext = Depends(get_current_principal)):
    tenant_id = auth.tenant_id
    user_id = auth.user_id
    # ... use auth context
```

---

### `tenant_context.py`

**Purpose**: Manages tenant and user context for request-scoped isolation, enabling Row-Level Security (RLS) policies at the database level.

**Key Components**:

#### Context Variables
Uses Python's `contextvars` module to maintain per-request isolation in async flows:

- `tenant_id_ctx`: Context variable storing the current request's tenant ID
- `user_id_ctx`: Context variable storing the current request's user ID

**Why Context Variables?**
- Async Python applications can have multiple concurrent requests
- Context variables ensure each async task has its own isolated context
- Prevents tenant/user ID leakage between concurrent requests

**Functions**:

- `set_tenant_context(auth: AuthContext) -> None`:
  - Sets the tenant and user context variables from an `AuthContext` object
  - Called at the start of each request after authentication
  - **Usage**: Called from `app/api/deps.py` in the `get_db()` dependency

- `clear_tenant_context() -> None`:
  - Clears the tenant and user context variables
  - Called at the end of each request to prevent context leakage
  - **Usage**: Called in the `finally` block of `get_db()` dependency

- `get_tenant_id() -> Optional[uuid.UUID]`:
  - Retrieves the current request's tenant ID from context
  - Returns `None` if no context is set
  - **Usage**: Used internally and by database session attachment

- `get_user_id() -> Optional[uuid.UUID]`:
  - Retrieves the current request's user ID from context
  - Returns `None` if no context is set
  - **Usage**: Used internally and by database session attachment

- `attach_context_to_session(session: AsyncSession) -> None`:
  - **Purpose**: Attaches tenant and user context to a SQLAlchemy session
  - **Behavior**: Stores `tenant_id` and `user_id` in `session.info` dictionary
  - **Why**: Enables Row-Level Security (RLS) policies in PostgreSQL to filter data based on tenant
  - **Usage**: Called automatically in `app/db/session.py` when creating database sessions
  - **Note**: This avoids passing `tenant_id` and `user_id` explicitly through every service call

**Request Flow**:
1. Request arrives → `get_current_principal()` extracts auth context
2. `get_db()` dependency calls `set_tenant_context(auth)` → sets context variables
3. `get_session()` calls `attach_context_to_session(session)` → attaches to DB session
4. Database queries use RLS policies that read from `session.info["tenant_id"]`
5. Request completes → `clear_tenant_context()` → cleans up context

**Usage Example**:
```python
# In app/api/deps.py
async def get_db(auth: AuthContext = Depends(get_current_principal)):
    tenant_context.set_tenant_context(auth)  # Set context
    try:
        async for session in get_session():
            yield session
    finally:
        tenant_context.clear_tenant_context()  # Clear context
```

---

## Cross-Module Interactions

### Configuration → Security
- `security.py` imports `get_settings()` from `config.py` to access authentication configuration (currently reserved for future JWT validation)

### Security → Tenant Context
- `tenant_context.py` imports `AuthContext` from `security.py` to set context from authenticated principals

### API Dependencies → All Core Modules
- `app/api/deps.py` orchestrates the flow:
  1. Uses `get_current_principal()` from `security.py` to authenticate
  2. Uses `set_tenant_context()` from `tenant_context.py` to set context
  3. Database sessions use context for RLS enforcement

---

## Design Principles

1. **Separation of Concerns**: Each module has a single, well-defined responsibility
2. **Dependency Injection**: Core modules are imported and used as dependencies, not singletons
3. **Async-Safe**: Context management uses `contextvars` for proper async isolation
4. **Configuration as Code**: Settings are type-safe and validated using Pydantic
5. **Security by Default**: Authentication is required by default, with explicit opt-out where needed

---

## Future Enhancements

### `config.py`
- Add validation for database URL format
- Add support for multiple environment profiles (dev, staging, prod)
- Add feature flags

### `security.py`
- Replace token stub with real JWT validation using `auth_public_key`
- Add token expiration validation
- Add role-based access control (RBAC) support
- Add rate limiting per tenant/user

### `tenant_context.py`
- Add support for customer-scoped context
- Add audit logging of context changes
- Add context validation middleware

---

## Testing Considerations

- **Config**: Test with various `.env` file formats and missing values
- **Security**: Test token parsing with valid/invalid formats, missing tokens, tenant overrides
- **Tenant Context**: Test context isolation in concurrent async scenarios, context leakage prevention

---

## Related Documentation

- [Execution Strategy](./execution-strategy.md) - Overall architecture and design philosophy
- [Data Architecture Design Documentation](../Agrisense%20MVP%20Middleware%20Data%20Architecture%20Design%20Documentation.pdf) - Database design and tenant isolation strategy


