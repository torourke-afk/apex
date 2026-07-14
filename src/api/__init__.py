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

_EVAL_INTERVAL_MINUTES = int(os.getenv("APEX_ALERT_EVALUATION_INTERVAL_MINUTES", "5"))


@asynccontextmanager
async def lifespan(app: FastAPI):
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
