from __future__ import annotations

import contextvars
import inspect
from typing import Any, Dict, Optional

class ContextData:
    def __init__(self, name: str, default: Any = None):
        self._var = contextvars.ContextVar(name, default=default)
        self._name = name

    def get(self):
        return self._var.get()

    def set(self, value):
        return self._var.set(value)

    def reset(self, token: contextvars.Token):
        self._var.reset(token)

    @property
    def name(self):
        return self._name

_context_registry: Dict[str, ContextData] = {}

class _ContextCache:
    def __init__(self):
        self._cache: Dict[Any, ContextData] = {}

    def get_or_create(self, key: Any, name: Optional[str] = None, default: Optional[Any] = None) -> ContextData:
        if key not in self._cache:
            if name is None:
                name = f"context_data_{id(key)}"
            self._cache[key] = ContextData(name, default)
            _context_registry[name] = self._cache[key]
        return self._cache[key]

_cache = _ContextCache()

def context_data(key: Any, default: Optional[Any] = None, name: Optional[str] = None) -> ContextData:
    return _cache.get_or_create(key, default, name)

def get_context_data(key: Any):
    data = context_data(key)
    return data.get()

def set_context_data(key: Any, value: Any):
    data = context_data(key)
    return data.set(value)

def reset_context_data(key: Any, token: contextvars.Token):
    data = context_data(key)
    data.reset(token)

def with_context(key: Any, value: Any):
    def decorator(func):
        if inspect.iscoroutinefunction(func):
            async def async_wrapper(*args, **kwargs):
                data = context_data(key)
                token = data.set(value)
                try:
                    return await func(*args, **kwargs)
                finally:
                    data.reset(token)
            return async_wrapper
        else:
            def sync_wrapper(*args, **kwargs):
                data = context_data(key)
                token = data.set(value)

                try:
                    return func(*args, **kwargs)
                finally:
                    data.reset(token)
            return sync_wrapper
    return decorator
