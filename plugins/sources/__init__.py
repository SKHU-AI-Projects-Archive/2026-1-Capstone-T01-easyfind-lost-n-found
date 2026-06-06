from core.utils.module_loader import get_class_by_name
from .dummy_source import DummySource
from .webcam_source import WebcamSource
from .image_source import FolderImageSource
from .video_source import VideoSource
from .archive_source import ArchiveSource



def build_source(config):
    source_type = config.get('type', 'DummySource')
    source_class = get_class_by_name("plugins.sources", source_type)
    return source_class(config)