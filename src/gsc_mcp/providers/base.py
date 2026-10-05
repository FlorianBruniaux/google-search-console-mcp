"""Normalized search metric contracts shared by search providers."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal, Protocol


SearchEngine = Literal["google", "bing"]


class UnsupportedProviderFeature(ValueError):
    """Raised when a provider cannot supply a requested metric dimension."""


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
    provider_metrics: dict[str, object] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.engine not in ("google", "bing"):
            raise ValueError("engine must be google or bing")
        if self.clicks < 0:
            raise ValueError("clicks must not be negative")
        if self.impressions < 0:
            raise ValueError("impressions must not be negative")
        if not 0 <= self.ctr <= 1:
            raise ValueError("ctr must be between 0 and 1")


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


class SearchMetricsProvider(Protocol):
    def fetch(
        self,
        site: str,
        start_date: str,
        end_date: str,
        dimensions: tuple[str, ...],
    ) -> SearchMetricBatch:
        """Fetch normalized rows for one provider and dimension set."""
