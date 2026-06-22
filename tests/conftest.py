import pytest
from unittest.mock import MagicMock


@pytest.fixture
def mock_gsc_service():
    service = MagicMock()
    sites = MagicMock()
    service.sites.return_value = sites

    searchanalytics = MagicMock()
    service.searchanalytics.return_value = searchanalytics

    sitemaps = MagicMock()
    service.sitemaps.return_value = sitemaps

    urlInspection = MagicMock()
    service.urlInspection.return_value = urlInspection

    return service


@pytest.fixture
def mock_indexing_service():
    service = MagicMock()
    urlNotifications = MagicMock()
    service.urlNotifications.return_value = urlNotifications

    def new_batch_http_request(callback=None):
        batch = MagicMock()
        batch._requests = []
        batch._callback = callback

        def add(request, request_id=None, callback=None):
            batch._requests.append((request, request_id, callback))

        batch.add = add

        def execute():
            for req, req_id, cb in batch._requests:
                if cb:
                    cb(req_id, {"status": "OK"}, None)

        batch.execute = execute
        return batch

    service.new_batch_http_request = new_batch_http_request
    return service


def _make_ga4_row(dimension_values: list, metric_values: list):
    row = MagicMock()
    row.dimension_values = [MagicMock(value=v) for v in dimension_values]
    row.metric_values = [MagicMock(value=v) for v in metric_values]
    return row


def _make_ga4_response(rows: list):
    response = MagicMock()
    response.rows = rows
    return response


def _make_ga4_batch_response(responses: list):
    response = MagicMock()
    response.reports = responses
    return response


@pytest.fixture
def mock_ga4_service():
    client = MagicMock()
    client.run_report.return_value = _make_ga4_response([])
    client.run_realtime_report.return_value = _make_ga4_response([])
    client.batch_run_reports.return_value = _make_ga4_batch_response([
        _make_ga4_response([]),
        _make_ga4_response([]),
        _make_ga4_response([]),
    ])
    return client
