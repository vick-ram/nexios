from __future__ import annotations

import sys
import builtins
import re
from typing import (
    Any,
    Dict,
    List,
    ForwardRef,
    get_type_hints,
)

class ResolveForwardRefs:

    @classmethod
    def resolve_forward_references(cls):
        localns = cls._get_local_namespace()
        globalns = cls._get_global_namespace()

        try:
            resolved_hints = get_type_hints(cls, globalns=globalns, localns=localns)
            cls.__annotations__.update(resolved_hints)
        except Exception:
            cls._custom_resolve_forward_references(globalns, localns)
    

    @classmethod
    def _get_global_namespace(cls) -> Dict[str, Any]:
        globalns = {**builtins.__dict__}
        import typing

        globalns.update(typing.__dict__)
        try:
            import typing_extensions

            globalns.update(typing_extensions.__dict__)
        except ImportError:
            pass
        globalns.update(cls.__registry__)  # type: ignore
        module = sys.modules.get(cls.__module__)
        if module:
            globalns.update(getattr(module, "__dict__", {}))
        return globalns
    
    @classmethod
    def _get_local_namespace(cls) -> Dict[str, Any]:
        localns = {}

        localns[cls.__name__] = cls

        module = sys.modules.get(cls.__module__)
        if module:
            for name, obj in module.__dict__.items():
                if (
                    isinstance(obj, type)
                    and hasattr(obj, "__module__")
                    and obj.__module__ == cls.__module__
                ):
                    localns[name] = obj

        return localns
    
    @classmethod
    def _custom_resolve_forward_references(
        cls, globalns: Dict[str, Any], localns: Dict[str, Any]
    ):
        for field_name, annotation in list(cls.__annotations__.items()):
            try:
                if isinstance(annotation, str):
                    resolved = cls._resolve_single_forward_ref(
                        annotation, globalns, localns
                    )
                    if resolved is not None:
                        cls.__annotations__[field_name] = resolved
                elif isinstance(annotation, ForwardRef):
                    resolved = cls._resolve_forward_ref_instance(
                        annotation, globalns, localns
                    )
                    if resolved is not None:
                        cls.__annotations__[field_name] = resolved
            except Exception as e:
                print(
                    f"Warning: Could not resolve forward reference for {cls.__name__}.{field_name}: {e}"
                )
    
    @classmethod
    def _resolve_single_forward_ref(
        cls, annotation: str, globalns: Dict[str, Any], localns: Dict[str, Any]
    ) -> Any:
        if re.match(r"^[A-Z][a-zA-Z_]*\[", annotation):
            return cls._resolve_generic_forward_ref(annotation, globalns, localns)

        if annotation in localns:
            return localns[annotation]

        if annotation in globalns:
            return globalns[annotation]

        for key, model_class in cls.__registry__.items():  # type: ignore[no-def]
            if key.endswith(f".{annotation}") or model_class.__name__ == annotation:
                return model_class

        try:
            return get_type_hints(annotation, globalns, localns)
        except Exception:
            pass
        return None

    @classmethod
    def _resolve_generic_forward_ref(
        cls, annotation: str, globalns: Dict[str, Any], localns: Dict[str, Any]
    ) -> Any:
        try:
            match = re.match(r"^([A-Z][a-zA-Z_]*)\[(.*)]$", annotation)
            if not match:
                return None

            outer_type_name, inner_type_str = match.groups()

            outer_type = None
            if outer_type_name in localns:
                outer_type = localns[outer_type_name]
            elif outer_type_name in globalns:
                outer_type = globalns[outer_type_name]

            if outer_type is None:
                return None

            inner_types = cls._parse_inner_types(inner_type_str)
            resolved_inner_types = []

            for inner_type in inner_types:
                if isinstance(inner_type, str) and inner_type.strip():
                    resolved_inner = cls._resolve_single_forward_ref(
                        inner_type.strip(), globalns, localns
                    )
                    resolved_inner_types.append(resolved_inner or inner_type)
                else:
                    resolved_inner_types.append(inner_type)

            if hasattr(outer_type, "__getitem__"):
                if len(resolved_inner_types) == 1:
                    return outer_type[resolved_inner_types[0]]
                else:
                    return outer_type[tuple(resolved_inner_types)]
            else:
                return outer_type
        except Exception:
            return None

    @classmethod
    def _parse_inner_types(cls, inner_type_str: str) -> List[str]:
        inner_types = []
        depth = 0
        current = []

        for char in inner_type_str:
            if char == "[":
                depth += 1
            elif char == "]":
                depth -= 1
            elif char == "," and depth == 0:
                inner_types.append("".join(current).strip())
                current = []
                continue

            current.append(char)

        if current:
            inner_types.append("".join(current).strip())

        return inner_types

    @classmethod
    def _resolve_forward_ref_instance(
        cls, forward_ref: ForwardRef, globalns: Dict[str, Any], localns: Dict[str, Any]
    ) -> Any:
        try:
            if hasattr(forward_ref, "_evaluate"):
                return get_type_hints(cls, globalns=globalns, localns=localns)
            else:
                return get_type_hints(
                    forward_ref.__forward_arg__, globalns=globalns, localns=localns
                )
        except Exception:
            return None