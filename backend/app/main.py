from __future__ import annotations

from fastapi import FastAPI

from backend.app.api.routes.sample_analysis import router as sample_analysis_router
from backend.app.api.routes.system import router as system_router


def create_app() -> FastAPI:
    app = FastAPI(
        title="样例视频分析后端",
        version="0.1.0",
        description="面向样例视频输入、结构拆解和标准化结果输出的最小后端闭环。",
    )
    app.include_router(system_router)
    app.include_router(sample_analysis_router)
    return app


app = create_app()
