from core.utils.module_loader import get_class_by_name

def build_tracker(config):
    tracker_type = config.get('type', 'DummyTracker')
    tracker_class = get_class_by_name("plugins.trackers", tracker_type)
    return tracker_class(config)