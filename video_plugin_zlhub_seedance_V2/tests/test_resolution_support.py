import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import main as plugin_main


def test_1080p_only_supported_for_standard_model():
    params_standard = plugin_main._sanitize_params(
        {"model": "doubao-seedance-2.0", "resolution": "1080p", "ratio": "16:9"}
    )
    assert params_standard["resolution"] == "1080p"
    assert (params_standard["pixel_width"], params_standard["pixel_height"]) == (1920, 1088)

    params_fast = plugin_main._sanitize_params(
        {"model": "doubao-seedance-2.0-fast", "resolution": "1080p", "ratio": "16:9"}
    )
    assert params_fast["resolution"] == "720p"
    assert (params_fast["pixel_width"], params_fast["pixel_height"]) == (1280, 720)


def test_1080p_ratio_pixel_map_matches_expected_values():
    expected_pairs = {
        "16:9": (1920, 1088),
        "4:3": (1664, 1248),
        "1:1": (1440, 1440),
        "3:4": (1248, 1664),
        "9:16": (1088, 1920),
        "21:9": (2176, 928),
    }
    assert plugin_main.RESOLUTION_RATIO_MAP["1080p"] == expected_pairs
