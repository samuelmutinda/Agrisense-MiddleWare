"""Validate FastAPI app startup and route registration."""
import sys
sys.path.insert(0, "/home/pc/Agrisense-MiddleWare-main")

from app.main import app

routes = []
for route in app.routes:
    if hasattr(route, "path"):
        methods = getattr(route, "methods", set()) or set()
        routes.append((route.path, sorted(methods)))

routes.sort()
print(f"Total routes: {len(routes)}")
print()
for path, methods in routes:
    print(f"  {','.join(methods) if methods else 'WS':>10}  {path}")

# Verify admin aggregates
agg_routes = [r for r in routes if "aggregates" in r[0]]
print(f"\nAdmin aggregate routes: {len(agg_routes)}")
for path, methods in agg_routes:
    print(f"  {','.join(methods):>10}  {path}")

if len(agg_routes) >= 4:
    print("\n✅ All 4 admin aggregate endpoints registered")
else:
    print(f"\n❌ Expected 4 aggregate routes, found {len(agg_routes)}")
    sys.exit(1)
