"""API package.

Import and expose the FastAPI app so Uvicorn can find it at src.api:app,
and so individual routers can be registered here.
"""

import os
from contextlib import asynccontextmanager

from apscheduler.schedulers.background import BackgroundScheduler
from fastapi import FastAPI

from .alerts import router as alerts_router, run_evaluation
from .directives import router as directives_router
from .ops import router as ops_router
from .product import router as product_router
from .scorecard import router as scorecard_router
from .sem import router as sem_router

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
app.include_router(scorecard_router)
app.include_router(sem_router)
app.include_router(alerts_router)
app.include_router(product_router)
app.include_router(ops_router)
app.include_router(directives_router)
