from time import perf_counter

from fastapi import APIRouter, status
from fastapi.responses import JSONResponse

from app.core.logger import build_log_message, get_logger
from app.db.mongo import ping_db

router = APIRouter(tags=["health"])
logger = get_logger("kodie.api.health")


@router.get("/live")
async def live() -> dict[str, str]:
    logger.debug(build_log_message("health_live_checked"))
    return {"status": "ok"}


@router.get("/ready")
async def ready() -> JSONResponse:
    started_at = perf_counter()
    logger.debug(build_log_message("health_ready_started"))

    try:
        await ping_db()
    except Exception:
        elapsed_ms = round((perf_counter() - started_at) * 1000, 2)
        logger.warning(
            build_log_message(
                "health_ready_failed", dependency="mongodb", time_ms=elapsed_ms
            )
        )
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content={
                "status": "error",
                "checks": {
                    "mongodb": {
                        "status": "error",
                        "time_ms": elapsed_ms,
                    }
                },
            },
        )

    elapsed_ms = round((perf_counter() - started_at) * 1000, 2)
    logger.debug(
        build_log_message(
            "health_ready_completed", dependency="mongodb", time_ms=elapsed_ms
        )
    )
    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={
            "status": "ok",
            "checks": {
                "mongodb": {
                    "status": "ok",
                    "time_ms": elapsed_ms,
                }
            },
        },
    )
