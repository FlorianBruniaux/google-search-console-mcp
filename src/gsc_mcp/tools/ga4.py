import json

from google.analytics.data_v1beta.types import (
    BatchRunReportsRequest,
    DateRange,
    Dimension,
    Filter,
    FilterExpression,
    Metric,
    RunRealtimeReportRequest,
    RunReportRequest,
)

from gsc_mcp.auth import get_ga4_service, get_ga4_property_id
from gsc_mcp.meta import with_meta


def _f(value: str) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def _i(value: str) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return 0


def _organic_filter() -> FilterExpression:
    return FilterExpression(
        filter=Filter(
            field_name="sessionMedium",
            string_filter=Filter.StringFilter(value="organic"),
        )
    )


def ga4_organic_landing_pages(
    start_date: str = "28daysAgo",
    end_date: str = "today",
    limit: int = 50,
    property_id: str = None,
) -> str:
    prop = get_ga4_property_id(override=property_id)
    client = get_ga4_service()

    request = RunReportRequest(
        property=prop,
        dimensions=[Dimension(name="landingPagePlusQueryString")],
        metrics=[
            Metric(name="sessions"),
            Metric(name="engagedSessions"),
            Metric(name="bounceRate"),
            Metric(name="averageSessionDuration"),
            Metric(name="conversions"),
            Metric(name="totalRevenue"),
        ],
        date_ranges=[DateRange(start_date=start_date, end_date=end_date)],
        dimension_filter=_organic_filter(),
        limit=limit,
    )

    response = client.run_report(request)

    pages = [
        {
            "landing_page": row.dimension_values[0].value,
            "sessions": _i(row.metric_values[0].value),
            "engaged_sessions": _i(row.metric_values[1].value),
            "bounce_rate": _f(row.metric_values[2].value),
            "avg_session_duration": _f(row.metric_values[3].value),
            "conversions": _f(row.metric_values[4].value),
            "total_revenue": _f(row.metric_values[5].value),
        }
        for row in response.rows
    ]

    data = {"start_date": start_date, "end_date": end_date, "count": len(pages), "pages": pages}
    if len(pages) >= limit:
        data["note"] = "Results may be truncated. Set a higher limit or filter by page_path for large properties."
    return json.dumps(with_meta(
        data,
        tool="ga4_organic_landing_pages",
        params={"start_date": start_date, "end_date": end_date, "limit": limit, "property_id": property_id},
    ))


def ga4_traffic_sources(
    start_date: str = "28daysAgo",
    end_date: str = "today",
    property_id: str = None,
) -> str:
    prop = get_ga4_property_id(override=property_id)
    client = get_ga4_service()

    request = RunReportRequest(
        property=prop,
        dimensions=[
            Dimension(name="sessionDefaultChannelGroup"),
            Dimension(name="sessionSource"),
            Dimension(name="sessionMedium"),
        ],
        metrics=[
            Metric(name="sessions"),
            Metric(name="engagedSessions"),
            Metric(name="conversions"),
            Metric(name="totalRevenue"),
        ],
        date_ranges=[DateRange(start_date=start_date, end_date=end_date)],
    )

    response = client.run_report(request)

    sources = [
        {
            "channel_group": row.dimension_values[0].value,
            "source": row.dimension_values[1].value,
            "medium": row.dimension_values[2].value,
            "sessions": _i(row.metric_values[0].value),
            "engaged_sessions": _i(row.metric_values[1].value),
            "conversions": _f(row.metric_values[2].value),
            "total_revenue": _f(row.metric_values[3].value),
        }
        for row in response.rows
    ]

    return json.dumps(with_meta(
        {"start_date": start_date, "end_date": end_date, "count": len(sources), "sources": sources},
        tool="ga4_traffic_sources",
        params={"start_date": start_date, "end_date": end_date, "property_id": property_id},
    ))


def ga4_page_performance(
    start_date: str = "28daysAgo",
    end_date: str = "today",
    page_path: str = None,
    property_id: str = None,
) -> str:
    prop = get_ga4_property_id(override=property_id)
    client = get_ga4_service()

    dimension_filter = None
    if page_path:
        dimension_filter = FilterExpression(
            filter=Filter(
                field_name="pagePath",
                string_filter=Filter.StringFilter(
                    match_type=Filter.StringFilter.MatchType.CONTAINS,
                    value=page_path,
                ),
            )
        )

    request = RunReportRequest(
        property=prop,
        dimensions=[Dimension(name="pagePath")],
        metrics=[
            Metric(name="screenPageViews"),
            Metric(name="activeUsers"),
            Metric(name="averageSessionDuration"),
            Metric(name="engagementRate"),
            Metric(name="bounceRate"),
            Metric(name="conversions"),
            Metric(name="totalRevenue"),
        ],
        date_ranges=[DateRange(start_date=start_date, end_date=end_date)],
        **({"dimension_filter": dimension_filter} if dimension_filter else {}),
    )

    response = client.run_report(request)

    pages = [
        {
            "page_path": row.dimension_values[0].value,
            "page_views": _i(row.metric_values[0].value),
            "active_users": _i(row.metric_values[1].value),
            "avg_session_duration": _f(row.metric_values[2].value),
            "engagement_rate": _f(row.metric_values[3].value),
            "bounce_rate": _f(row.metric_values[4].value),
            "conversions": _f(row.metric_values[5].value),
            "total_revenue": _f(row.metric_values[6].value),
        }
        for row in response.rows
    ]

    return json.dumps(with_meta(
        {"start_date": start_date, "end_date": end_date, "count": len(pages), "pages": pages},
        tool="ga4_page_performance",
        params={"start_date": start_date, "end_date": end_date, "page_path": page_path, "property_id": property_id},
    ))


def ga4_realtime(property_id: str = None) -> str:
    prop = get_ga4_property_id(override=property_id)
    client = get_ga4_service()

    request = RunRealtimeReportRequest(
        property=prop,
        dimensions=[
            Dimension(name="unifiedScreenName"),
            Dimension(name="country"),
            Dimension(name="deviceCategory"),
        ],
        metrics=[Metric(name="activeUsers")],
    )

    response = client.run_realtime_report(request)

    active = [
        {
            "screen_name": row.dimension_values[0].value,
            "country": row.dimension_values[1].value,
            "device_category": row.dimension_values[2].value,
            "active_users": _i(row.metric_values[0].value),
        }
        for row in response.rows
    ]

    return json.dumps(with_meta(
        {"count": len(active), "active": active},
        tool="ga4_realtime",
        params={"property_id": property_id},
    ))


def ga4_user_behavior(
    start_date: str = "28daysAgo",
    end_date: str = "today",
    property_id: str = None,
) -> str:
    prop = get_ga4_property_id(override=property_id)
    client = get_ga4_service()

    date_ranges = [DateRange(start_date=start_date, end_date=end_date)]
    behavior_metrics = [
        Metric(name="sessions"),
        Metric(name="engagementRate"),
    ]

    batch_request = BatchRunReportsRequest(
        property=prop,
        requests=[
            RunReportRequest(
                dimensions=[Dimension(name="deviceCategory")],
                metrics=behavior_metrics,
                date_ranges=date_ranges,
            ),
            RunReportRequest(
                dimensions=[Dimension(name="country")],
                metrics=behavior_metrics,
                date_ranges=date_ranges,
                limit=20,
            ),
            RunReportRequest(
                dimensions=[Dimension(name="newVsReturning")],
                metrics=behavior_metrics,
                date_ranges=date_ranges,
            ),
        ],
    )

    response = client.batch_run_reports(batch_request)

    def _parse_sessions_engagement(rows):
        return [
            {
                "dimension": row.dimension_values[0].value,
                "sessions": _i(row.metric_values[0].value),
                "engagement_rate": _f(row.metric_values[1].value),
            }
            for row in rows
        ]

    by_device = _parse_sessions_engagement(response.reports[0].rows)
    by_country = _parse_sessions_engagement(response.reports[1].rows)
    by_user_type = _parse_sessions_engagement(response.reports[2].rows)

    return json.dumps(with_meta(
        {
            "start_date": start_date,
            "end_date": end_date,
            "by_device": by_device,
            "by_country": by_country,
            "by_user_type": by_user_type,
        },
        tool="ga4_user_behavior",
        params={"start_date": start_date, "end_date": end_date, "property_id": property_id},
    ))


def ga4_conversion_funnel(
    start_date: str = "28daysAgo",
    end_date: str = "today",
    event_name: str = None,
    property_id: str = None,
) -> str:
    prop = get_ga4_property_id(override=property_id)
    client = get_ga4_service()

    date_ranges = [DateRange(start_date=start_date, end_date=end_date)]

    pages_response = client.run_report(
        RunReportRequest(
            property=prop,
            dimensions=[Dimension(name="pagePath")],
            metrics=[Metric(name="conversions")],
            date_ranges=date_ranges,
        )
    )

    converting_pages = [
        {
            "page_path": row.dimension_values[0].value,
            "conversions": _f(row.metric_values[0].value),
        }
        for row in pages_response.rows
        if _f(row.metric_values[0].value) > 0
    ]

    event_filter = None
    if event_name:
        event_filter = FilterExpression(
            filter=Filter(
                field_name="eventName",
                string_filter=Filter.StringFilter(value=event_name),
            )
        )

    events_response = client.run_report(
        RunReportRequest(
            property=prop,
            dimensions=[Dimension(name="eventName")],
            metrics=[Metric(name="eventCount")],
            date_ranges=date_ranges,
            **({"dimension_filter": event_filter} if event_filter else {}),
        )
    )

    events = [
        {
            "event_name": row.dimension_values[0].value,
            "event_count": _i(row.metric_values[0].value),
        }
        for row in events_response.rows
    ]

    return json.dumps(with_meta(
        {
            "start_date": start_date,
            "end_date": end_date,
            "converting_pages": converting_pages,
            "events": events,
        },
        tool="ga4_conversion_funnel",
        params={"start_date": start_date, "end_date": end_date, "event_name": event_name, "property_id": property_id},
    ))
