"""Normalized search metric contracts shared by search providers."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from types import MappingProxyType
from typing import Literal, Protocol


SearchEngine = Literal["google", "bing"]


class UnsupportedProviderFeature(ValueError):
    """Raised when a provider cannot supply a requested metric dimension."""


def _freeze_metric_value(value: object) -> object:
    if isinstance(value, Mapping):
        return MappingProxyType(
            {key: _freeze_metric_value(child) for key, child in value.items()}
        )
    if isinstance(value, (list, tuple)):
        return tuple(_freeze_metric_value(child) for child in value)
    if isinstance(value, (set, frozenset)):
        return frozenset(_freeze_metric_value(child) for child in value)
    return value


def _json_metric_value(value: object) -> object:
    if isinstance(value, Mapping):
        return {key: _json_metric_value(child) for key, child in value.items()}
    if isinstance(value, (tuple, frozenset)):
        return [_json_metric_value(child) for child in value]
    return value


@dataclass(frozen=True)
class SearchMetricRow:
    engine: SearchEngine
    date: str | None
    query: str | None
    page: str | None
    clicks: int
    impressions: int
    ctr: float
    position: float | None
    provider_metrics: Mapping[str, object] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.engine not in ("google", "bing"):
            raise ValueError("engine must be google or bing")
        if self.clicks < 0:
            raise ValueError("clicks must not be negative")
        if self.impressions < 0:
            raise ValueError("impressions must not be negative")
        if not 0 <= self.ctr <= 1:
            raise ValueError("ctr must be between 0 and 1")
        object.__setattr__(
            self,
            "provider_metrics",
            _freeze_metric_value(self.provider_metrics),
        )

    def to_dict(self) -> dict[str, object]:
        return {
            "engine": self.engine,
            "date": self.date,
            "query": self.query,
            "page": self.page,
            "clicks": self.clicks,
            "impressions": self.impressions,
            "ctr": self.ctr,
            "position": self.position,
            "provider_metrics": _json_metric_value(self.provider_metrics),
        }


@dataclass(frozen=True)
class SearchMetricBatch:
    engine: SearchEngine
    dimensions: tuple[str, ...]
    rows: tuple[SearchMetricRow, ...]
    requested_start: str
    requested_end: str
    observed_start: str | None
    observed_end: str | None
    window_exact: bool
    position_semantics: str

    def __post_init__(self) -> None:
        if self.engine not in ("google", "bing"):
            raise ValueError("engine must be google or bing")

    def to_dict(self) -> dict[str, object]:
        return {
            "engine": self.engine,
            "dimensions": list(self.dimensions),
            "rows": [row.to_dict() for row in self.rows],
            "requested_start": self.requested_start,
            "requested_end": self.requested_end,
            "observed_start": self.observed_start,
            "observed_end": self.observed_end,
            "window_exact": self.window_exact,
            "position_semantics": self.position_semantics,
        }


class SearchMetricsProvider(Protocol):
    def fetch(
        self,
        site: str,
        start_date: str,
        end_date: str,
        dimensions: tuple[str, ...],
    ) -> SearchMetricBatch:
        """Fetch normalized rows for one provider and dimension set."""
