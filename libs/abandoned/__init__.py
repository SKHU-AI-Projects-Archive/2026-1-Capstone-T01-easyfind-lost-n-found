from core.utils.module_loader import get_class_by_name

def build_abandoned(config):
    abandoned_type = config.get('type', 'abandonedObject')
    abandoned_class = get_class_by_name('libs.abandoned', abandoned_type)
    return abandoned_class(config)