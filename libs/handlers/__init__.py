from core.utils.module_loader import get_class_by_name


def build_handler(config):
    handler_type = config.get('type', 'ScreenHandler')
    handler_class = get_class_by_name("libs.handlers", handler_type)
    return handler_class(config)
