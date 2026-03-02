from __future__ import annotations

import asyncio
import os
import sys
from pathlib import Path

project_root = Path(__file__).parent.parent

sys.path.insert(0, str(project_root))

os.chdir(project_root)

os.environ.setdefault("ENV_FILE", str(project_root / ".env"))

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from app.core.config import get_settings
from app.db.models import Tenant
from app.services.chirpstack_client import get_all_tenants


async def sync_tenants() -> None:
    settings = get_settings()
    
    print(f"Connecting to database: {settings.database_url.split('@')[-1] if '@' in settings.database_url else '***'}")
    print(f"Fetching tenants from ChirpStack: {settings.chirpstack_base_url}")
    print("-" * 60)
    
    engine = create_async_engine(settings.database_url, echo=False)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    
    try:
        print("Fetching tenants from ChirpStack...")
        chirpstack_tenants = await get_all_tenants()
        print(f"Found {len(chirpstack_tenants)} tenants in ChirpStack")
        
        if not chirpstack_tenants:
            print("No tenants found in ChirpStack. Exiting.")
            return
        
        async with async_session() as session:
            added_count = 0
            existing_count = 0
            error_count = 0
            
            for cs_tenant in chirpstack_tenants:
                tenant_id_str = cs_tenant.get("id")
                tenant_name = cs_tenant.get("name", "Unknown")
                
                if not tenant_id_str:
                    print(f"⚠️  Skipping tenant with missing ID: {tenant_name}")
                    error_count += 1
                    continue
                
                try:
                    import uuid
                    tenant_id = uuid.UUID(tenant_id_str)
                    
                    stmt = select(Tenant).where(Tenant.id == tenant_id)
                    result = await session.execute(stmt)
                    existing_tenant = result.scalar_one_or_none()
                    
                    if existing_tenant:
                        print(f"✓ Tenant already exists: {tenant_name} (ID: {tenant_id})")
                        existing_count += 1
                    else:
                        new_tenant = Tenant(
                            id=tenant_id,
                            name=tenant_name,
                        )
                        session.add(new_tenant)
                        print(f"Added new tenant: {tenant_name} (ID: {tenant_id})")
                        added_count += 1
                
                except ValueError as e:
                    print(f"Invalid tenant ID format for '{tenant_name}': {tenant_id_str} - {e}")
                    error_count += 1
                except Exception as e:
                    print(f"Error processing tenant '{tenant_name}': {e}")
                    error_count += 1
            
            if added_count > 0:
                await session.commit()
                print("-" * 60)
                print(f"Successfully added {added_count} new tenant(s)")
            else:
                print("-" * 60)
                print("No new tenants to add")
            
            print(f"Summary:")
            print(f"   - Existing tenants: {existing_count}")
            print(f"   - New tenants added: {added_count}")
            print(f"   - Errors: {error_count}")
            print(f"   - Total processed: {len(chirpstack_tenants)}")
    
    except Exception as e:
        print(f"Fatal error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    
    finally:
        await engine.dispose()


if __name__ == "__main__":
    asyncio.run(sync_tenants())

