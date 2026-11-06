"""Load standalone Silent Film node classes from the package registry."""

import importlib
import logging
import traceback

from .node_registry import ENABLE_NODE_LOADING, NODE_SPECS, NODE_UI_METADATA

_LOGGER = logging.getLogger("ALEXZ_SilentFilm")
NODE_CLASS_MAPPINGS = {}
NODE_DISPLAY_NAME_MAPPINGS = {}
LOAD_RESULTS = {"ok": [], "fail": []}


def _load_node(type_name, display_name, module_name, class_name):
    """Import one node class and add it to ComfyUI's mappings."""
    try:
        module = importlib.import_module(module_name, __name__)
        node_class = getattr(module, class_name)
        NODE_CLASS_MAPPINGS[type_name] = node_class
        NODE_DISPLAY_NAME_MAPPINGS[type_name] = display_name
        LOAD_RESULTS["ok"].append(type_name)
        _LOGGER.info("✅ %s loaded", display_name)
    except Exception as exc:
        LOAD_RESULTS["fail"].append({"name": type_name, "display_name": display_name,
                                    "module": module_name, "class_name": class_name,
                                    "reason": str(exc)})
        _LOGGER.error("Failed to load node %s: %s\n%s", type_name, exc, traceback.format_exc())


if ENABLE_NODE_LOADING:
    for _spec in NODE_SPECS:
        _load_node(_spec.type_name, _spec.display_name, _spec.module_import, _spec.class_name)

for _name, _node_class in NODE_CLASS_MAPPINGS.items():
    _metadata = NODE_UI_METADATA.get(_name)
    if not _metadata:
        continue
    if not getattr(_node_class, "DESCRIPTION", ""):
        _node_class.DESCRIPTION = _metadata["description"]
    if not hasattr(_node_class, "OUTPUT_TOOLTIPS"):
        _node_class.OUTPUT_TOOLTIPS = list(_metadata["output_tooltips"])
    if not hasattr(_node_class, "SEARCH_ALIASES"):
        _node_class.SEARCH_ALIASES = list(_metadata["search_aliases"])

__all__ = ["NODE_CLASS_MAPPINGS", "NODE_DISPLAY_NAME_MAPPINGS", "LOAD_RESULTS"]
