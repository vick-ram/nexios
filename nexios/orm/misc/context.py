from __future__ import annotations

import contextvars
import functools
import inspect
from contextlib import contextmanager, asynccontextmanager
from enum import Enum
from typing import TypeVar, Dict, Any, Type, Callable, Optional, Awaitable, Union, Self
from dataclasses import dataclass, field

T = TypeVar('T')
T_co = TypeVar('T_co', covariant=True)


class Lifecycle(Enum):
    TRANSIENT = 'transient'  # New instance each time
    SCOPED = 'scoped'  # One instance per scope
    SINGLETON = 'singleton'  # Single instance globally
    REQUEST = 'request'  # One instance per request (scope-like)


@dataclass
class DependencyInfo:
    interface: Type
    implementation: Optional[Type] = None
    factory: Optional[Callable[..., Any]] = None
    lifecycle: Lifecycle = Lifecycle.SCOPED
    args: tuple = field(default_factory=tuple)
    kwargs: Dict[str, Any] = field(default_factory=dict)


class DependencyContainer:
    def __init__(self, parent: Optional[DependencyContainer] = None):
        self._parent = parent
        self._registry: Dict[Type, DependencyInfo] = {}
        self._scoped_instances: Dict[Type, Any] = {}
        self._singleton_instances: Dict[Type, Any] = {}

        self._current_scope: contextvars.ContextVar[Dict[Type, Any]] = contextvars.ContextVar(
            'current_scope',
            default={}
        )

    def register(
            self,
            interface: Type[T],
            implementation: Optional[Type[T]] = None,
            *,
            factory: Optional[Callable[..., Union[T, Awaitable[T]]]] = None,
            lifecycle: Lifecycle = Lifecycle.SCOPED, **kwargs
    ) -> None:
        if implementation is None and factory is None:
            implementation = interface

        self._registry[interface] = DependencyInfo(
            interface=interface,
            implementation=implementation,
            factory=factory,
            lifecycle=lifecycle,
            kwargs=kwargs
        )

    async def resolve(self, interface: Type[T]) -> T:
        return await self._resolve_dependency(interface, set())

    async def _resolve_dependency(self, interface: Type[T], resolving: set, path: tuple = ()) -> T:
        if interface in resolving:
            cycle_path = "->".join(str(p) for p in path + (interface,))
            raise DependencyResolutionError(f"Circular dependency detected: {cycle_path}")

        dep_info = self._find_dependency_info(interface)
        if dep_info is None:
            raise DependencyResolutionError(f"No dependency found for {interface}")

        instance = self._get_existing_instance(dep_info)
        if instance is not None:
            return instance
        new_resolving = resolving.copy()
        new_resolving.add(interface)
        new_path = path + (interface,)

        try:
            instance = await  self._create_instance(dep_info, new_resolving, new_path)
        except Exception as e:
            raise DependencyResolutionError(f"Failed to create instance of {interface}: {e}")

        self._store_instance(dep_info, instance)

        return instance

    def _find_dependency_info(self, interface: Type[T]) -> Optional[DependencyInfo]:
        if interface in self._registry:
            return self._registry[interface]
        if self._parent:
            return self._parent._find_dependency_info(interface)
        return None

    def _get_existing_instance(self, dep_info: DependencyInfo) -> Optional[Any]:
        if dep_info.lifecycle == Lifecycle.SINGLETON:
            return self._singleton_instances.get(dep_info.interface)
        elif dep_info.lifecycle == Lifecycle.SCOPED:
            scope = self._current_scope.get()
            if scope and dep_info.interface in scope:
                return scope[dep_info.interface]
        return None

    async def _create_instance(self, dep_info: DependencyInfo, resolving: set, path: tuple = ()) -> Any:
        if dep_info.factory:
            return await self._call_factory(dep_info, resolving, path)

        impl = dep_info.implementation or dep_info.interface

        if impl is None:
            raise DependencyResolutionError(f"No implementation or interface found for {dep_info.interface}")

        sig = inspect.signature(impl.__init__)
        params = {}

        for param_name, param in sig.parameters.items():
            if param.kind == param.POSITIONAL_OR_KEYWORD:
                continue

            if param_name in dep_info.kwargs:
                params[param_name] = dep_info.kwargs[param_name]
            elif param.annotation == param.empty:
                params[param_name] = self._resolve_dependency(param.annotation, resolving, path)
            elif param.default != inspect.Parameter.empty:
                params[param_name] = param.default
            else:
                raise DependencyResolutionError(f"Cannot resolve parameter {param_name} for {impl.__name__}")

        instance = impl(**params)

        if hasattr(instance, '__ainit__'):
            instance.__ainit__()

        return instance

    async def _call_factory(self, dep_info: DependencyInfo, resolving: set, path: tuple = ()) -> Any:
        factory = dep_info.factory
        is_async = inspect.iscoroutinefunction(factory)
        if factory is None:
            raise DependencyResolutionError(f"Factory is None for {dep_info.interface}")

        sig = inspect.signature(factory)

        if not is_async and len(sig.parameters) > 0:
            params = {}

            for param_name, param in sig.parameters.items():
                if param.annotation == inspect.Parameter.empty:
                    params[param_name] = self._resolve_dependency(param.annotation, resolving, path)
                elif param_name in dep_info.kwargs:
                    params[param_name] = dep_info.kwargs[param_name]
            result = factory(**params)
        elif is_async:
            if len(sig.parameters) > 0:
                params = {}
                for param_name, param in sig.parameters.items():
                    if param.annotation == inspect.Parameter.empty:
                        params[param_name] = self._resolve_dependency(param.annotation, resolving, path)
                    elif param_name in dep_info.kwargs:
                        params[param_name] = dep_info.kwargs[param_name]
                result = await factory(**params)
            else:
                result = await factory()
        else:
            result = factory()

        return result

    def _store_instance(self, dep_info: DependencyInfo, instance: Any) -> None:
        if dep_info.lifecycle == Lifecycle.SINGLETON:
            self._singleton_instances[dep_info.interface] = instance
        elif dep_info.lifecycle == Lifecycle.SCOPED:
            scope = self._current_scope.get()
            if scope is not None:
                scope[dep_info.interface] = instance

    @asynccontextmanager
    async def scope(self):
        scope_context: Dict[Type, Any] = {}
        token = self._current_scope.set(scope_context)

        try:
            yield
        finally:
            for instance in scope_context.values():
                if hasattr(instance, '__exit__'):
                    instance.__exit__(None, None, None)
                elif hasattr(instance, '__aexit__'):
                    await instance.__aexit__(None, None, None)
            self._current_scope.reset(token)

    def child(self) -> Self:
        return self.__class__(parent=self)

class DependencyResolutionError(Exception):
    pass

class DependencyContext:

    def __init__(self):
        self._root_container = DependencyContainer()
        self._container_var = contextvars.ContextVar("current_container", default=self._root_container)

    @property
    def container(self) -> DependencyContainer:
        return self._container_var.get()

    @contextmanager
    def scope(self):
        scope_context = {}
        token = self._container_var.set(self.container.child())

        try:
            yield scope_context
        finally:
            self._container_var.reset(token)

    def register(
            self,
            interface: Type[T],
            implementation: Optional[Type[T]] = None,
            *,
            factory: Optional[Callable[..., Union[T, Awaitable[T]]]] = None,
            lifecycle: Lifecycle = Lifecycle.SCOPED,
            **kwargs
    ):
        self._root_container.register(
            interface=interface,
            implementation=implementation,
            factory=factory,
            lifecycle=lifecycle,
            **kwargs
        )

    async def resolve(self, interface: Type[T]) -> T:
        return await self.container.resolve(interface)


_context = DependencyContext()

def register(
        interface: Type[T],
        implementation: Optional[Type[T]] = None,
        *,
        factory: Optional[Callable[..., Union[T, Awaitable[T]]]] = None,
        lifecycle: Lifecycle = Lifecycle.SCOPED,
        **kwargs
) -> None:
    _context.register(
        interface=interface,
        implementation=implementation,
        factory=factory,
        lifecycle=lifecycle,
        **kwargs
    )

def resolve(interface: Type[T]) -> T:
    from nexios.orm.misc.event_loop import NexiosEventLoop
    _loop = NexiosEventLoop()

    return _loop.run(_context.resolve(interface))

def inject(interface: Type[T]) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            instance = resolve(interface)
            return func(instance, *args, **kwargs)

        return wrapper

    return decorator
