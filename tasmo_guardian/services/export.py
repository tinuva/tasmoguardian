"""Export service - CSV export functionality."""

import csv
import io


def export_devices_csv(devices: list) -> str:
    """Export devices to CSV string."""
    output = io.StringIO()
    writer = csv.writer(output)

    writer.writerow(["Name", "IP", "MAC", "Type", "Version", "Last Backup", "Backup Count"])

    for device in devices:
        writer.writerow([
            device.name,
            device.ip,
            device.mac,
            "Tasmota" if device.type == 0 else "WLED",
            device.version,
            device.lastbackup.strftime("%Y-%m-%d %H:%M:%S") if device.lastbackup else "",
            device.noofbackups or 0,
        ])

    return output.getvalue()
