import sys
from pathlib import Path

import pytest


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import main as plugin_main


def _tos_params():
    return {
        "tos_ak": "ak",
        "tos_sk": "sk",
        "tos_endpoint": "tos-cn-beijing.volces.com",
        "tos_region": "cn-beijing",
        "tos_bucket": "zlhub-asset-outside",
    }


def test_normalize_or_upload_media_url_passthrough_public_and_asset():
    params = _tos_params()
    assert (
        plugin_main._normalize_or_upload_media_url(
            "https://example.com/a.png", "参考图片", params
        )
        == "https://example.com/a.png"
    )
    assert (
        plugin_main._normalize_or_upload_media_url(
            "asset://abc123", "参考图片", params
        )
        == "asset://abc123"
    )


def test_normalize_or_upload_media_url_uploads_local_file(monkeypatch, tmp_path):
    file_path = tmp_path / "sample.png"
    file_path.write_bytes(b"png-bytes")

    called = {"path": None}

    def fake_upload(path, params):
        called["path"] = path
        return "https://cdn.example.com/uploaded.png"

    monkeypatch.setattr(plugin_main, "_upload_file_to_tos", fake_upload)

    result = plugin_main._normalize_or_upload_media_url(
        str(file_path), "参考图片", _tos_params()
    )

    assert result == "https://cdn.example.com/uploaded.png"
    assert called["path"] == str(file_path)


def test_normalize_or_upload_media_url_uploads_data_url(monkeypatch):
    called = {"data": None}

    def fake_upload(data_url, params):
        called["data"] = data_url
        return "https://cdn.example.com/from-data.png"

    monkeypatch.setattr(plugin_main, "_upload_data_url_to_tos", fake_upload)

    data_url = "data:image/png;base64,Zm9v"
    result = plugin_main._normalize_or_upload_media_url(
        data_url, "参考图片", _tos_params()
    )

    assert result == "https://cdn.example.com/from-data.png"
    assert called["data"] == data_url


def test_ensure_tos_config_requires_all_fields():
    with pytest.raises(plugin_main.PluginFatalError, match="TOS"):
        plugin_main._ensure_tos_config({"tos_ak": "", "tos_sk": ""})
