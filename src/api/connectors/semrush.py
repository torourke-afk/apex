"""
SEMrush Connector
=================

Pulls keyword analytics, domain overview, and competitive data from
the SEMrush API.  Maps to: sem, brand_awareness, seo domains.

Required credentials (env vars):
    SEMRUSH_API_KEY  — SEMrush API key
"""

from __future__ import annotations

import logging
import os
from datetime import datetime
from typing import Any
from urllib.parse import urlencode

from .base import (
    BaseConnector,
    ConnectorConfig,
    ConnectorHealth,
    DataDomain,
    QueryFilters,
)

logger = logging.getLogger(__name__)

_API_BASE = "https://api.semrush.com"
_DEFAULT_KEY = os.environ.get("SEMRUSH_API_KEY", "")


def default_config() -> ConnectorConfig:
    return ConnectorConfig(
        connector_type="semrush",
        display_name="SEMrush",
        domains=[DataDomain.SEM, DataDomain.BRAND_AWARENESS, DataDomain.SEO],
        credentials={"api_key": _DEFAULT_KEY},
        settings={
            "database": "us",          # SEMrush geo database
            "export_columns": "Ph,Po,Nq,Cp,Co,Nr,Td",
        },
        enabled=bool(_DEFAULT_KEY),
        refresh_interval_minutes=60,
    )


class SEMrushConnector(BaseConnector):
    """Connector for SEMrush Analytics API."""

    def __init__(self, config: ConnectorConfig | None = None) -> None:
        super().__init__(config or default_config())
        self._session: Any = None

    # -- Lifecycle ----------------------------------------------------------

    async def connect(self) -> bool:
        api_key = self.config.credentials.get("api_key")
        if not api_key:
            self._health = ConnectorHealth(
                status="disconnected",
                last_error="Missing SEMRUSH_API_KEY",
            )
            return False

        try:
            import httpx

            self._session = httpx.AsyncClient(
                timeout=30.0,
                headers={"Accept": "text/csv"},
            )

            # Validate key with a minimal request
            params = {
                "type": "domain_ranks",
                "key": api_key,
                "domain": "example.com",
                "database": "us",
                "export_columns": "Dn",
            }
            resp = await self._session.get(f"{_API_BASE}/", params=params)

            if "ERROR" in resp.text and "WRONG KEY" in resp.text:
                self._health = ConnectorHealth(
                    status="error",
                    last_error="Invalid SEMrush API key",
                )
                return False

            self._health = ConnectorHealth(
                status="connected",
                last_sync=datetime.utcnow(),
                details={"database": self.config.settings.get("database", "us")},
            )
            return True

        except ImportError:
            self._health = ConnectorHealth(
                status="error",
                last_error="httpx package not installed. Run: pip install httpx",
            )
            return False
        except Exception as exc:
            self._health = ConnectorHealth(
                status="error",
                last_error=str(exc),
            )
            return False

    async def disconnect(self) -> None:
        if self._session:
            await self._session.aclose()
            self._session = None
        self._health = ConnectorHealth(status="disconnected")

    async def health_check(self) -> ConnectorHealth:
        if self._session is None:
            return ConnectorHealth(status="disconnected")
        return self._health

    # -- Data fetching ------------------------------------------------------

    async def fetch(
        self,
        domain: DataDomain,
        endpoint: str,
        filters: QueryFilters | None = None,
    ) -> Any:
        if self._session is None:
            return None

        api_key = self.config.credentials["api_key"]
        db = self.config.settings.get("database", "us")

        dispatch = {
            ("sem", "overview"): self._fetch_sem_overview,
            ("sem", "keywords"): self._fetch_keywords,
            ("brand_awareness", "share_of_search"): self._fetch_share_of_search,
            ("seo", "rankings"): self._fetch_organic_rankings,
            ("seo", "competitors"): self._fetch_organic_competitors,
        }

        handler = dispatch.get((domain.value, endpoint))
        if handler is None:
            logger.warning("SEMrush: no handler for %s.%s", domain.value, endpoint)
            return None

        try:
            result = await handler(api_key, db, filters)
            self._health.last_sync = datetime.utcnow()
            return result
        except Exception as exc:
            logger.error("SEMrush fetch error (%s.%s): %s", domain.value, endpoint, exc)
            self._health.last_error = str(exc)
            self._health.status = "degraded"
            return None

    # -- SEMrush fetch implementations --------------------------------------

    async def _fetch_sem_overview(
        self,
        api_key: str,
        database: str,
        filters: QueryFilters | None,
    ) -> dict[str, Any]:
        """Fetch domain-level SEM overview."""
        target_domain = self.config.settings.get("target_domain", "53.com")
        params = {
            "type": "domain_adwords",
            "key": api_key,
            "domain": target_domain,
            "database": database,
            "export_columns": "Ph,Po,Nq,Cp,Co,Nr,Td",
            "display_limit": 100,
        }
        resp = await self._session.get(f"{_API_BASE}/", params=params)
        return _parse_csv_response(resp.text, [
            "keyword", "position", "search_volume", "cpc",
            "competition", "results", "trend",
        ])

    async def _fetch_keywords(
        self,
        api_key: str,
        database: str,
        filters: QueryFilters | None,
    ) -> dict[str, Any]:
        """Fetch keyword analytics."""
        target_domain = self.config.settings.get("target_domain", "53.com")
        params = {
            "type": "domain_organic",
            "key": api_key,
            "domain": target_domain,
            "database": database,
            "export_columns": "Ph,Po,Nq,Cp,Ur,Tr,Tc",
            "display_limit": 200,
        }
        resp = await self._session.get(f"{_API_BASE}/", params=params)
        return _parse_csv_response(resp.text, [
            "keyword", "position", "search_volume", "cpc",
            "url", "traffic", "traffic_cost",
        ])

    async def _fetch_share_of_search(
        self,
        api_key: str,
        database: str,
        filters: QueryFilters | None,
    ) -> list[dict[str, Any]]:
        """Fetch branded keyword MSV for share-of-search calculation."""
        keywords = self.config.settings.get("brand_keywords", [
            "fifth third bank",
            "huntington bank",
            "keybank",
            "pnc bank",
            "us bank",
        ])

        results = []
        for kw in keywords:
            params = {
                "type": "phrase_this",
                "key": api_key,
                "phrase": kw,
                "database": database,
                "export_columns": "Ph,Nq,Cp,Co",
            }
            resp = await self._session.get(f"{_API_BASE}/", params=params)
            rows = _parse_csv_response(resp.text, [
                "keyword", "search_volume", "cpc", "competition",
            ])
            if rows.get("rows"):
                row = rows["rows"][0]
                results.append({
                    "keyword": kw,
                    "msv": int(row.get("search_volume", 0)),
                    "cpc": float(row.get("cpc", 0)),
                })
            else:
                results.append({"keyword": kw, "msv": 0, "cpc": 0.0})

        total_msv = sum(r["msv"] for r in results)
        for r in results:
            r["share"] = r["msv"] / total_msv if total_msv > 0 else 0

        return results

    async def _fetch_organic_rankings(
        self,
        api_key: str,
        database: str,
        filters: QueryFilters | None,
    ) -> dict[str, Any]:
        """Fetch organic search rankings."""
        target_domain = self.config.settings.get("target_domain", "53.com")
        params = {
            "type": "domain_organic",
            "key": api_key,
            "domain": target_domain,
            "database": database,
            "export_columns": "Ph,Po,Nq,Cp,Ur,Tr",
            "display_limit": 100,
            "display_sort": "tr_desc",
        }
        resp = await self._session.get(f"{_API_BASE}/", params=params)
        return _parse_csv_response(resp.text, [
            "keyword", "position", "search_volume", "cpc", "url", "traffic",
        ])

    async def _fetch_organic_competitors(
        self,
        api_key: str,
        database: str,
        filters: QueryFilters | None,
    ) -> dict[str, Any]:
        """Fetch organic competitor domains."""
        target_domain = self.config.settings.get("target_domain", "53.com")
        params = {
            "type": "domain_organic_organic",
            "key": api_key,
            "domain": target_domain,
            "database": database,
            "export_columns": "Dn,Cr,Np,Or,Ot,Oc,Ad",
            "display_limit": 20,
        }
        resp = await self._session.get(f"{_API_BASE}/", params=params)
        return _parse_csv_response(resp.text, [
            "domain", "competition_level", "common_keywords",
            "organic_keywords", "organic_traffic", "organic_cost", "adwords_keywords",
        ])


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _parse_csv_response(text: str, columns: list[str]) -> dict[str, Any]:
    """Parse SEMrush CSV response into a dict with column-mapped rows."""
    lines = [l.strip() for l in text.strip().split("\n") if l.strip()]
    if not lines or lines[0].startswith("ERROR"):
        return {"rows": [], "error": lines[0] if lines else "Empty response"}

    rows = []
    for line in lines:
        values = line.split(";")
        if len(values) >= len(columns):
            rows.append(dict(zip(columns, values)))

    return {"rows": rows, "total": len(rows)}
