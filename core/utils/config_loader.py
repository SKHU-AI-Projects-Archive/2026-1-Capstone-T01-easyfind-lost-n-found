import yaml
import os

def load_config(exp_config_path=None):
    with open("configs/default_config.yaml", 'r', encoding='utf-8') as f:
        config = yaml.safe_load(f)

    if exp_config_path and os.path.exists(exp_config_path):
        with open(exp_config_path, 'r', encoding='utf-8') as f:
            exp_config = yaml.safe_load(f)
            _deep_update(config, exp_config)
            print(f"[Config] Merged with {exp_config_path}")

    return config

def _deep_update(base_dict, update_dict):
    for key, val in update_dict.items():
        if isinstance(val, dict) and key in base_dict:
            _deep_update(base_dict[key], val)
        else:
            base_dict[key] = val