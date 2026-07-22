"""Export router — GET /api/export/{surface}?format=xlsx|csv|pdf

Returns a downloadable file for any exportable surface.
"""

from __future__ import annotations

import logging
from enum import Enum

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import Response

from .data import SURFACE_FETCHERS, SURFACE_LABELS, fetch_surface_data
from .formatters import to_xlsx, to_csv, to_pdf

log = logging.getLogger(__name__)

router = APIRouter(prefix="/api/export", tags=["export"])


class ExportFormat(str, Enum):
    xlsx = "xlsx"
    csv = "csv"
    pdf = "pdf"


MIME_TYPES = {
    ExportFormat.xlsx: "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    ExportFormat.csv: "text/csv",
    ExportFormat.pdf: "application/pdf",
}

EXTENSIONS = {
    ExportFormat.xlsx: ".xlsx",
    ExportFormat.csv: ".csv",
    ExportFormat.pdf: ".pdf",
}


@router.get("/surfaces")
def list_exportable_surfaces():
    """Return which surfaces support export."""
    return {
        "surfaces": [
            {"id": sid, "label": SURFACE_LABELS.get(sid, sid)}
            for sid in sorted(SURFACE_FETCHERS.keys())
        ]
    }


@router.get("/{surface}")
def export_surface(
    surface: str,
    format: ExportFormat = Query(default=ExportFormat.xlsx, description="Export file format"),
    date_start: str | None = Query(default=None, description="ISO date start filter"),
    date_end: str | None = Query(default=None, description="ISO date end filter"),
    product: str | None = Query(default=None, description="Comma-separated product filter"),
    dma: str | None = Query(default=None, description="Comma-separated DMA filter"),
    channel: str | None = Query(default=None, description="Comma-separated channel filter"),
):
    """Export a surface's data as XLSX, CSV, or PDF."""
    if surface not in SURFACE_FETCHERS:
        raise HTTPException(
            status_code=404,
            detail=f"Surface '{surface}' not found. Available: {sorted(SURFACE_FETCHERS.keys())}",
        )

    label = SURFACE_LABELS.get(surface, surface.title())

    try:
        datasets = fetch_surface_data(
            surface,
            date_start=date_start,
            date_end=date_end,
            product=product,
            dma=dma,
            channel=channel,
        )
    except Exception as e:
        log.exception("Failed to fetch data for export: %s", surface)
        raise HTTPException(status_code=500, detail=f"Data fetch failed: {e}")

    # Format
    try:
        if format == ExportFormat.xlsx:
            content = to_xlsx(datasets, surface_label=label)
        elif format == ExportFormat.csv:
            content = to_csv(datasets, surface_label=label)
        elif format == ExportFormat.pdf:
            content = to_pdf(datasets, surface_label=label)
        else:
            raise HTTPException(status_code=400, detail=f"Unknown format: {format}")
    except ImportError as e:
        # Missing optional dependency — give a helpful install hint
        log.warning("Export format %s unavailable: %s", format.value, e)
        raise HTTPException(
            status_code=422,
            detail=(
                f"{format.value.upper()} export requires a missing Python package. "
                f"Run: pip install openpyxl reportlab"
            ),
        )
    except Exception as e:
        log.exception("Failed to format export: %s / %s", surface, format)
        raise HTTPException(status_code=500, detail=f"Format failed: {e}")

    from datetime import datetime

    timestamp = datetime.now().strftime("%Y%m%d-%H%M")
    filename = f"apex-{surface}-{timestamp}{EXTENSIONS[format]}"

    return Response(
        content=content,
        media_type=MIME_TYPES[format],
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
            "Access-Control-Expose-Headers": "Content-Disposition",
        },
    )
