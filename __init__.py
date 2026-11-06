"""ComfyUI_ALEXZ_SilentFilm custom node package."""

from .nodes import NODE_CLASS_MAPPINGS, NODE_DISPLAY_NAME_MAPPINGS
from .nodes.node_registry import ENABLE_NODE_LOADING

WEB_DIRECTORY = "./web" if ENABLE_NODE_LOADING else None

if ENABLE_NODE_LOADING:
    try:
        from aiohttp import web
        from server import PromptServer
    except Exception:  # pragma: no cover - non-ComfyUI import
        PromptServer = None
        web = None

    if PromptServer is not None and web is not None and getattr(PromptServer, "instance", None) is not None:
        from .utils.video_io_api import register_routes

        register_routes(PromptServer, web)

    from .utils.video_cache import install as _install_video_cache

    _install_video_cache()

__all__ = ["NODE_CLASS_MAPPINGS", "NODE_DISPLAY_NAME_MAPPINGS"]
