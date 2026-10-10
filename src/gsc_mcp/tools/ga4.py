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
    CheckCompatibilityRequest,
    Compatibility,
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
from gsc_mcp.audit_runtime import call_ga4
from gsc_mcp.retry import with_retry
from gsc_mcp.ai_referrals import MATCHING_RULES, assistant_breakdown, parse_row, totals, validate_window


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


def _nullable_i(value: str) -> int | None:
    """Keep malformed traffic counts unknown instead of inventing a zero."""
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _report_coverage(response, returned_rows: int) -> tuple[dict, str | None]:
    """Expose API coverage without guessing absent metadata."""
    row_count = getattr(response, "row_count", None)
    if type(row_count) is not int or row_count < 0:
        row_count = None
    metadata = getattr(response, "metadata", None)
    loss = getattr(metadata, "data_loss_from_other_row", None)
    thresholding = getattr(metadata, "subject_to_thresholding", None)
    sampling = getattr(metadata, "sampling_metadatas", None)
    time_zone = getattr(metadata, "time_zone", None)
    empty_reason = getattr(metadata, "empty_reason", None)
    restrictions = getattr(getattr(metadata, "schema_restriction_response", None), "active_metric_restrictions", None)
    metric_restrictions = None
    if restrictions is not None and not isinstance(restrictions, str) and hasattr(restrictions, "__len__"):
        metric_restrictions = [
            {"metric_name": item.metric_name, "restricted_metric_types": [int(value) for value in item.restricted_metric_types]}
            for item in restrictions
        ]
    return {
        "row_count": row_count,
        "returned_rows": returned_rows,
        "complete": row_count == returned_rows if row_count is not None else None,
        "data_loss_from_other_row": loss if type(loss) is bool else None,
        "sampling": bool(sampling) if sampling is not None and hasattr(sampling, "__len__") else None,
        "subject_to_thresholding": thresholding if type(thresholding) is bool else None,
        "empty_reason": empty_reason if isinstance(empty_reason, str) and empty_reason else None,
        "metric_restrictions": metric_restrictions,
    }, time_zone if isinstance(time_zone, str) and time_zone else None


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
def _ai_referral_request(client, method: str, request):
    """Retry individual requests before composing an unavailable report."""
    return call_ga4(getattr(client, method), request)


def ga4_ai_referrals(
    start_date: str,
    end_date: str,
    property_id: str | None = None,
    hostname: str | None = None,
) -> str:
    """Report observed GA4 visits attributed to exact documented assistant sources.

    Requires inclusive YYYY-MM-DD dates. Only chatgpt.com is currently confirmed;
    other candidate product sources remain separate. Reads up to 10000 all-source
    landing-page rows in one compatible report. Shares require complete coverage;
    counts describe returned observations, not citations or all true AI visits.
    The conversions alias is sourced from the current GA4 keyEvents metric.
    """
    validate_window(start_date, end_date)
    params = {"start_date": start_date, "end_date": end_date, "property_id": property_id, "hostname": hostname}
    source = {"property": None, "filters": {"hostname": hostname},
              "requested_window": {"start": start_date, "end": end_date},
              "reported_window": None, "observed_window": None}
    data = {
        "start_date": start_date, "end_date": end_date, "availability": "unavailable",
        "rows": [], "confirmed_totals": None, "candidate_totals": None, "assistants": [],
        "total_sessions": None, "ai_session_share": None, "share_reason": "source_unavailable",
        "coverage": None, "time_zone": None,
        "comparison": {"availability": "unavailable", "reason": "not_requested"},
        "matching_rules": MATCHING_RULES, "metric_mapping": {"conversions": "keyEvents"},
        "limitations": [
            "Recorded source attribution measures visits, not observed citations or citation probability.",
            "Missing referrers and attribution errors can undercount or misattribute visits; counts are not a guaranteed lower bound.",
            "Source labels including UTM tags can be spoofed; a matching label does not authenticate the client.",
            "Totals describe returned rows; the 10000-row cap, row loss, sampling or thresholding can limit coverage.",
            "Source calendar boundaries use the reported GA4 property timezone; no comparison period was requested.",
            "The installed API metadata may not expose newer dataTruncationReasons fields.",
        ],
    }
    try:
        prop = get_ga4_property_id(override=property_id)
        client = get_ga4_service()
        dimensions = [Dimension(name=name) for name in ("sessionSource", "sessionMedium", "landingPagePlusQueryString")]
        metrics = [Metric(name=name) for name in ("sessions", "engagedSessions", "keyEvents")]
        dimension_filter = _build_dimension_filter(hostname)
        source["property"] = prop
        check = _ai_referral_request(client, "check_compatibility", CheckCompatibilityRequest(
            property=prop, dimensions=dimensions, metrics=metrics, dimension_filter=dimension_filter,
        ))
        compatible_dimensions = {item.dimension_metadata.api_name for item in check.dimension_compatibilities
                                 if item.compatibility == Compatibility.COMPATIBLE}
        compatible_metrics = {item.metric_metadata.api_name for item in check.metric_compatibilities
                              if item.compatibility == Compatibility.COMPATIBLE}
        if not ({d.name for d in dimensions} <= compatible_dimensions
                and {m.name for m in metrics} <= compatible_metrics):
            data["reason"] = "incompatible_or_unknown_api_fields"
        else:
            response = _ai_referral_request(client, "run_report", RunReportRequest(
                property=prop, dimensions=dimensions, metrics=metrics, dimension_filter=dimension_filter,
                date_ranges=[DateRange(start_date=start_date, end_date=end_date)], limit=10000,
            ))
            data["coverage"], data["time_zone"] = _report_coverage(response, len(response.rows))
            source["reported_window"] = source["requested_window"]
            try:
                rows = [parse_row(row) for row in response.rows]
            except (TypeError, ValueError, AttributeError):
                data.update(availability="unknown", reason="malformed_measurements", share_reason="unknown_source")
            else:
                data["availability"] = "measured" if rows else "empty"
                data["rows"] = rows
                if not rows:
                    data["share_reason"] = "empty_source"
                else:
                    confirmed = [row for row in rows if row["classification"] == "confirmed"]
                    candidates = [row for row in rows if row["classification"] == "candidate"]
                    data["confirmed_totals"], data["candidate_totals"] = totals(confirmed), totals(candidates)
                    data["assistants"] = assistant_breakdown(confirmed)
                    coverage = data["coverage"]
                    complete = coverage["complete"] is True and coverage["metric_restrictions"] == [] and all(
                        coverage[flag] is False for flag in ("data_loss_from_other_row", "sampling", "subject_to_thresholding")
                    )
                    if not complete:
                        data["share_reason"] = "incomplete_coverage"
                    else:
                        data["total_sessions"] = sum(row["sessions"] for row in rows)
                        if data["total_sessions"] == 0:
                            data["share_reason"] = "zero_denominator"
                        else:
                            data["ai_session_share"] = data["confirmed_totals"]["sessions"] / data["total_sessions"]
                            data["share_reason"] = None
    except Exception as exc:
        configuration_error = isinstance(exc, RuntimeError) and str(exc).startswith(
            ("No GA4 config", "No credentials:", "OAuth browser flow disabled")
        )
        data.update(reason="configuration_error" if configuration_error else "upstream_error", error_type=type(exc).__name__)
    source["availability"] = data["availability"]
    source["coverage"] = data["coverage"]
    source["time_zone"] = data["time_zone"]
    data["source_data"] = {"ga4": source}
    return json.dumps(with_meta(data, tool="ga4_ai_referrals", params=params, sources={"ga4": {"property": source["property"]}}))


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

    response = call_ga4(client.run_report, request)

    pages = [
        {
            "landing_page": row.dimension_values[0].value,
            "sessions": _nullable_i(row.metric_values[0].value),
            "engaged_sessions": _i(row.metric_values[1].value),
            "bounce_rate": _f(row.metric_values[2].value),
            "avg_session_duration": _f(row.metric_values[3].value),
            "conversions": _f(row.metric_values[4].value),
            "total_revenue": _f(row.metric_values[5].value),
        }
        for row in response.rows
    ]

    coverage, time_zone = _report_coverage(response, len(pages))
    data = {"start_date": start_date, "end_date": end_date, "count": len(pages), "pages": pages,
            "coverage": coverage, "time_zone": time_zone}
    if len(pages) >= limit:
        data["note"] = "Results may be truncated. Set a higher limit or filter by page_path for large properties."
    return json.dumps(with_meta(
        data,
        tool="ga4_organic_landing_pages",
        params={"start_date": start_date, "end_date": end_date, "limit": limit, "property_id": property_id, "hostname": hostname, "country": country},
        sources={"ga4": {"property": prop}},
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

    response = call_ga4(client.run_report, request)

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
        sources={"ga4": {"property": prop}},
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

    response = call_ga4(client.run_report, request)

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
        sources={"ga4": {"property": prop}},
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

    response = call_ga4(client.run_realtime_report, request)

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
        sources={"ga4": {"property": prop}},
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

    response = call_ga4(client.batch_run_reports, batch_request)

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
        sources={"ga4": {"property": prop}},
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

    pages_response = call_ga4(client.run_report,
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

    events_response = call_ga4(client.run_report,
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
        sources={"ga4": {"property": prop}},
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
    response = call_ga4(client.run_funnel_report, request)

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
        sources={"ga4": {"property": prop}},
    ))
