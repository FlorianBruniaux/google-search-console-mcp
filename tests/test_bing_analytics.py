import json
from datetime import date, timedelta

import pytest

from gsc_mcp.tools import bing_analytics


QUERY_ROW = {
    "AvgClickPosition": 18,
    "AvgImpressionPosition": 17,
    "Clicks": 15,
    "Date": "/Date(1788566400000+0000)/",
    "Impressions": 100,
    "Query": "example query",
}


def _use_client(monkeypatch, mock_bing_client, rows):
    mock_bing_client.read.return_value = rows
    monkeypatch.setattr(bing_analytics, "get_bing_client", lambda: mock_bing_client)


def test_bing_query_stats_normalizes_positions_ctr_and_metric_nature(
    monkeypatch, mock_bing_client
):
    zero_impressions = {
        **QUERY_ROW,
        "Clicks": 3,
        "Impressions": 0,
        "Query": "zero impressions",
    }
    lower_impressions = {
        **QUERY_ROW,
        "Clicks": 2,
        "Impressions": 20,
        "Query": "lower impressions",
    }
    _use_client(
        monkeypatch,
        mock_bing_client,
        [zero_impressions, lower_impressions, QUERY_ROW],
    )

    result = json.loads(
        bing_analytics.bing_query_stats(
            "https://example.com/", days=10_000, limit=3
        )
    )

    assert [row["query"] for row in result["rows"]] == [
        "example query",
        "lower impressions",
        "zero impressions",
    ]
    assert result["rows"][0] == {
        "query": "example query",
        "date": "2026-09-05",
        "clicks": 15,
        "impressions": 100,
        "ctr": 0.15,
        "position": 17.0,
        "avg_click_position": 18.0,
        "avg_impression_position": 17.0,
    }
    assert result["rows"][2]["ctr"] == 0.0
    assert result["_meta"]["engine"] == "bing"
    assert result["_meta"]["position_semantics"] == {
        "position": "average_impression_position",
        "avg_click_position": "average_click_position",
        "avg_impression_position": "average_impression_position",
    }
    assert result["_meta"]["metrics"] == {
        "measured": [
            "clicks",
            "impressions",
            "position",
            "avg_click_position",
            "avg_impression_position",
        ],
        "derived": ["ctr"],
    }
    mock_bing_client.read.assert_called_once_with(
        "GetQueryStats", {"siteUrl": "https://example.com/"}
    )


def test_bing_page_stats_renames_query_filters_then_limits_and_reports_windows(
    monkeypatch, mock_bing_client
):
    today = date.today()
    in_window = (today - timedelta(days=1)).isoformat()
    window_start = (today - timedelta(days=2)).isoformat()
    out_of_window = (today - timedelta(days=3)).isoformat()
    rows = [
        {
            **QUERY_ROW,
            "Query": "https://example.com/old",
            "Date": out_of_window,
            "Impressions": 1000,
            "__type": "PageStats:#Microsoft.Bing.Webmaster.Api",
        },
        {
            **QUERY_ROW,
            "Query": "https://example.com/kept",
            "Date": in_window,
            "Impressions": 50,
            "__type": "PageStats:#Microsoft.Bing.Webmaster.Api",
        },
        {
            **QUERY_ROW,
            "Query": "https://example.com/limited",
            "Date": window_start,
            "Impressions": 10,
        },
    ]
    _use_client(monkeypatch, mock_bing_client, rows)

    result = json.loads(
        bing_analytics.bing_page_stats("https://example.com/", days=3, limit=1)
    )

    assert result["rows"][0]["page"] == "https://example.com/kept"
    assert "query" not in result["rows"][0]
    assert "__type" not in json.dumps(result)
    assert result["count"] == 1
    assert result["_meta"]["requested_window"] == {
        "start": window_start,
        "end": today.isoformat(),
        "days": 3,
    }
    assert result["_meta"]["observed_window"] == {
        "start": window_start,
        "end": in_window,
    }
    mock_bing_client.read.assert_called_once_with(
        "GetPageStats", {"siteUrl": "https://example.com/"}
    )


def test_bing_page_query_stats_scopes_rows_to_requested_page(
    monkeypatch, mock_bing_client
):
    today = date.today().isoformat()
    _use_client(
        monkeypatch,
        mock_bing_client,
        [{**QUERY_ROW, "Date": today, "Query": "page query"}],
    )

    result = json.loads(
        bing_analytics.bing_page_query_stats(
            "https://example.com/",
            "https://example.com/page",
            days=1,
            limit=10,
        )
    )

    assert result["page"] == "https://example.com/page"
    assert result["rows"][0]["query"] == "page query"
    mock_bing_client.read.assert_called_once_with(
        "GetPageQueryStats",
        {
            "siteUrl": "https://example.com/",
            "page": "https://example.com/page",
        },
    )


def test_bing_rank_traffic_stats_exposes_only_observed_metrics_and_derived_ctr(
    monkeypatch, mock_bing_client
):
    today = date.today()
    earlier = (today - timedelta(days=1)).isoformat()
    later = today.isoformat()
    _use_client(
        monkeypatch,
        mock_bing_client,
        [
            {"Date": later, "Clicks": 1, "Impressions": 4},
            {"Date": earlier, "Clicks": 2, "Impressions": 10},
        ],
    )

    result = json.loads(
        bing_analytics.bing_rank_traffic_stats("https://example.com/", days=2)
    )

    assert result["rows"] == [
        {"date": earlier, "clicks": 2, "impressions": 10, "ctr": 0.2},
        {"date": later, "clicks": 1, "impressions": 4, "ctr": 0.25},
    ]
    assert result["_meta"]["position_semantics"] == "unavailable"
    assert result["_meta"]["metrics"] == {
        "measured": ["clicks", "impressions"],
        "derived": ["ctr"],
    }
    assert all("position" not in row for row in result["rows"])
    mock_bing_client.read.assert_called_once_with(
        "GetRankAndTrafficStats", {"siteUrl": "https://example.com/"}
    )


def test_bing_query_stats_accepts_an_empty_response(monkeypatch, mock_bing_client):
    _use_client(monkeypatch, mock_bing_client, [])

    result = json.loads(bing_analytics.bing_query_stats("https://example.com/"))

    assert result["rows"] == []
    assert result["count"] == 0
    assert result["_meta"]["observed_window"] == {
        "start": None,
        "end": None,
    }


@pytest.mark.parametrize("limit", [0, 10_001])
def test_bing_query_stats_rejects_limit_outside_supported_range(limit):
    with pytest.raises(ValueError, match="limit must be between 1 and 10000"):
        bing_analytics.bing_query_stats("https://example.com/", limit=limit)


@pytest.mark.parametrize("days", [0, -1])
def test_bing_query_stats_rejects_non_positive_days(days):
    with pytest.raises(ValueError, match="days must be at least 1"):
        bing_analytics.bing_query_stats("https://example.com/", days=days)


def test_bing_link_counts_normalizes_nested_links_without_private_fields(
    monkeypatch, mock_bing_client
):
    _use_client(
        monkeypatch,
        mock_bing_client,
        {
            "Links": [
                {
                    "Url": "https://source.example/one",
                    "Count": 7,
                    "AuthenticationCode": "never-return-this",
                },
                {"Url": "https://source.example/two", "Count": "3"},
                "ignore malformed element",
            ],
            "TotalPages": "4",
            "DnsVerificationCode": "never-return-this-either",
        },
    )

    result = json.loads(
        bing_analytics.bing_link_counts("https://example.com/", page=2)
    )

    assert result["_meta"].pop("evidence") == {"version": 1, "fields": {}}
    assert result == {
        "site": "https://example.com/",
        "page": 2,
        "links": [
            {"url": "https://source.example/one", "count": 7},
            {"url": "https://source.example/two", "count": 3},
        ],
        "total_pages": 4,
        "_meta": {
            "tool": "bing_link_counts",
            "params": {"site": "https://example.com/", "page": 2},
            "engine": "bing",
            "contract_status": "UNVERIFIED_RUNTIME",
        },
    }
    assert "never-return-this" not in json.dumps(result)
    mock_bing_client.read.assert_called_once_with(
        "GetLinkCounts", {"siteUrl": "https://example.com/", "page": 2}
    )


def test_bing_url_links_normalizes_details_and_translates_url_to_link(
    monkeypatch, mock_bing_client
):
    target_url = "https://example.com/target"
    _use_client(
        monkeypatch,
        mock_bing_client,
        {
            "Details": [
                {
                    "Url": "https://source.example/article",
                    "AnchorText": "useful anchor",
                },
                {"Url": "https://source.example/plain", "AnchorText": None},
                None,
            ],
            "TotalPages": 1,
        },
    )

    result = json.loads(
        bing_analytics.bing_url_links(
            "https://example.com/", target_url, page=0
        )
    )

    assert result["details"] == [
        {
            "url": "https://source.example/article",
            "anchor_text": "useful anchor",
        },
        {"url": "https://source.example/plain", "anchor_text": None},
    ]
    assert result["total_pages"] == 1
    assert result["_meta"]["contract_status"] == "UNVERIFIED_RUNTIME"
    mock_bing_client.read.assert_called_once_with(
        "GetUrlLinks",
        {
            "siteUrl": "https://example.com/",
            "link": target_url,
            "page": 0,
        },
    )
    assert "url" not in mock_bing_client.read.call_args.args[1]


@pytest.mark.parametrize("page", [-1, 32_768, True, 1.5])
@pytest.mark.parametrize("tool_name", ["bing_link_counts", "bing_url_links"])
def test_bing_backlink_tools_reject_pages_outside_int16_range(page, tool_name):
    tool = getattr(bing_analytics, tool_name)
    args = ("https://example.com/",)
    if tool_name == "bing_url_links":
        args += ("https://example.com/target",)

    with pytest.raises(ValueError, match="page must be between 0 and 32767"):
        tool(*args, page=page)


@pytest.mark.parametrize(
    ("tool_name", "response_key", "result_key"),
    [
        ("bing_link_counts", "Links", "links"),
        ("bing_url_links", "Details", "details"),
    ],
)
def test_bing_backlink_tools_accept_empty_page(
    monkeypatch,
    mock_bing_client,
    tool_name,
    response_key,
    result_key,
):
    _use_client(
        monkeypatch,
        mock_bing_client,
        {response_key: [], "TotalPages": 0},
    )
    tool = getattr(bing_analytics, tool_name)
    args = ("https://example.com/",)
    if tool_name == "bing_url_links":
        args += ("https://example.com/target",)

    result = json.loads(tool(*args, page=0))

    assert result[result_key] == []
    assert result["total_pages"] == 0
