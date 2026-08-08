"""FastAPI application entrypoint."""
import logging
from contextlib import asynccontextmanager
from pathlib import Path

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.staticfiles import StaticFiles

from .config import settings
from .db import init_db
from .decoder import shutdown as decoder_shutdown
from . import mqtt
from .poller import poll_all_devices
from .retention import retention_sweep, scheduled_backup_all
from .routers import backups, devices, updates
from .routers import operations
from .routers.settings_api import load_overrides
from .routers import settings_api
from .updater import fail_interrupted_jobs
from .ws import hub

logging.basicConfig(level=logging.INFO)

scheduler = AsyncIOScheduler()


@asynccontextmanager
async def lifespan(_app: FastAPI):
    await init_db()
    # apply DB-stored setting overrides before scheduling anything
    await load_overrides()
    # mark update rows interrupted by a previous shutdown as failed
    await fail_interrupted_jobs()
    scheduler.add_job(
        poll_all_devices,
        "interval",
        seconds=settings.poll_interval_s,
        id="status_poll",
        max_instances=1,
        coalesce=True,
    )
    scheduler.start()
    # kick one poll immediately at startup
    scheduler.add_job(poll_all_devices, id="status_poll_boot")
    scheduler.add_job(
        scheduled_backup_all,
        "cron",
        hour=settings.backup_cron_hour,
        minute=settings.backup_cron_minute,
        id="scheduled_backups",
        max_instances=1,
        coalesce=True,
    )
    scheduler.add_job(
        retention_sweep,
        "cron",
        hour=4,
        minute=30,
        id="retention_sweep",
        max_instances=1,
        coalesce=True,
    )
    mqtt.start()
    yield
    await mqtt.stop()
    scheduler.shutdown(wait=False)
    decoder_shutdown()


app = FastAPI(title="TasmoGuardian", version="0.1.0", lifespan=lifespan)

app.include_router(devices.router, prefix="/api/v1")
app.include_router(backups.router, prefix="/api/v1")
app.include_router(updates.router, prefix="/api/v1")
app.include_router(operations.router, prefix="/api/v1")
app.include_router(settings_api.router, prefix="/api/v1")


@app.get("/healthz")
async def healthz():
    return {"status": "ok"}


# Firmware serving FOR DEVICES — must remain plain-HTTP reachable from the
# device LAN even if the app sits behind a TLS proxy (see README).
settings.firmware_dir.mkdir(parents=True, exist_ok=True)
app.mount("/ota", StaticFiles(directory=settings.firmware_dir), name="ota")


@app.websocket("/ws")
async def websocket_endpoint(ws: WebSocket):
    await hub.connect(ws)
    try:
        while True:
            # We don't act on client messages yet; keep the socket alive.
            await ws.receive_text()
    except WebSocketDisconnect:
        await hub.disconnect(ws)


# Serve the built SPA if present (Docker image); dev uses Vite proxy instead.
_spa_dist = Path(__file__).resolve().parent.parent / "static"
if _spa_dist.is_dir():
    app.mount("/", StaticFiles(directory=_spa_dist, html=True), name="spa")
