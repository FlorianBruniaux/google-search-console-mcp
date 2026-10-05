import json
from datetime import date, timedelta

import pytest

from gsc_mcp.tools import bing_webmaster
from gsc_mcp.url_safety import URLSafetyError


SITE = "https://example.com/"
SITE_ROW = {
    "AuthenticationCode": "never-return-this",
    "DnsVerificationCode": "never-return-this-either",
    "IsVerified": True,
    "Url": "https://example.com",
}
CRAWL_ROW = {
    "Date": "/Date(1788566400000+0000)/",
    "CrawledPages": 100,
    "CrawlErrors": 3,
    "InIndex": 90,
    "InLinks": 250,
    "Code2xx": 95,
    "Code301": 2,
    "Code302": 1,
    "Code4xx": 2,
    "Code5xx": 0,
    "BlockedByRobotsTxt": 1,
    "DnsFailures": 0,
    "ConnectionTimeout": 0,
    "ContainsMalware": 0,
    "AllOtherCodes": 0,
}


def _use_client(monkeypatch, mock_bing_client, response):
    mock_bing_client.read.return_value = response
    monkeypatch.setattr(
        bing_webmaster, "get_bing_client", lambda: mock_bing_client
    )


def test_bing_sites_list_returns_only_public_site_fields(
    monkeypatch, mock_bing_client
):
    _use_client(monkeypatch, mock_bing_client, [SITE_ROW])

    result = json.loads(bing_webmaster.bing_sites_list())

    assert result["sites"] == [{"url": "https://example.com", "verified": True}]
    assert result["count"] == 1
    assert "never-return-this" not in json.dumps(result)
    assert "AuthenticationCode" not in json.dumps(result)
    assert "DnsVerificationCode" not in json.dumps(result)
    mock_bing_client.read.assert_called_once_with("GetUserSites", {})


def test_bing_crawl_stats_filters_window_and_normalizes_integer_counts(
    monkeypatch, mock_bing_client
):
    today = date.today()
    in_window = today.isoformat()
    window_start = (today - timedelta(days=1)).isoformat()
    out_of_window = (today - timedelta(days=2)).isoformat()
    raw_counts = {key: str(value) for key, value in CRAWL_ROW.items() if key != "Date"}
    _use_client(
        monkeypatch,
        mock_bing_client,
        [
            {**raw_counts, "Date": out_of_window, "CrawledPages": "999"},
            {**raw_counts, "Date": in_window},
        ],
    )

    result = json.loads(bing_webmaster.bing_crawl_stats(SITE, days=2))

    assert result["rows"] == [
        {
            "date": in_window,
            "crawled_pages": 100,
            "crawl_errors": 3,
            "in_index": 90,
            "in_links": 250,
            "code_2xx": 95,
            "code_301": 2,
            "code_302": 1,
            "code_4xx": 2,
            "code_5xx": 0,
            "blocked_by_robots_txt": 1,
            "dns_failures": 0,
            "connection_timeout": 0,
            "contains_malware": 0,
            "all_other_codes": 0,
        }
    ]
    assert all(
        isinstance(value, int)
        for key, value in result["rows"][0].items()
        if key != "date"
    )
    assert result["_meta"]["requested_window"] == {
        "start": window_start,
        "end": in_window,
        "days": 2,
    }
    assert result["_meta"]["observed_window"] == {
        "start": in_window,
        "end": in_window,
    }
    mock_bing_client.read.assert_called_once_with(
        "GetCrawlStats", {"siteUrl": SITE}
    )


def test_bing_crawl_issues_decodes_all_known_flags_and_preserves_unknown_bits(
    monkeypatch, mock_bing_client
):
    all_known_flags = 1 | 2 | 4 | 8 | 16 | 32 | 64 | 128 | 256
    unknown_flag = 512
    _use_client(
        monkeypatch,
        mock_bing_client,
        [
            {
                "Url": "https://example.com/problem",
                "Issues": all_known_flags | unknown_flag,
                "AuthenticationCode": "never-return-this",
            }
        ],
    )

    result = json.loads(bing_webmaster.bing_crawl_issues(SITE, limit=1))

    assert result["issues"] == [
        {
            "url": "https://example.com/problem",
            "issue_types": [
                "code_301",
                "code_302",
                "code_4xx",
                "code_5xx",
                "blocked_by_robots_txt",
                "contains_malware",
                "important_url_blocked_by_robots_txt",
                "dns_errors",
                "timeout_errors",
            ],
            "unknown_issue_bits": 512,
        }
    ]
    assert result["_meta"]["contract_status"] == "UNVERIFIED_RUNTIME"
    assert "never-return-this" not in json.dumps(result)
    mock_bing_client.read.assert_called_once_with(
        "GetCrawlIssues", {"siteUrl": SITE}
    )


def test_bing_crawl_settings_exposes_only_exact_rate_and_marks_partial_contract(
    monkeypatch, mock_bing_client
):
    crawl_rate = [1, 2, 3, 4]
    _use_client(
        monkeypatch,
        mock_bing_client,
        {
            "CrawlRate": crawl_rate,
            "UnknownBoolean": True,
            "AuthenticationCode": "never-return-this",
        },
    )

    result = json.loads(bing_webmaster.bing_crawl_settings_get(SITE))

    assert result["crawl_rate"] == crawl_rate
    assert set(result) == {"site", "crawl_rate", "_meta"}
    assert result["_meta"]["contract_status"] == "PARTIAL"
    assert "never-return-this" not in json.dumps(result)
    mock_bing_client.read.assert_called_once_with(
        "GetCrawlSettings", {"siteUrl": SITE}
    )


def test_bing_url_info_exposes_only_observed_fields_without_index_verdict(
    monkeypatch, mock_bing_client
):
    page_url = "https://example.com/page"
    _use_client(
        monkeypatch,
        mock_bing_client,
        {
            "AnchorCount": "12",
            "DiscoveryDate": "/Date(1788566400000+0000)/",
            "DocumentSize": "4096",
            "HttpStatus": "200",
            "IsPage": True,
            "LastCrawledDate": "2026-09-06T12:00:00Z",
            "TotalChildUrlCount": "7",
            "Url": page_url,
            "InIndex": True,
            "AuthenticationCode": "never-return-this",
        },
    )

    result = json.loads(bing_webmaster.bing_url_info(SITE, page_url))

    assert {key for key in result if key != "_meta"} == {
        "anchor_count",
        "discovery_date",
        "document_size",
        "http_status",
        "is_page",
        "last_crawled_date",
        "total_child_url_count",
        "url",
    }
    assert result["anchor_count"] == 12
    assert result["discovery_date"] == "2026-09-05"
    assert result["last_crawled_date"] == "2026-09-06"
    assert "indexed" not in json.dumps(result).lower()
    assert "never-return-this" not in json.dumps(result)
    mock_bing_client.read.assert_called_once_with(
        "GetUrlInfo", {"siteUrl": SITE, "url": page_url}
    )


def test_bing_url_traffic_derives_ctr_without_position(
    monkeypatch, mock_bing_client
):
    page_url = "https://example.com/page"
    _use_client(
        monkeypatch,
        mock_bing_client,
        {
            "Clicks": "5",
            "Impressions": "20",
            "IsPage": True,
            "Url": page_url,
        },
    )

    result = json.loads(bing_webmaster.bing_url_traffic(SITE, page_url))

    assert {key for key in result if key != "_meta"} == {
        "clicks",
        "impressions",
        "ctr",
        "is_page",
        "url",
    }
    assert result["ctr"] == 0.25
    assert "position" not in json.dumps(result)
    assert result["_meta"]["metrics"] == {
        "measured": ["clicks", "impressions"],
        "derived": ["ctr"],
    }
    mock_bing_client.read.assert_called_once_with(
        "GetUrlTrafficInfo", {"siteUrl": SITE, "url": page_url}
    )


@pytest.mark.parametrize("tool_name", ["bing_feeds_list", "bing_feed_details"])
def test_bing_feed_tools_normalize_lists_without_indexed_count(
    monkeypatch, mock_bing_client, tool_name
):
    feed_url = "https://example.com/sitemap.xml"
    _use_client(
        monkeypatch,
        mock_bing_client,
        [
            {
                "Compressed": False,
                "FileSize": "1024",
                "LastCrawled": "/Date(1788566400000+0000)/",
                "Status": "Success",
                "Submitted": "2026-09-04T00:00:00Z",
                "Type": "Sitemap",
                "Url": feed_url,
                "UrlCount": "20",
                "IndexedCount": 19,
                "DnsVerificationCode": "never-return-this-either",
            }
        ],
    )

    tool = getattr(bing_webmaster, tool_name)
    result = json.loads(tool(SITE, feed_url) if tool_name.endswith("details") else tool(SITE))

    assert result["feeds"] == [
        {
            "compressed": False,
            "file_size": 1024,
            "last_crawled": "2026-09-05",
            "status": "Success",
            "submitted": "2026-09-04",
            "type": "Sitemap",
            "url": feed_url,
            "url_count": 20,
        }
    ]
    assert "indexed_count" not in json.dumps(result)
    assert "never-return-this" not in json.dumps(result)
    expected = (
        ("GetFeedDetails", {"siteUrl": SITE, "feedUrl": feed_url})
        if tool_name.endswith("details")
        else ("GetFeeds", {"siteUrl": SITE})
    )
    mock_bing_client.read.assert_called_once_with(*expected)


def test_bing_feed_details_accepts_an_empty_list(monkeypatch, mock_bing_client):
    _use_client(monkeypatch, mock_bing_client, [])

    result = json.loads(
        bing_webmaster.bing_feed_details(SITE, "https://example.com/sitemap.xml")
    )

    assert result["feeds"] == []
    assert result["count"] == 0


def test_bing_url_submission_quota_keeps_semantics_unknown(
    monkeypatch, mock_bing_client
):
    _use_client(
        monkeypatch,
        mock_bing_client,
        {
            "DailyQuota": "100",
            "MonthlyQuota": "1000",
            "AuthenticationCode": "never-return-this",
        },
    )

    result = json.loads(bing_webmaster.bing_url_submission_quota(SITE))

    assert result["daily_quota"] == 100
    assert result["monthly_quota"] == 1000
    assert result["_meta"]["quota_semantics"] == "unknown_total_or_remaining"
    assert "never-return-this" not in json.dumps(result)
    mock_bing_client.read.assert_called_once_with(
        "GetUrlSubmissionQuota", {"siteUrl": SITE}
    )


@pytest.mark.parametrize("days", [0, -1, True, 1.5])
def test_bing_crawl_stats_rejects_invalid_days(days):
    with pytest.raises(ValueError, match="days must be at least 1"):
        bing_webmaster.bing_crawl_stats(SITE, days=days)


@pytest.mark.parametrize("limit", [0, 10_001, True, 1.5])
def test_bing_crawl_issues_rejects_invalid_limit(limit):
    with pytest.raises(ValueError, match="limit must be between 1 and 10000"):
        bing_webmaster.bing_crawl_issues(SITE, limit=limit)


def _allow_safe_urls(monkeypatch):
    strict_calls = []
    origin_calls = []

    def validate_strict(url):
        strict_calls.append(url)
        return url, "93.184.216.34"

    def validate_origin(site, candidate):
        origin_calls.append((site, candidate))

    monkeypatch.setattr(bing_webmaster, "validate_url_strict", validate_strict)
    monkeypatch.setattr(bing_webmaster, "validate_same_origin", validate_origin)
    return strict_calls, origin_calls


def test_bing_url_submit_validates_before_exact_write_and_marks_indexing_unverified(
    monkeypatch, mock_bing_client
):
    page_url = "https://example.com/page"
    strict_calls, origin_calls = _allow_safe_urls(monkeypatch)
    monkeypatch.setattr(
        bing_webmaster, "get_bing_client", lambda: mock_bing_client
    )

    result = json.loads(bing_webmaster.bing_url_submit(SITE, page_url))

    assert strict_calls == [page_url]
    assert origin_calls == [(SITE, page_url)]
    mock_bing_client.write.assert_called_once_with(
        "SubmitUrl", {"siteUrl": SITE, "url": page_url}
    )
    assert {key for key in result if key != "_meta"} == {
        "engine",
        "site",
        "status",
        "indexed",
    }
    assert result == {
        "engine": "bing",
        "site": SITE,
        "status": "accepted",
        "indexed": False,
        "_meta": {
            "tool": "bing_url_submit",
            "params": {"site": SITE, "url": page_url},
            "engine": "bing",
            "indexed_semantics": "not_verified",
        },
    }


def test_bing_url_submit_rejects_unsafe_url_before_client_lookup(
    monkeypatch, mock_bing_client
):
    def reject(_url):
        raise URLSafetyError("blocked")

    get_client = lambda: mock_bing_client
    monkeypatch.setattr(bing_webmaster, "validate_url_strict", reject)
    monkeypatch.setattr(bing_webmaster, "get_bing_client", get_client)

    with pytest.raises(URLSafetyError, match="blocked"):
        bing_webmaster.bing_url_submit(SITE, "https://example.com/private")

    mock_bing_client.write.assert_not_called()


def test_bing_url_submit_rejects_cross_origin_before_write(
    monkeypatch, mock_bing_client
):
    monkeypatch.setattr(
        bing_webmaster,
        "validate_url_strict",
        lambda url: (url, "93.184.216.34"),
    )
    monkeypatch.setattr(
        bing_webmaster, "get_bing_client", lambda: mock_bing_client
    )

    with pytest.raises(URLSafetyError, match="outside"):
        bing_webmaster.bing_url_submit(SITE, "https://other.example/page")

    mock_bing_client.write.assert_not_called()


@pytest.mark.parametrize("urls", [[], ["https://example.com/a"] * 501])
def test_bing_urls_submit_batch_rejects_outside_1_to_500_before_client(
    monkeypatch, mock_bing_client, urls
):
    monkeypatch.setattr(
        bing_webmaster, "get_bing_client", lambda: mock_bing_client
    )

    with pytest.raises(ValueError, match="between 1 and 500"):
        bing_webmaster.bing_urls_submit_batch(SITE, urls)

    mock_bing_client.read.assert_not_called()
    mock_bing_client.write.assert_not_called()


def test_bing_urls_submit_batch_validates_every_url_before_client_lookup(
    monkeypatch, mock_bing_client
):
    urls = [
        "https://example.com/valid",
        "https://example.com/blocked",
        "https://example.com/never-reached",
    ]
    validated = []

    def validate(url):
        validated.append(url)
        if url.endswith("blocked"):
            raise URLSafetyError("blocked")
        return url, "93.184.216.34"

    monkeypatch.setattr(bing_webmaster, "validate_url_strict", validate)
    monkeypatch.setattr(
        bing_webmaster, "get_bing_client", lambda: mock_bing_client
    )

    with pytest.raises(URLSafetyError, match="blocked"):
        bing_webmaster.bing_urls_submit_batch(SITE, urls)

    assert validated == urls[:2]
    mock_bing_client.read.assert_not_called()
    mock_bing_client.write.assert_not_called()


def test_bing_urls_submit_batch_refuses_unknown_quota_semantics_after_preflight(
    monkeypatch, mock_bing_client
):
    urls = ["https://example.com/a", "https://example.com/b"]
    strict_calls, origin_calls = _allow_safe_urls(monkeypatch)
    mock_bing_client.read.return_value = {
        "DailyQuota": "100",
        "MonthlyQuota": "1000",
        "AuthenticationCode": "never-return-this",
    }
    monkeypatch.setattr(
        bing_webmaster, "get_bing_client", lambda: mock_bing_client
    )

    result = json.loads(bing_webmaster.bing_urls_submit_batch(SITE, urls))

    assert strict_calls == urls
    assert origin_calls == [(SITE, url) for url in urls]
    mock_bing_client.read.assert_called_once_with(
        "GetUrlSubmissionQuota", {"siteUrl": SITE}
    )
    mock_bing_client.write.assert_not_called()
    assert result["status"] == "refused"
    assert result["error_category"] == "bing_quota_semantics_unverified"
    assert result["submitted_count"] == 0
    assert result["daily_quota_before"] == 100
    assert result["monthly_quota_before"] == 1000
    assert "never-return-this" not in json.dumps(result)


@pytest.mark.parametrize(
    ("daily", "monthly"),
    [(1, 1000), (100, 1)],
)
def test_bing_urls_submit_batch_rejects_exceeding_confirmed_remaining_quota(
    monkeypatch, mock_bing_client, daily, monthly
):
    urls = ["https://example.com/a", "https://example.com/b"]
    _allow_safe_urls(monkeypatch)
    mock_bing_client.read.return_value = {
        "DailyQuota": daily,
        "MonthlyQuota": monthly,
    }
    monkeypatch.setattr(bing_webmaster, "_BING_QUOTA_SEMANTICS", "remaining")
    monkeypatch.setattr(
        bing_webmaster, "get_bing_client", lambda: mock_bing_client
    )

    result = json.loads(bing_webmaster.bing_urls_submit_batch(SITE, urls))

    assert result["status"] == "refused"
    assert result["error_category"] == "bing_quota_exceeded"
    assert result["submitted_count"] == 0
    mock_bing_client.write.assert_not_called()


def test_bing_urls_submit_batch_uses_exact_payload_when_remaining_quota_is_confirmed(
    monkeypatch, mock_bing_client
):
    urls = ["https://example.com/a", "https://example.com/b"]
    _allow_safe_urls(monkeypatch)
    mock_bing_client.read.return_value = {
        "DailyQuota": "2",
        "MonthlyQuota": "20",
    }
    monkeypatch.setattr(bing_webmaster, "_BING_QUOTA_SEMANTICS", "remaining")
    monkeypatch.setattr(
        bing_webmaster, "get_bing_client", lambda: mock_bing_client
    )

    result = json.loads(bing_webmaster.bing_urls_submit_batch(SITE, urls))

    mock_bing_client.read.assert_called_once_with(
        "GetUrlSubmissionQuota", {"siteUrl": SITE}
    )
    mock_bing_client.write.assert_called_once_with(
        "SubmitUrlBatch", {"siteUrl": SITE, "urlList": urls}
    )
    assert result["engine"] == "bing"
    assert result["status"] == "accepted"
    assert result["indexed"] is False
    assert result["submitted_count"] == 2
    assert result["daily_quota_before"] == 2
    assert result["monthly_quota_before"] == 20


def test_bing_feed_submit_validates_before_exact_write(
    monkeypatch, mock_bing_client
):
    feed_url = "https://example.com/sitemap.xml"
    strict_calls, origin_calls = _allow_safe_urls(monkeypatch)
    monkeypatch.setattr(
        bing_webmaster, "get_bing_client", lambda: mock_bing_client
    )

    result = json.loads(bing_webmaster.bing_feed_submit(SITE, feed_url))

    assert strict_calls == [feed_url]
    assert origin_calls == [(SITE, feed_url)]
    mock_bing_client.write.assert_called_once_with(
        "SubmitFeed", {"siteUrl": SITE, "feedUrl": feed_url}
    )
    assert result["status"] == "accepted"
    assert result["indexed"] is False
    assert result["_meta"]["indexed_semantics"] == "not_verified"


def test_bing_feed_submit_rejects_unsafe_or_cross_origin_before_write(
    monkeypatch, mock_bing_client
):
    monkeypatch.setattr(
        bing_webmaster,
        "validate_url_strict",
        lambda url: (url, "93.184.216.34"),
    )
    monkeypatch.setattr(
        bing_webmaster, "get_bing_client", lambda: mock_bing_client
    )

    with pytest.raises(URLSafetyError, match="outside"):
        bing_webmaster.bing_feed_submit(
            SITE, "https://other.example/sitemap.xml"
        )

    mock_bing_client.write.assert_not_called()


@pytest.mark.parametrize("confirm", [1, "true", None])
def test_bing_feed_remove_requires_a_boolean_confirmation(confirm):
    with pytest.raises(ValueError, match="confirm must be a boolean"):
        bing_webmaster.bing_feed_remove(
            SITE, "https://example.com/sitemap.xml", confirm=confirm
        )


def test_bing_feed_remove_requires_confirmation_without_bing_call(
    monkeypatch, mock_bing_client
):
    monkeypatch.setattr(
        bing_webmaster, "get_bing_client", lambda: mock_bing_client
    )

    result = json.loads(
        bing_webmaster.bing_feed_remove(
            SITE, "https://example.com/sitemap.xml"
        )
    )

    assert result["status"] == "confirmation_required"
    assert result["removed"] is False
    assert result["_meta"]["contract_status"] == "UNVERIFIED_RUNTIME"
    mock_bing_client.read.assert_not_called()
    mock_bing_client.write.assert_not_called()


@pytest.mark.parametrize(
    "feed_url",
    [
        "https://example.com/feed.json",
        "https://example.com/feed.xml.json",
    ],
)
def test_bing_feed_remove_rejects_non_feed_shape_before_bing_call(
    monkeypatch, mock_bing_client, feed_url
):
    strict_calls, origin_calls = _allow_safe_urls(monkeypatch)
    monkeypatch.setattr(
        bing_webmaster, "get_bing_client", lambda: mock_bing_client
    )

    with pytest.raises(ValueError, match="XML, TXT, or sitemap"):
        bing_webmaster.bing_feed_remove(SITE, feed_url, confirm=True)

    assert strict_calls == [feed_url]
    assert origin_calls == [(SITE, feed_url)]
    mock_bing_client.read.assert_not_called()
    mock_bing_client.write.assert_not_called()


@pytest.mark.parametrize(
    "feed_url",
    [
        "https://example.com/feed.xml",
        "https://example.com/feed.txt",
        "https://example.com/sitemaps/feed",
    ],
)
def test_bing_feed_remove_checks_registration_before_exact_write(
    monkeypatch, mock_bing_client, feed_url
):
    _allow_safe_urls(monkeypatch)
    mock_bing_client.read.return_value = [
        {"Url": feed_url, "AuthenticationCode": "never-return-this"}
    ]
    monkeypatch.setattr(
        bing_webmaster, "get_bing_client", lambda: mock_bing_client
    )

    result = json.loads(
        bing_webmaster.bing_feed_remove(SITE, feed_url, confirm=True)
    )

    mock_bing_client.read.assert_called_once_with(
        "GetFeeds", {"siteUrl": SITE}
    )
    mock_bing_client.write.assert_called_once_with(
        "RemoveFeed", {"siteUrl": SITE, "feedUrl": feed_url}
    )
    assert result["status"] == "accepted"
    assert result["removed"] is True
    assert result["_meta"]["contract_status"] == "UNVERIFIED_RUNTIME"
    assert "never-return-this" not in json.dumps(result)


def test_bing_feed_remove_refuses_unregistered_feed_without_write(
    monkeypatch, mock_bing_client
):
    feed_url = "https://example.com/sitemap.xml"
    _allow_safe_urls(monkeypatch)
    mock_bing_client.read.return_value = [
        {"Url": "https://example.com/other-sitemap.xml"}
    ]
    monkeypatch.setattr(
        bing_webmaster, "get_bing_client", lambda: mock_bing_client
    )

    result = json.loads(
        bing_webmaster.bing_feed_remove(SITE, feed_url, confirm=True)
    )

    assert result["status"] == "refused"
    assert result["error_category"] == "feed_not_registered"
    assert result["removed"] is False
    mock_bing_client.write.assert_not_called()
