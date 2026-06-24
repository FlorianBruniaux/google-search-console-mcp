import json

from google.analytics.data_v1alpha.types import (
    DateRange as AlphaDateRange,
    Funnel,
    FunnelEventFilter,
    FunnelFilterExpression,
    FunnelStep,
    RunFunnelReportRequest,
)
from google.analytics.data_v1beta.types import (
    BatchRunReportsRequest,
    DateRange,
    Dimension,
    Filter,
    FilterExpression,
    FilterExpressionList,
    Metric,
    RunRealtimeReportRequest,
    RunReportRequest,
)

from gsc_mcp.auth import get_alpha_ga4_service, get_ga4_service, get_ga4_property_id
from gsc_mcp.meta import with_meta
from gsc_mcp.retry import with_retry


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


def _build_dimension_filter(
    hostname: str | None = None,
    country: str | None = None,
    base_filter: FilterExpression | None = None,
) -> FilterExpression | None:
    expressions = []
    if base_filter:
        expressions.append(base_filter)
    if hostname:
        expressions.append(FilterExpression(filter=Filter(
            field_name="hostName",
            string_filter=Filter.StringFilter(
                match_type=Filter.StringFilter.MatchType.EXACT,
                value=hostname,
            ),
        )))
    if country:
        expressions.append(FilterExpression(filter=Filter(
            field_name="country",
            string_filter=Filter.StringFilter(
                match_type=Filter.StringFilter.MatchType.EXACT,
                value=country,
            ),
        )))
    if not expressions:
        return None
    if len(expressions) == 1:
        return expressions[0]
    return FilterExpression(and_group=FilterExpressionList(expressions=expressions))


@with_retry()
def ga4_organic_landing_pages(
    start_date: str = "28daysAgo",
    end_date: str = "today",
    limit: int = 50,
    property_id: str | None = None,
    hostname: str | None = None,
    country: str | None = None,
) -> str:
    """Fetch GA4 landing page performance filtered to organic traffic only.

    Dates use GA4 relative format: '28daysAgo', 'today', '7daysAgo', 'yesterday',
    or 'YYYY-MM-DD'. Returns sessions, engaged_sessions, bounce_rate, avg_session_duration,
    conversions, and revenue per landing page. Pass property_id to override GA4_PROPERTY_ID
    for multi-property setups. hostname and country narrow results to a specific host or country.
    """
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
        dimension_filter=_build_dimension_filter(hostname, country, base_filter=_organic_filter()),
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
        params={"start_date": start_date, "end_date": end_date, "limit": limit, "property_id": property_id, "hostname": hostname, "country": country},
    ))


@with_retry()
def ga4_traffic_sources(
    start_date: str = "28daysAgo",
    end_date: str = "today",
    property_id: str | None = None,
    hostname: str | None = None,
    country: str | None = None,
) -> str:
    """Fetch GA4 sessions grouped by channel group, source, and medium.

    Shows which traffic channels (Organic Search, Direct, Referral, etc.) drive
    the most sessions, engagement, conversions, and revenue. Dates use GA4 relative
    format: '28daysAgo', 'today', 'YYYY-MM-DD'. hostname and country narrow results.
    """
    prop = get_ga4_property_id(override=property_id)
    client = get_ga4_service()

    dim_filter = _build_dimension_filter(hostname, country)
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
        **({"dimension_filter": dim_filter} if dim_filter else {}),
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
        params={"start_date": start_date, "end_date": end_date, "property_id": property_id, "hostname": hostname, "country": country},
    ))


@with_retry()
def ga4_page_performance(
    start_date: str = "28daysAgo",
    end_date: str = "today",
    page_path: str | None = None,
    property_id: str | None = None,
    hostname: str | None = None,
    country: str | None = None,
) -> str:
    """Fetch GA4 page-level metrics: views, active users, session duration, engagement and bounce rates, conversions, and revenue.

    Optionally filter to pages whose path contains page_path (substring match).
    Dates use GA4 relative format: '28daysAgo', 'today', '7daysAgo', 'YYYY-MM-DD'.
    hostname and country narrow results to a specific host or country.
    """
    prop = get_ga4_property_id(override=property_id)
    client = get_ga4_service()

    page_filter = None
    if page_path:
        page_filter = FilterExpression(
            filter=Filter(
                field_name="pagePath",
                string_filter=Filter.StringFilter(
                    match_type=Filter.StringFilter.MatchType.CONTAINS,
                    value=page_path,
                ),
            )
        )

    dimension_filter = _build_dimension_filter(hostname, country, base_filter=page_filter)

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
        params={"start_date": start_date, "end_date": end_date, "page_path": page_path, "property_id": property_id, "hostname": hostname, "country": country},
    ))


@with_retry()
def ga4_realtime(property_id: str | None = None, hostname: str | None = None) -> str:
    """Fetch active users in the last 30 minutes from the GA4 Realtime API.

    Groups active users by screen name, country, and device category. Use for live
    traffic monitoring. No date range applies — this reflects the current moment only.
    hostname narrows results to a specific host (country is already a dimension, not a filter).
    """
    prop = get_ga4_property_id(override=property_id)
    client = get_ga4_service()

    hostname_filter = _build_dimension_filter(hostname=hostname)
    request = RunRealtimeReportRequest(
        property=prop,
        dimensions=[
            Dimension(name="unifiedScreenName"),
            Dimension(name="country"),
            Dimension(name="deviceCategory"),
        ],
        metrics=[Metric(name="activeUsers")],
        **({"dimension_filter": hostname_filter} if hostname_filter else {}),
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
        params={"property_id": property_id, "hostname": hostname},
    ))


@with_retry()
def ga4_user_behavior(
    start_date: str = "28daysAgo",
    end_date: str = "today",
    property_id: str | None = None,
    hostname: str | None = None,
    country: str | None = None,
) -> str:
    """Fetch GA4 sessions and engagement rate broken down by device, country, and user type.

    Executes a single batch request returning three reports: by device category,
    by country (top 20), and by new vs returning users. Useful for audience analysis.
    hostname and country narrow results across all three sub-reports.
    """
    prop = get_ga4_property_id(override=property_id)
    client = get_ga4_service()

    date_ranges = [DateRange(start_date=start_date, end_date=end_date)]
    behavior_metrics = [
        Metric(name="sessions"),
        Metric(name="engagementRate"),
    ]

    dim_filter = _build_dimension_filter(hostname, country)
    filter_kwargs = {"dimension_filter": dim_filter} if dim_filter else {}

    batch_request = BatchRunReportsRequest(
        property=prop,
        requests=[
            RunReportRequest(
                dimensions=[Dimension(name="deviceCategory")],
                metrics=behavior_metrics,
                date_ranges=date_ranges,
                **filter_kwargs,
            ),
            RunReportRequest(
                dimensions=[Dimension(name="country")],
                metrics=behavior_metrics,
                date_ranges=date_ranges,
                limit=20,
                **filter_kwargs,
            ),
            RunReportRequest(
                dimensions=[Dimension(name="newVsReturning")],
                metrics=behavior_metrics,
                date_ranges=date_ranges,
                **filter_kwargs,
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
        params={"start_date": start_date, "end_date": end_date, "property_id": property_id, "hostname": hostname, "country": country},
    ))


@with_retry()
def ga4_conversion_funnel(
    start_date: str = "28daysAgo",
    end_date: str = "today",
    event_name: str | None = None,
    property_id: str | None = None,
    hostname: str | None = None,
    country: str | None = None,
) -> str:
    """Fetch GA4 conversion data: pages that generated conversions, and event counts.

    Runs two reports in sequence: pages ranked by conversion count, and events ranked
    by event_count (optionally filtered to a specific event_name). Useful for identifying
    which pages and events drive goals. Dates use GA4 relative format.
    hostname and country narrow both reports to a specific host or country.
    """
    prop = get_ga4_property_id(override=property_id)
    client = get_ga4_service()

    date_ranges = [DateRange(start_date=start_date, end_date=end_date)]
    dim_filter = _build_dimension_filter(hostname, country)

    pages_response = client.run_report(
        RunReportRequest(
            property=prop,
            dimensions=[Dimension(name="pagePath")],
            metrics=[Metric(name="conversions")],
            date_ranges=date_ranges,
            **({"dimension_filter": dim_filter} if dim_filter else {}),
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

    events_filter = _build_dimension_filter(hostname, country, base_filter=event_filter)

    events_response = client.run_report(
        RunReportRequest(
            property=prop,
            dimensions=[Dimension(name="eventName")],
            metrics=[Metric(name="eventCount")],
            date_ranges=date_ranges,
            **({"dimension_filter": events_filter} if events_filter else {}),
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
        params={"start_date": start_date, "end_date": end_date, "event_name": event_name, "property_id": property_id, "hostname": hostname, "country": country},
    ))


@with_retry()
def ga4_funnel(
    steps: list[dict],
    start_date: str,
    end_date: str,
    property_id: str | None = None,
) -> str:
    """Run a GA4 funnel report using the v1alpha RunFunnelReport API.

    Each step is a dict with 'name' (display label) and 'event' (GA4 event name).
    Requires at least 2 steps. Returns users per step and conversion rate relative
    to step 1. Step 1 conversion_rate is always null. Pass property_id to override
    GA4_PROPERTY_ID for multi-property setups.
    """
    params = {"steps": steps, "start_date": start_date, "end_date": end_date, "property_id": property_id}

    if len(steps) < 2:
        return json.dumps(with_meta(
            {"error": "INVALID_STEPS", "reason": "minimum 2 steps required"},
            tool="ga4_funnel",
            params=params,
        ))

    funnel_steps = [
        FunnelStep(
            name=step["name"],
            filter_expression=FunnelFilterExpression(
                funnel_event_filter=FunnelEventFilter(event_name=step["event"])
            ),
        )
        for step in steps
    ]

    prop = get_ga4_property_id(override=property_id)
    client = get_alpha_ga4_service()

    request = RunFunnelReportRequest(
        property=prop,
        funnel=Funnel(steps=funnel_steps),
        date_ranges=[AlphaDateRange(start_date=start_date, end_date=end_date)],
    )
    response = client.run_funnel_report(request)

    rows = list(response.funnel_table.rows)
    step1_users = _i(rows[0].metric_values[0].value) if rows else 0
    result_steps = []
    for i, step in enumerate(steps):
        if i < len(rows):
            users = _i(rows[i].metric_values[0].value)
        else:
            users = 0
        conversion_rate = (
            None if i == 0
            else (round(users / step1_users * 100, 2) if step1_users else 0.0)
        )
        result_steps.append({
            "name": step["name"],
            "event": step["event"],
            "users": users,
            "conversion_rate": conversion_rate,
        })

    return json.dumps(with_meta(
        {"start_date": start_date, "end_date": end_date, "steps": result_steps},
        tool="ga4_funnel",
        params=params,
    ))
