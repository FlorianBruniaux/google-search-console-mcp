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
