from time import perf_counter

from fastapi import APIRouter, status
from fastapi.responses import JSONResponse

from app.db.mongo import ping_db

router = APIRouter(tags=["health"])


@router.get("/live")
async def live() -> dict[str, str]:
    return {"status": "ok"}


@router.get("/ready")
async def ready() -> JSONResponse:
    started_at = perf_counter()

    try:
        await ping_db()
    except Exception:
        elapsed_ms = round((perf_counter() - started_at) * 1000, 2)
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
