import importlib
import pkgutil
import inspect
import sys

def import_all_modules_in_package(package_name):
    try:
        package = importlib.import_module(package_name)
    except ImportError as e:
        print(f"[ModuleLoader] Warning: Failed to import package '{package_name}'. {e}")
        return

    if not hasattr(package, "__path__"):
        return

    for _, name, _ in pkgutil.iter_modules(package.__path__):
        full_module_name = f"{package_name}.{name}"
        if full_module_name not in sys.modules:
            importlib.import_module(full_module_name)

def get_class_by_name(package_name, class_name):
    import_all_modules_in_package(package_name)
    
    for module_key, module in sys.modules.items():
        if module_key.startswith(package_name):
            if hasattr(module, class_name):
                found_class = getattr(module, class_name)
                if inspect.isclass(found_class):
                    return found_class
    
    raise ValueError(f"Class '{class_name}' not found under package '{package_name}'")