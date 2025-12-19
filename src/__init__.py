"""
AutoFish Minecraft - Modules.
"""

from .config_manager import load_config, save_config
from .audio_processing import (
    get_running_applications,
    get_app_volume,
    volume_to_db,
    db_to_normalized_scale
)
from .window_management import (
    get_process_id_by_name,
    is_application_in_foreground,
    get_hwnds_for_pid,
    bring_window_to_front
)
from .human_behavior import HumanProfile, HumanLikeRandomizer
from .stats_manager import StatsManager
from .calibration import AutoCalibrator
from .ui_components import (
    VolumeGraphBar,
    COLORS_MAP,
    get_color_list,
    translate_color
)

__all__ = [
    # config_manager
    'load_config',
    'save_config',
    # audio_processing
    'get_running_applications',
    'get_app_volume',
    'volume_to_db',
    'db_to_normalized_scale',
    # window_management
    'get_process_id_by_name',
    'is_application_in_foreground',
    'get_hwnds_for_pid',
    'bring_window_to_front',
    # human_behavior
    'HumanProfile',
    'HumanLikeRandomizer',
    # stats_manager
    'StatsManager',
    # calibration
    'AutoCalibrator',
    # ui_components
    'VolumeGraphBar',
    'COLORS_MAP',
    'get_color_list',
    'translate_color',
]
