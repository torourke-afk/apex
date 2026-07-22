"""API package.

Import and expose the FastAPI app so Uvicorn can find it at src.api:app,
and so individual routers can be registered here.
"""

import functools
import os
from contextlib import asynccontextmanager

# ---------------------------------------------------------------------------
# Streamlit cache shim
# Replace st.cache_data / st.cache_resource with cachetools TTLCache so data
# modules work under FastAPI without a running Streamlit runtime.  Must run
# before any src.data.* imports.
# ---------------------------------------------------------------------------
import streamlit as _st
from cachetools import TTLCache as _TTLCache


def _cache_data(fn=None, *, ttl=300, show_spinner=False, hash_funcs=None, **_kw):
    def decorator(f):
        _cache = _TTLCache(maxsize=256, ttl=ttl)

        @functools.wraps(f)
        def wrapper(*args, **kwargs):
            try:
                key = (args, tuple(sorted(kwargs.items())))
                hash(key)
            except TypeError:
                return f(*args, **kwargs)
            if key not in _cache:
                _cache[key] = f(*args, **kwargs)
            return _cache[key]

        wrapper.clear = _cache.clear

        return wrapper

    return decorator(fn) if fn is not None else decorator


def _cache_resource(fn=None, **_kw):
    return fn if fn is not None else lambda f: f


_st.cache_data = _cache_data
_st.cache_resource = _cache_resource
# ---------------------------------------------------------------------------

from apscheduler.schedulers.background import BackgroundScheduler
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# --- Existing routers ---
from .alerts import router as alerts_router, run_evaluation
from .directives import router as directives_router
from .ops import router as ops_router
from .product import router as product_router
from .scorecard import router as scorecard_router
from .sem import router as sem_router

# --- New domain routers ---
from .spend import router as spend_router
from .funnel import router as funnel_router
from .channels_brand import router as channels_brand_router
from .channels_seo import router as channels_seo_router
from .channels_aeo import router as channels_aeo_router
from .channels_social import router as channels_social_router
from .retention import router as retention_router
from .brand_awareness_api import router as brand_awareness_router
from .simulate import router as simulate_router
from .settings_api import router as settings_router
from .creative import router as creative_router
from .modeling import router as modeling_router
from .media import media_router
from .audience import audience_router
from .experiments import router as experiments_router
from .allocation import router as allocation_router
from .launch import router as launch_router
from .lens import router as lens_router
from .metrics import router as metrics_router

# --- Connector & Sync routers ---
from .sync.router import router as sync_router

# --- Audit router ---
from .audit import router as audit_router

# --- Export router ---
from .export.router import router as export_router

_EVAL_INTERVAL_MINUTES = int(os.getenv("APEX_ALERT_EVALUATION_INTERVAL_MINUTES", "5"))


async def _init_connectors():
    """Register the seed connector (and any configured external connectors)."""
    from .connectors import registry
    from .connectors.seed import SeedConnector
    from .connectors.google_analytics import GoogleAnalytics4Connector, default_config as ga4_config
    from .connectors.semrush import SEMrushConnector, default_config as semrush_config
    from .connectors.google_ads import GoogleAdsConnector, default_config as gads_config
    from .connectors.meta_ads import MetaAdsConnector, default_config as meta_config

    # Always register the seed connector as fallback
    seed = SeedConnector()
    registry.register(seed, is_fallback=True)
    await seed.connect()

    # Auto-register external connectors if their env vars are set
    for ConnectorCls, config_fn in [
        (GoogleAnalytics4Connector, ga4_config),
        (SEMrushConnector, semrush_config),
        (GoogleAdsConnector, gads_config),
        (MetaAdsConnector, meta_config),
    ]:
        cfg = config_fn()
        if cfg.enabled:
            conn = ConnectorCls(cfg)
            registry.register(conn)
            try:
                await conn.connect()
            except Exception as exc:
                import logging
                logging.getLogger(__name__).warning(
                    "Failed to connect %s: %s", cfg.display_name, exc,
                )


@asynccontextmanager
async def lifespan(app: FastAPI):
    # --- Connector init ---
    await _init_connectors()

    # --- Background scheduler ---
    scheduler = BackgroundScheduler()
    scheduler.add_job(
        run_evaluation,
        trigger="interval",
        minutes=_EVAL_INTERVAL_MINUTES,
        id="alert_evaluation",
        replace_existing=True,
    )
    scheduler.start()
    try:
        yield
    finally:
        scheduler.shutdown(wait=False)
        # Disconnect all connectors
        from .connectors import registry
        import asyncio
        try:
            await registry.disconnect_all()
        except Exception:
            pass


app = FastAPI(title="Apex API", version="0.1.0", lifespan=lifespan)

# CORS — allow the Next.js front end (web/) and Vite dev server to call the
# API from the browser.  Origins are configurable via APEX_CORS_ORIGINS
# (comma-separated); defaults cover local dev for both Next.js and Vite.
_cors_origins = os.getenv(
    "APEX_CORS_ORIGINS",
    "http://localhost:3000,http://127.0.0.1:3000,"
    "http://localhost:5173,http://127.0.0.1:5173",
).split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in _cors_origins if o.strip()],
    allow_methods=["*"],
    allow_headers=["*"],
    allow_credentials=False,
)

# --- Mount existing routers ---
app.include_router(scorecard_router)
app.include_router(sem_router)
app.include_router(alerts_router)
app.include_router(product_router)
app.include_router(ops_router)
app.include_router(directives_router)

# --- Mount new domain routers ---
app.include_router(spend_router)
app.include_router(funnel_router)
app.include_router(channels_brand_router)
app.include_router(channels_seo_router)
app.include_router(channels_aeo_router)
app.include_router(channels_social_router)
app.include_router(retention_router)
app.include_router(brand_awareness_router)
app.include_router(simulate_router)
app.include_router(settings_router)
app.include_router(creative_router)
app.include_router(modeling_router)
app.include_router(media_router)
app.include_router(audience_router)
app.include_router(launch_router)
app.include_router(allocation_router)
app.include_router(experiments_router)

# --- Lens NL-to-SQL ---
app.include_router(lens_router)

# --- Audit ---
app.include_router(audit_router)

# --- Metric Layer ---
app.include_router(metrics_router)

# --- Connector & Sync ---
app.include_router(sync_router)

# --- Export ---
app.include_router(export_router)
