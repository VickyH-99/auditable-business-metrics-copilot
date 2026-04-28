from __future__ import annotations

import json
from pathlib import Path

from app.schemas.api import MetricCatalogResponse, MetricDefinition


class MetricCatalog:
    def __init__(self, definitions: list[MetricDefinition]) -> None:
        self.definitions = definitions
        self._by_id = {metric.metric_id: metric for metric in definitions}

    def get(self, metric_id: str) -> MetricDefinition:
        if metric_id not in self._by_id:
            raise KeyError(f"Unknown metric: {metric_id}")
        return self._by_id[metric_id]

    def exists(self, metric_id: str) -> bool:
        return metric_id in self._by_id

    def to_response(self) -> MetricCatalogResponse:
        return MetricCatalogResponse(metrics=self.definitions)

    def option_names(self) -> list[str]:
        return [metric.name_zh for metric in self.definitions]


def load_metric_catalog() -> MetricCatalog:
    catalog_path = Path(__file__).with_name("catalog.json")
    payload = json.loads(catalog_path.read_text(encoding="utf-8"))
    definitions = [MetricDefinition.model_validate(item) for item in payload["metrics"]]
    return MetricCatalog(definitions)

