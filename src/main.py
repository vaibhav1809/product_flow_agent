
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .config import log, CONFIG
from .api.v1 import all_routes


app = FastAPI(
    title=CONFIG.project_name,
    version=CONFIG.version,
    description=CONFIG.description,
    openapi_url=f"{CONFIG.api_v1_str}/openapi.json",
)

log.info(f"Starting application: {CONFIG.project_name} v{CONFIG.version}")

origins = ["*"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API router
for route in all_routes:
    if route.get("isWebSocket", False):
        app.include_router(route["router"], tags=route.get("tags", []))
    else:
        prefix = f'{CONFIG.api_v1_str}{route.get("prefix", "")}'
        app.include_router(route["router"], prefix=prefix,
                           tags=route.get("tags", []))
