from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.agents.copilot_agent import CopilotAgent
from app.api.routes import router
from app.core.config import get_settings
from app.metrics.catalog_loader import load_metric_catalog
from app.services.chat_service import ChatService
from app.services.data_source import DataSourceManager
from app.services.metric_service import MetricService
from app.services.nlu import QueryParser


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    catalog = load_metric_catalog()
    data_source = DataSourceManager(settings)
    data_source.initialize()
    metric_service = MetricService(catalog, data_source, settings)
    parser = QueryParser(settings.today)
    chat_service = ChatService(metric_service, parser)
    app.state.catalog = catalog
    app.state.data_source = data_source
    app.state.metric_service = metric_service
    app.state.agent = CopilotAgent(chat_service, metric_service)
    yield


settings = get_settings()
app = FastAPI(title=settings.app_name, lifespan=lifespan)
local_dev_origins = {
    "http://localhost:5174",
    "http://127.0.0.1:5174",
    "http://0.0.0.0:5174",
    "http://localhost:5173",
    "http://127.0.0.1:5173",
    "http://0.0.0.0:5173",
}
app.add_middleware(
    CORSMiddleware,
    allow_origins=sorted({*settings.cors_origins, *local_dev_origins}),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(router, prefix=settings.api_prefix)
