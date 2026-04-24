import importlib.util
from pathlib import Path


MODULE_PATH = (
    Path(__file__).resolve().parents[1] / "main.py"
)
SPEC = importlib.util.spec_from_file_location("seedance_v2_main", MODULE_PATH)
PLUGIN = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(PLUGIN)


def test_legacy_base_url_is_ignored_and_endpoints_are_fixed(monkeypatch):
    monkeypatch.delenv("ZLHUB_TOS_AK", raising=False)
    monkeypatch.delenv("ZLHUB_TOS_SK", raising=False)

    params = PLUGIN._sanitize_params(  # pylint: disable=protected-access
        {"base_url": "https://evil.example.com", "model": "doubao-seedance-2.0"}
    )

    assert "base_url" not in params
    assert params["task_create_url"] == "https://api.zlhub.cn/v1/task/create"
    assert params["task_query_url"] == "https://api.zlhub.cn/v1/task/get"
    assert params["asset_base_url"] == "https://asset.zlhub.cn"
    assert params["endpoint_source"] == "constant"


def test_tos_credentials_prefer_env(monkeypatch):
    monkeypatch.setenv("ZLHUB_TOS_AK", "ENV_AK_VALUE")
    monkeypatch.setenv("ZLHUB_TOS_SK", "ENV_SK_VALUE")

    ak, sk, source = PLUGIN._resolve_tos_credentials()  # pylint: disable=protected-access

    assert ak == "ENV_AK_VALUE"
    assert sk == "ENV_SK_VALUE"
    assert source == "env"


def test_tos_credentials_fallback_to_fixed_when_env_missing(monkeypatch):
    monkeypatch.delenv("ZLHUB_TOS_AK", raising=False)
    monkeypatch.delenv("ZLHUB_TOS_SK", raising=False)

    ak, sk, source = PLUGIN._resolve_tos_credentials()  # pylint: disable=protected-access

    assert ak == PLUGIN._FIXED_TOS_AK  # pylint: disable=protected-access
    assert sk == PLUGIN._FIXED_TOS_SK  # pylint: disable=protected-access
    assert source == "constant"


def test_sensitive_log_sanitization_masks_tos_values():
    sanitized = PLUGIN._sanitize_for_log(  # pylint: disable=protected-access
        {
            "tos_ak": "AKLTNzI3MDM1NDQwZGMyNDM2M2E5YzY3MGE1ZGVjNzgyMzY",
            "tos_sk": "TmpFNFpUUmxaRE16TmpobE5EWTRaVGxrTXpabVpXRTJObVpsTVRjek1HWQ==",
        }
    )

    assert sanitized["tos_ak"] != "AKLTNzI3MDM1NDQwZGMyNDM2M2E5YzY3MGE1ZGVjNzgyMzY"
    assert sanitized["tos_sk"] != "TmpFNFpUUmxaRE16TmpobE5EWTRaVGxrTXpabVpXRTJObVpsTVRjek1HWQ=="
    assert "***" in sanitized["tos_ak"]
    assert "***" in sanitized["tos_sk"]
