"""Export API endpoint."""

from datetime import datetime

from fastapi import APIRouter
from fastapi.responses import Response

from ..models.database import db_session
from ..models.device import Device
from ..services.export import export_devices_csv

router = APIRouter()


@router.get("/api/export/csv")
async def export_csv() -> Response:
    """Export devices to CSV file."""
    with db_session() as session:
        devices = session.query(Device).all()
        csv_data = export_devices_csv(devices)

    filename = f"devices_{datetime.now().strftime('%Y-%m-%d')}.csv"

    return Response(
        content=csv_data,
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )
