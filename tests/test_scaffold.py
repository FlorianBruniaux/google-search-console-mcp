import sys
import importlib


def test_python_version():
    assert sys.version_info >= (3, 11), "Requires Python 3.11+"


def test_server_importable():
    mod = importlib.import_module("gsc_mcp.server")
    assert hasattr(mod, "mcp")
    assert hasattr(mod, "main")


def test_mock_gsc_service(mock_gsc_service):
    sites = mock_gsc_service.sites()
    assert sites is not None


def test_mock_indexing_service(mock_indexing_service):
    batch = mock_indexing_service.new_batch_http_request()
    assert hasattr(batch, "add")
    assert hasattr(batch, "execute")
