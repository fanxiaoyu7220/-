from __future__ import annotations

import os
import secrets
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request, Response, status
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from . import __version__
from .core import CapacityError, DownloadJobManager, PublicUrlError


PACKAGE_DIR = Path(__file__).resolve().parent
STATIC_DIR = PACKAGE_DIR / "static"
DATA_DIR = Path(os.environ.get("ACAN_WEB_DATA_DIR", str(Path.cwd() / ".acan-web-data"))).expanduser()
MAX_WORKERS = max(1, min(int(os.environ.get("ACAN_WEB_MAX_WORKERS", "2")), 4))
MAX_PENDING = max(MAX_WORKERS, min(int(os.environ.get("ACAN_WEB_MAX_PENDING", "8")), 24))
RETENTION_SECONDS = max(900, int(os.environ.get("ACAN_WEB_RETENTION_SECONDS", "7200")))
ACCESS_CODE = os.environ.get("ACAN_WEB_ACCESS_CODE", "")


class JobRequest(BaseModel):
    url: str = Field(min_length=8, max_length=4096)
    accessCode: str = Field(default="", max_length=256)


def create_app(manager: DownloadJobManager | None = None) -> FastAPI:
    job_manager = manager or DownloadJobManager(
        DATA_DIR,
        max_workers=MAX_WORKERS,
        max_pending_jobs=MAX_PENDING,
        retention_seconds=RETENTION_SECONDS,
    )
    @asynccontextmanager
    async def lifespan(_app: FastAPI):
        yield
        job_manager.shutdown()

    app = FastAPI(
        title="ACAN Studio Web",
        version=__version__,
        docs_url=None,
        redoc_url=None,
        openapi_url=None,
        lifespan=lifespan,
    )
    app.state.job_manager = job_manager

    @app.middleware("http")
    async def security_headers(request: Request, call_next):
        response: Response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "no-referrer"
        response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; style-src 'self'; script-src 'self'; img-src 'self' data:; "
            "connect-src 'self'; base-uri 'none'; frame-ancestors 'none'; form-action 'self'"
        )
        if request.url.path.startswith("/api/"):
            response.headers["Cache-Control"] = "no-store"
        return response

    @app.get("/", include_in_schema=False)
    def index():
        return FileResponse(STATIC_DIR / "index.html")

    @app.get("/api/health")
    def health():
        return {
            "ok": True,
            "version": __version__,
            "requiresAccessCode": bool(ACCESS_CODE),
            "maxFileSize": os.environ.get("ACAN_WEB_MAX_FILESIZE", "2G"),
        }

    @app.post("/api/jobs", status_code=status.HTTP_202_ACCEPTED)
    def create_job(payload: JobRequest):
        if ACCESS_CODE and not secrets.compare_digest(payload.accessCode, ACCESS_CODE):
            raise HTTPException(status_code=401, detail="体验码不正确。")
        try:
            job = job_manager.create_job(payload.url)
        except PublicUrlError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        except CapacityError as exc:
            raise HTTPException(status_code=429, detail=str(exc)) from exc
        return job.public_dict()

    @app.get("/api/jobs/{job_id}")
    def get_job(job_id: str):
        job = job_manager.get_job(job_id)
        if not job:
            raise HTTPException(status_code=404, detail="任务不存在或结果已经过期。")
        return job.public_dict()

    @app.delete("/api/jobs/{job_id}", status_code=status.HTTP_204_NO_CONTENT)
    def cancel_job(job_id: str):
        if not job_manager.cancel_job(job_id):
            raise HTTPException(status_code=409, detail="任务已经结束，无法取消。")
        return Response(status_code=status.HTTP_204_NO_CONTENT)

    @app.get("/api/jobs/{job_id}/files/{filename}")
    def download_file(job_id: str, filename: str):
        path = job_manager.get_file(job_id, filename)
        if not path:
            raise HTTPException(status_code=404, detail="文件不存在或已经过期。")
        return FileResponse(path, filename=path.name, media_type="application/octet-stream")

    app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
    return app


app = create_app()
