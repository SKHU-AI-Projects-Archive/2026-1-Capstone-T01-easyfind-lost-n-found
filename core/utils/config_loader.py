import yaml
import os
from pathlib import Path

_DEFAULTS_PATH = Path(__file__).parent.parent.parent / 'configs' / 'default_config.yaml'


def load_config(exp_config_path=None):
    """default_config.yaml을 기준으로 실험 config를 deep-merge하여 반환한다."""
    with open(_DEFAULTS_PATH, 'r', encoding='utf-8') as f:
        config = yaml.safe_load(f)

    if exp_config_path and os.path.exists(exp_config_path):
        with open(exp_config_path, 'r', encoding='utf-8') as f:
            exp_config = yaml.safe_load(f)
        _deep_update(config, exp_config)
        print(f"[Config] Loaded: {exp_config_path}")

    return config


def _deep_update(base_dict, update_dict):
    """update_dict의 값을 base_dict에 재귀적으로 병합한다.
    두 값이 모두 dict일 때만 재귀 병합하고, 그 외에는 update_dict 값으로 덮어쓴다."""
    for key, val in update_dict.items():
        if isinstance(val, dict) and key in base_dict and isinstance(base_dict[key], dict):
            _deep_update(base_dict[key], val)
        else:
            base_dict[key] = val
