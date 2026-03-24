"""Dynamic strategy loader — loads a strategy class from a dotted path."""
from __future__ import annotations

import importlib
from typing import Type

from sdk.strategy_sdk.base import BaseStrategy


def load_strategy(path: str) -> Type[BaseStrategy]:
    """Load a strategy class from 'module.path:ClassName' format."""
    if ":" not in path:
        raise ValueError(f"strategy path must be 'module:ClassName', got '{path}'")
    module_path, class_name = path.rsplit(":", 1)
    module = importlib.import_module(module_path)
    cls = getattr(module, class_name)
    if not (isinstance(cls, type) and issubclass(cls, BaseStrategy)):
        raise TypeError(f"{cls} is not a BaseStrategy subclass")
    return cls
