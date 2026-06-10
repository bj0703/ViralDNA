from __future__ import annotations

import logging
logging.basicConfig(
    level=logging.INFO,
    format="[%(levelname)s] %(name)s: %(message)s",
)
for logger_name in ["CapCutDraftGeneratorService", "CapCutDraftBackgroundTask", "GapResolverAgent", "EditPlannerAgent"]:
    logging.getLogger(logger_name).setLevel(logging.INFO)

from fastapi import FastAPI
from backend.app.api.routes.sample_analysis import router as sample_analysis_router
from backend.app.api.routes.system import router as system_router
from backend.app.api.routes.orchestration import router as orchestration_router


def create_app() -> FastAPI:
    app = FastAPI(
        title="爆款结构迁移引擎 - Agent 动态编排版",
        version="0.2.0",
        description="共享工作记忆 + 动态 Agent 编排系统",
    )
    app.include_router(system_router)
    app.include_router(sample_analysis_router)
    app.include_router(orchestration_router)
    return app


app = create_app()
