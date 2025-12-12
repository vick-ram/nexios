from __future__ import annotations

import sys
import builtins
import inspect
import re
from enum import Enum
from dataclasses import dataclass
from typing import (
    Annotated,
    ClassVar,
    Dict,
    List,
    Literal,
    Optional,
    Type,
    TypeVar,
    Any,
    Union,
    dataclass_transform,
    get_args,
    get_origin,
    ForwardRef,
    get_type_hints,
    Callable,
    overload,
)
from pydantic import BaseModel as PydanticBaseModel, ConfigDict
from pydantic.fields import FieldInfo
from pydantic_core import (
    PydanticUndefined as Undefined,
    PydanticUndefinedType as UndefinedType,
)
from nexios.orm.query import ColumnExpression
from pydantic._internal._model_construction import ModelMetaclass as ModelMetaclass

T = TypeVar("T", bound="BaseModel")
ModelType = TypeVar("ModelType", bound="BaseModel")


class RelationshipType(Enum):
    ONE_TO_ONE = "one_to_one"
    ONE_TO_MANY = "one_to_many"
    MANY_TO_ONE = "many_to_one"
    MANY_TO_MANY = "many_to_many"

@dataclass
class ColumnInfo:
    primary_key: bool = False
    foreign_key: Optional[str] = None
    unique: bool = False
    index: bool = False
    auto_increment: bool = False
    nullable: bool = True
    default: Optional[Any] = None
    db_type: Optional[str] = None
    relationship: Optional[Dict[str, Any]] = None


def get_column_info(annotation: Any, info: Any) -> ColumnInfo:
    """Type-safe version with proper validation"""
    column_info = ColumnInfo()

    # Normalize to default and optionally keep FieldInfo for extracting json_schema_extra
    field_info_obj: Optional[FieldInfo] = None
    default = None
    if isinstance(info, FieldInfo):
        field_info_obj = info
        # FieldInfo may store PydanticUndefined as default sentinel
        default = getattr(field_info_obj, "default", None)
    else:
        default = info

    # Set nullable based on default value and type
    column_info.nullable = _determine_nullable(annotation, default)

    if default is Undefined:
        default = None

    # Set nullable based on default value and type
    column_info.nullable = _determine_nullable(annotation, default)

    if field_info_obj is not None:
        column_info = _extract_from_field_info(field_info_obj, column_info, default)

    if get_origin(annotation) is Annotated:
        base_type, *metadata = get_args(annotation)
        for meta in metadata:
            if isinstance(meta, FieldInfo):
                column_info = _extract_from_field_info(meta, column_info, default)
            elif isinstance(meta, ColumnInfo):
                column_info = meta
            elif isinstance(meta, str):
                column_info = _apply_string_metadata(meta, column_info)
            elif isinstance(meta, dict):
                column_info = _apply_dict_metadata(meta, column_info)
    else:
        # Handle non-annotated types
        column_info = _infer_from_type_and_default(annotation, default, column_info)

    return column_info


def _determine_nullable(annotation: Any, default: Any) -> bool:
    """Determine if a field is nullable based on type and default"""
    if default is None:
        return True

    origin = get_origin(annotation)
    return origin is Union and type(None) in get_args(annotation)


def _infer_from_type_and_default(
    annotation: Any, default: Any, column_info: ColumnInfo
) -> ColumnInfo:
    """Infer ORM properties from type and default value"""
    # Auto-increment inference for primary keys with None default
    if (
        column_info.primary_key
        and default is None
        and annotation in (int, Optional[int])
    ):
        column_info.auto_increment = True

    # Handle default values that imply database defaults
    if default is not None:
        column_info.default = default
        if callable(default):
            column_info.default = default()

    return column_info


def _apply_string_metadata(meta: str, column_info: ColumnInfo) -> ColumnInfo:
    """Apply string-based metadata to column info"""
    if meta == "primary_key":
        column_info.primary_key = True
    elif meta == "unique":
        column_info.unique = True
    elif meta == "index":
        column_info.index = True
    elif meta == "auto_increment":
        column_info.auto_increment = True
    elif meta == "nullable":
        column_info.nullable = True
    elif meta == "not_null":
        column_info.nullable = False
    elif meta.startswith("fk:"):
        # Handle foreign key syntax: 'fk:User' or 'fk:User.id'
        fk_parts = meta.split(":")
        if len(fk_parts) > 1:
            column_info.foreign_key = fk_parts[1]

    return column_info


def _apply_dict_metadata(meta: dict, column_info: ColumnInfo) -> ColumnInfo:
    """Apply dictionary metadata to column info"""
    # Handle direct ORM configuration in dict
    if "primary_key" in meta and isinstance(meta["primary_key"], bool):
        column_info.primary_key = meta["primary_key"]

    if "unique" in meta and isinstance(meta["unique"], bool):
        column_info.unique = meta["unique"]

    if "index" in meta and isinstance(meta["index"], bool):
        column_info.index = meta["index"]

    if "auto_increment" in meta and isinstance(meta["auto_increment"], bool):
        column_info.auto_increment = meta["auto_increment"]

    if "foreign_key" in meta and isinstance(meta["foreign_key"], str):
        column_info.foreign_key = meta["foreign_key"]

    if "nullable" in meta and isinstance(meta["nullable"], bool):
        column_info.nullable = meta["nullable"]

    if "db_type" in meta and isinstance(meta["db_type"], str):
        column_info.db_type = meta["db_type"]

    # Handle relationship configuration
    if "relationship" in meta and isinstance(meta["relationship"], dict):
        column_info.relationship = meta["relationship"]

    return column_info


def _extract_from_field_info(
    field_info: FieldInfo, column_info: ColumnInfo, default: Any
) -> ColumnInfo:
    """Safely extract ORM config from FieldInfo"""
    if not field_info.json_schema_extra:
        return column_info

    json_extra = field_info.json_schema_extra

    # Type guard checks
    if not isinstance(json_extra, dict):
        return column_info

    orm_config = json_extra.get("orm")
    if not isinstance(orm_config, dict):
        return column_info

    # Safe extraction with type checking
    if "primary_key" in orm_config and isinstance(orm_config["primary_key"], bool):
        column_info.primary_key = orm_config["primary_key"]
        # If it's a primary key with None default and int type, assume auto-increment
        if column_info.primary_key and default is None:
            column_info.auto_increment = True

    if "unique" in orm_config and isinstance(orm_config["unique"], bool):
        column_info.unique = orm_config["unique"]

    if "index" in orm_config and isinstance(orm_config["index"], bool):
        column_info.index = orm_config["index"]

    if "auto_increment" in orm_config and isinstance(
        orm_config["auto_increment"], bool
    ):
        column_info.auto_increment = orm_config["auto_increment"]

    if "foreign_key" in orm_config and isinstance(orm_config["foreign_key"], str):
        column_info.foreign_key = orm_config["foreign_key"]

    if "nullable" in orm_config and isinstance(orm_config["nullable"], bool):
        column_info.nullable = orm_config["nullable"]

    if "db_type" in orm_config and isinstance(orm_config["db_type"], str):
        column_info.db_type = orm_config["db_type"]

    if "relationship" in orm_config and isinstance(orm_config["relationship"], dict):
        column_info.relationship = orm_config["relationship"]

    if default is not None and default is not Undefined:
        column_info.default = default

    return column_info

# @dataclass_transform(kw_only_default=True, field_specifiers=(Field, ColumnInfo))
class BaseModelMeta(ModelMetaclass):
    def __getattribute__(cls, key):
        if key in ["model_fields", "__dict__", "__pydantic_fields__", "__pydantic_complete__", "model_fields_set"]:
            return super().__getattribute__(key)
        if key not in cls.model_fields:
            return super().__getattribute__(key)
        return ColumnExpression(cls, key) # type: ignore

class ORMConfig:
    def __init__(self):
        self.table_name: Optional[str] = None
        self.database: Optional[str] = "default"
        self.relationships: Dict[str, Dict[str, Any]] = {}
        # self.relationships: Dict[str, RelationshipInfo]
        self.indexes: List[Dict[str, Any]] = []
        self.unique_constraints: List[List[str]] = []
        self.fields: Dict[str, ColumnInfo] = {}
        self.primary_key: Optional[str] = None

    def analyze_fields(self, model_class: Type[BaseModel]):
        """Analyze model fields to extract ORM metadata"""
        self.fields = {}

        for field_name, field_info in model_class.model_fields.items():
            annotation = model_class.__annotations__.get(field_name, Any)
            column_info = get_column_info(annotation, field_info.default)

        for field_name, field_info in model_class.model_fields.items():
            annotation = model_class.__annotations__.get(field_name, Any)
            column_info = get_column_info(annotation, field_info)

            # Store field metadata
            self.fields[field_name] = column_info

            # Track primary key
            if column_info.primary_key:
                self.primary_key = field_name

            # Auto-detect relationships from type hints
            self._detect_relationships(model_class, field_name, annotation, column_info)

    def _detect_relationships(
        self,
        model_class: Type[BaseModel],
        field_name: str,
        annotation: Any,
        column_info: ColumnInfo,
    ):
        """Auto-detect relationships from type annotations"""
        actual_type = annotation

        # Handle Annotated types
        if get_origin(annotation) is Annotated:
            base_type, *metadata = get_args(annotation)
            actual_type = base_type

            # Check for relationship metadata
            for meta in metadata:
                if isinstance(meta, dict) and "relationship" in meta:
                    self.relationships[field_name] = meta["relationship"]
                    return

        # Handle ForwardRefs (string type hints)
        if isinstance(actual_type, str):
            # We'll resolve these in __init_subclass__
            return

        def unwrap_optional(t):
            if get_origin(t) is Union:
                args = [a for a in get_args(t) if a is not type(None)]
                return args[0] if args else t
            return t

        actual_type = unwrap_optional(actual_type)

        # Auto-detect based on type
        if (
            inspect.isclass(actual_type)
            and issubclass(actual_type, BaseModel)
            and field_name not in self.relationships
        ):
            # Many-to-one relationship (ForeignKey)
            if not column_info.foreign_key:
                column_info.foreign_key = f"{actual_type.__name__.lower()}_id"

            self.relationships[field_name] = {
                "type": RelationshipType.MANY_TO_ONE,
                "related_class": actual_type,
                "foreign_key": column_info.foreign_key,
            }

        # Handle List[Model] for one-to-many
        elif get_origin(actual_type) is list or get_origin(actual_type) is List:
            args = get_args(actual_type)
            if args and inspect.isclass(args[0]) and issubclass(args[0], BaseModel):
                related_class = args[0]
                relationship_name = f"{model_class.__name__.lower()}_id"

                self.relationships[field_name] = {
                    "type": RelationshipType.ONE_TO_MANY,
                    "related_class": related_class,
                    "foreign_key": relationship_name,
                }


class BaseModel(PydanticBaseModel, metaclass=BaseModelMeta):
    __orm_config__: ClassVar[ORMConfig] = ORMConfig()
    __session__: ClassVar[Optional[Any]] = None
    __registry__: ClassVar[Dict[str, Type["BaseModel"]]] = {}
    __initialized__: ClassVar[bool] = False
    __fields_cache__: ClassVar[Dict[str, ColumnInfo]] = {}
    is_table: ClassVar[bool] = False

    model_config = ConfigDict(
        arbitrary_types_allowed=True,
        validate_assignment=True,
        from_attributes=True,
        use_enum_values=True,
        protected_namespaces=(),  # Allow __orm_config__ without conflicts
        populate_by_name=True,
    )

    def __init_subclass__(cls, table=False, **kwargs):
        super().__init_subclass__(**kwargs)

        # Initialize ORM config
        cls.__orm_config__ = ORMConfig()

        # Register the class
        cls.__registry__[cls.__name__] = cls

        if not cls.is_table:
            cls.is_table = hasattr(cls, "__tablename__")
        else:
            cls.is_table = table

        if cls.is_table:
            if hasattr(cls, "__tablename__"):
                cls.__orm_config__.table_name = cls.__tablename__  # type: ignore
            else:
                cls.__orm_config__.table_name = cls.__name__.lower() + "s"
        else:
            cls.__orm_config__.table_name = None

        cls.__initialized__ = False

    @classmethod
    def _initialize_orm(cls):
        if getattr(cls, "__initialized__", False):
            return

        if not hasattr(cls, "model_fields") or not cls.model_fields:
            cls.model_fields = cls.model_fields  # type: ignore

        # Analyze fields after class creation
        cls.__orm_config__.analyze_fields(cls)

        # Cache the fields
        cls.__fields_cache__ = cls.__orm_config__.fields.copy()

        # Resolve forward references and relationships
        cls._resolve_forward_references()
        cls._auto_setup_relationships()

        cls.__initialized__ = True

    @classmethod
    def c(cls, field_name: str) -> ColumnExpression:
        return ColumnExpression(cls, field_name)

    @classmethod
    def _resolve_forward_references(cls):
        """Resolve string type annotations to actual classes"""
        globalns = cls._get_global_namespace()
        localns = cls._get_local_namespace()

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

        globalns.update(cls.__registry__)
        module = sys.modules.get(cls.__module__)
        if module:
            globalns.update(getattr(module, "__dict__", {}))
        return globalns

    @classmethod
    def _get_local_namespace(cls) -> Dict[str, Any]:
        """Get local namespace for type resolution"""
        localns = {}

        # Add the class itself and its attributes
        localns[cls.__name__] = cls

        # Add all classes in the same module
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
        """Custom forward reference resolution when built-in fails"""
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
                # Log the error but don't break the whole process
                print(
                    f"Warning: Could not resolve forward reference for {cls.__name__}.{field_name}: {e}"
                )
                continue

    @classmethod
    def _resolve_single_forward_ref(
        cls, annotation: str, globalns: Dict, localns: Dict
    ) -> Any:
        """Resolve a single string forward reference"""
        # Handle generic types like List['User'], Optional['User'], etc.
        if re.match(r"^[A-Z][a-zA-Z_]*\[", annotation):
            return cls._resolve_generic_forward_ref(annotation, globalns, localns)

        # Handle simple type names
        if annotation in localns:
            return localns[annotation]

        if annotation in globalns:
            return globalns[annotation]

        # Try to find in registry by class name
        for key, model_class in cls.__registry__.items():
            if key.endswith(f".{annotation}") or model_class.__name__ == annotation:
                return model_class

        # Try to evaluate the type
        try:
            return get_type_hints(annotation, globalns, localns)
        except Exception:
            pass

        return None

    @classmethod
    def _resolve_generic_forward_ref(
        cls, annotation: str, globalns: Dict, localns: Dict
    ) -> Any:
        """Resolve generic types with forward references"""
        try:
            # Extract the outer type and inner types
            match = re.match(r"^([A-Z][a-zA-Z_]*)\[(.*)\]$", annotation)
            if not match:
                return None

            outer_type_name, inner_types_str = match.groups()

            # Get the outer type
            outer_type = None
            if outer_type_name in localns:
                outer_type = localns[outer_type_name]
            elif outer_type_name in globalns:
                outer_type = globalns[outer_type_name]

            if outer_type is None:
                return None

            # Parse and resolve inner types
            inner_types = cls._parse_inner_types(inner_types_str)
            resolved_inner_types = []

            for inner_type in inner_types:
                if isinstance(inner_type, str) and inner_type.strip():
                    resolved_inner = cls._resolve_single_forward_ref(
                        inner_type.strip(), globalns, localns
                    )
                    resolved_inner_types.append(resolved_inner or inner_type)
                else:
                    resolved_inner_types.append(inner_type)

            # Reconstruct the generic type
            if hasattr(outer_type, "__getitem__"):
                if len(resolved_inner_types) == 1:
                    return outer_type[resolved_inner_types[0]]
                else:
                    return outer_type[tuple(resolved_inner_types)]
            else:
                return outer_type

        except Exception as e:
            return None

    @classmethod
    def _parse_inner_types(cls, inner_types_str: str) -> List[str]:
        """Parse inner types from a generic type string"""
        # Simple parser for generic type arguments
        inner_types = []
        depth = 0
        current = []

        for char in inner_types_str:
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
        cls, forward_ref: ForwardRef, globalns: Dict, localns: Dict
    ) -> Any:
        """Resolve a ForwardRef instance"""
        try:
            # Try Pydantic's method first
            if hasattr(forward_ref, "_evaluate"):
                return get_type_hints(globalns, localns)
                # return forward_ref._evaluate(globalns, localns, recursive_guard=frozenset())

            # Fallback to manual evaluation
            return get_type_hints(forward_ref.__forward_arg__, globalns, localns)
        except Exception as e:
            return None

    @classmethod
    def _auto_setup_relationships(cls):
        """Automatically setup bidirectional relationships"""
        for field_name, relationship in cls.__orm_config__.relationships.items():
            related_class = relationship["related_class"]

            # Setup reverse relationship
            if relationship["type"] == RelationshipType.MANY_TO_ONE:
                # This is a foreign key, setup reverse one-to-many
                reverse_name = cls.__name__.lower() + "s"
                if reverse_name not in related_class.__orm_config__.relationships:
                    related_class.__orm_config__.relationships[reverse_name] = {
                        "type": RelationshipType.ONE_TO_MANY,
                        "related_class": cls,
                        "foreign_key": relationship["foreign_key"],
                    }

            elif relationship["type"] == RelationshipType.ONE_TO_MANY:
                # This is a one-to-many, setup reverse many-to-one
                reverse_name = cls.__name__.lower()
                if reverse_name not in related_class.__orm_config__.relationships:
                    related_class.__orm_config__.relationships[reverse_name] = {
                        "type": RelationshipType.MANY_TO_ONE,
                        "related_class": cls,
                        "foreign_key": relationship["foreign_key"],
                    }

    @classmethod
    def set_session(cls, session: Any):
        cls.__session__ = session

    # Enhanced field access methods
    @classmethod
    def get_primary_key(cls) -> Optional[str]:
        return cls.__orm_config__.primary_key

    @classmethod
    def get_fields(cls) -> Dict[str, ColumnInfo]:
        if not cls.__initialized__:
            cls._initialize_orm()
        return cls.__orm_config__.fields

    @classmethod
    def get_relationships(cls) -> Dict[str, Dict[str, Any]]:
        if not cls.__initialized__:
            cls._initialize_orm()

        return cls.__orm_config__.relationships


def Field(
    default: Optional[Any] = ...,
    title: Optional[str] = None,
    description: Optional[str] = None,
    alias: Optional[str] = None,
    *,
    primary_key: bool = False,
    unique: bool = False,
    index: bool = False,
    auto_increment: Optional[bool] = None,
    foreign_key: Optional[str] = None,
    nullable: Optional[bool] = None,
    db_type: Optional[str] = None,
    relationship: Optional[Dict[str, Any]] = None,
    json_schema_extra: Optional[Dict[str, Any]] = None,
    **kwargs,
) -> Any:
    orm_meta: Dict[str, Any] = {}

    if primary_key:
        orm_meta["primary_key"] = True

    if auto_increment is not None:
        orm_meta["auto_increment"] = auto_increment

    if unique:
        orm_meta["unique"] = True

    if index:
        orm_meta["index"] = True

    if foreign_key:
        orm_meta["foreign_key"] = foreign_key

    if nullable is not None:
        orm_meta["nullable"] = nullable

    if db_type:
        orm_meta["db_type"] = db_type

    if relationship:
        orm_meta["relationship"] = relationship

    extra = dict(json_schema_extra) if json_schema_extra else {}
    existing_orm = (
        extra.get("orm", {}) if isinstance(extra.get("orm", {}), dict) else {}
    )
    merged_orm = {**existing_orm, **orm_meta}
    if merged_orm:
        extra["orm"] = merged_orm

    return FieldInfo(
        default=default,
        alias=alias,
        title=title,
        description=description,
        json_schema_extra=extra,
        **kwargs,
    )

