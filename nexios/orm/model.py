from __future__ import annotations

import re
import types
from packaging import version
from enum import Enum
from dataclasses import dataclass, field
from typing import (
    Union,
    Optional,
    List,
    Type,
    Tuple,
    Dict,
    Callable,
    Any,
    Literal,
    TypeVar,
    ClassVar,
    ForwardRef,
    get_origin,
    get_args,
    dataclass_transform,
    overload,
    cast,
    TYPE_CHECKING,
)
from pydantic import ConfigDict, BaseModel as PydanticBaseModel
import pydantic
from pydantic.fields import FieldInfo as PydanticFieldInfo
from pydantic_core import (
    PydanticUndefined as Undefined,
    PydanticUndefinedType as UndefinedType,
)
from pydantic._internal._repr import Representation
from pydantic._internal._model_construction import ModelMetaclass as ModelMetaclass
from nexios.orm.misc.refs import ResolveForwardRefs
from nexios.orm.misc.store import get_context_data

if TYPE_CHECKING:
    from nexios.orm.query.builder import Select
    from nexios.orm.sessions import AsyncSession

OnDeleteOrUpdate = Literal[
    "CASCADE", "SET NULL", "SET DEFAULT", "RESTRICT", "NO ACTION"
]
LazyOp = Literal["select", "joined", "subquery", "dynamic"]
T = TypeVar("T")
InstanceOrType = Union[T, Type[T]]
_TNexiosModel = TypeVar("_TNexiosModel", bound="NexiosModel")

PYDANTIC_VERSION = version.parse(pydantic.__version__)

IS_PYDANTIC_V2 = PYDANTIC_VERSION.major >= 2

_NOT_LOADED = object()

class NexiosModelConfig(ConfigDict, total=False):
    table: Optional[bool]


def get_config_value(
        *, model: InstanceOrType[_TNexiosModel], parameter: str, default: Any = None
) -> Any:
    if IS_PYDANTIC_V2:
        return model.model_config.get(parameter, default)
    else:
        return getattr(model.__config__, parameter, default)


def set_config_value(
        *, model: InstanceOrType[_TNexiosModel], parameter: str, value: Any
) -> None:
    if IS_PYDANTIC_V2:
        model.model_config[parameter] = value
    else:
        setattr(model.__config__, parameter, value)


def get_tablename_for_class(cls: Any) -> Optional[str]:
    if hasattr(cls, "__tablename__") and cls.__tablename__ is not None:
        return cls.__tablename__

    table = get_config_value(model=cls, parameter="table", default=False)
    if table is True and (hasattr(cls, "model_config") or hasattr(cls, '__config__')):
        tablename = (
            f"{cls.__name__.lower()}" if cls.__name__.lower().endswith('s')
            else f"{cls.__name__.lower()}s"
        )
        return tablename

    return None

def _to_snake_case(name: str) -> str:
        """Converts CamelCase to snake_case."""
        s1 = re.sub('(.)([A-Z][a-z]+)', r'\1_\2', name)
        return re.sub('([a-z0-9])([A-Z])', r'\1_\2', s1).lower()

class RelationshipType(Enum):
    ONE_TO_ONE = "one_to_one"
    ONE_TO_MANY = "one_to_many"
    MANY_TO_ONE = "many_to_one"
    MANY_TO_MANY = "many_to_many"


class FieldInfo(PydanticFieldInfo):
    def __init__(self, default: Any = Undefined, **kwargs: Any) -> None:
        primary_key = kwargs.pop("primary_key", Undefined)
        nullable = kwargs.pop("nullable", Undefined)
        foreign_key = kwargs.pop("foreign_key", Undefined)
        ondelete = kwargs.pop("ondelete", Undefined)
        unique = kwargs.pop("unique", Undefined)
        index = kwargs.pop("index", Undefined)
        auto_increment = kwargs.pop("auto_increment", False)

        if auto_increment and default is Undefined:
            default = None

        super().__init__(default=default, **kwargs)
        self.primary_key = primary_key
        self.nullable = nullable
        self.foreign_key = foreign_key
        self.ondelete = ondelete
        self.unique = unique
        self.index = index
        self.auto_increment = auto_increment


@dataclass
class RelationshipInfo(Representation):
    """Information about a relationship between models."""

    field_name: str
    related_model_name: str  # Store as string to avoid circular imports
    relationship_type: RelationshipType
    foreign_key: Optional[str] = None
    related_field_name: Optional[str] = None
    through: Optional[str] = None  # Store as string
    ondelete: Optional[OnDeleteOrUpdate] = None
    onupdate: Optional[OnDeleteOrUpdate] = None
    nullable: bool = False
    unique: bool = False
    back_populates: Optional[str] = None
    lazy: LazyOp = "select"

    # Database constraints
    deferrable: Optional[bool] = None
    initially_deferred: Optional[bool] = None

    # For many-to-many relationships
    association_table: Optional[str] = None
    local_column: Optional[str] = None
    foreign_column: Optional[str] = None

    # For tracking
    is_resolved: bool = False
    metadata: Dict[str, Any] = field(default_factory=dict)

    # Cache for resolved models
    _related_model: Optional[Type["NexiosModel"]] = None
    _through_model: Optional[Type["NexiosModel"]] = None

    @property
    def through_model(self) -> Optional[Type["NexiosModel"]]:
        if self._through_model is None and self.through:
            try:
                if (
                        hasattr(NexiosModel, "__registry__")
                        and self.through in NexiosModel.__registry__
                ):
                    self._through_model = NexiosModel.__registry__[self.through]
            except (AttributeError, KeyError):
                pass
        return self._through_model

    @property
    def related_model(self) -> Optional[Type["NexiosModel"]]:
        if self._related_model is None and self.related_model_name:
            try:
                if (
                        hasattr(NexiosModel, "__registry__")
                        and self.related_model_name in NexiosModel.__registry__
                ):
                    self._related_model = NexiosModel.__registry__[
                        self.related_model_name
                    ]
            except (AttributeError, KeyError):
                pass
        return self._related_model


@overload
def Field(
        default: Any = Undefined,
        *,
        default_factory: Optional[Callable[[], Any]] = None,
        title: Optional[str] = None,
        description: Optional[str] = None,
        alias: Optional[str] = None,
        const: Optional[bool] = None,
        gt: Optional[float] = None,
        ge: Optional[float] = None,
        lt: Optional[float] = None,
        le: Optional[float] = None,
        multiple_of: Optional[float] = None,
        max_digits: Optional[int] = None,
        decimal_places: Optional[int] = None,
        min_items: Optional[int] = None,
        max_items: Optional[int] = None,
        unique_items: Optional[bool] = None,
        min_length: Optional[int] = None,
        max_length: Optional[int] = None,
        allow_mutation: bool = True,
        regex: Optional[str] = None,
        discriminator: Optional[str] = None,
        repr: bool = True,
        primary_key: Union[bool, UndefinedType] = Undefined,
        auto_increment: bool = False,
        foreign_key: Any = Undefined,
        unique: Union[bool, UndefinedType] = Undefined,
        nullable: Union[bool, UndefinedType] = Undefined,
        index: Union[bool, UndefinedType] = Undefined,
        schema_extra: Optional[Dict[str, Any]] = None,
) -> Any: ...


@overload
def Field(
        default: Any = Undefined,
        *,
        default_factory: Optional[Callable[[], Any]] = None,
        title: Optional[str] = None,
        description: Optional[str] = None,
        alias: Optional[str] = None,
        const: Optional[bool] = None,
        gt: Optional[float] = None,
        ge: Optional[float] = None,
        lt: Optional[float] = None,
        le: Optional[float] = None,
        multiple_of: Optional[float] = None,
        max_digits: Optional[int] = None,
        decimal_places: Optional[int] = None,
        min_items: Optional[int] = None,
        max_items: Optional[int] = None,
        unique_items: Optional[bool] = None,
        min_length: Optional[int] = None,
        max_length: Optional[int] = None,
        allow_mutation: bool = True,
        regex: Optional[str] = None,
        discriminator: Optional[str] = None,
        repr: bool = True,
        primary_key: Union[bool, UndefinedType] = Undefined,
        auto_increment: bool = False,
        foreign_key: str,
        ondelete: Union[OnDeleteOrUpdate, UndefinedType] = Undefined,
        onupdate: Union[OnDeleteOrUpdate, UndefinedType] = Undefined,
        unique: Union[bool, UndefinedType] = Undefined,
        nullable: Union[bool, UndefinedType] = Undefined,
        index: Union[bool, UndefinedType] = Undefined,
        schema_extra: Optional[Dict[str, Any]] = None,
) -> Any: ...


def Field(
        default: Any = Undefined,
        *,
        default_factory: Optional[Callable[[], Any]] = None,
        title: Optional[str] = None,
        description: Optional[str] = None,
        alias: Optional[str] = None,
        const: Optional[bool] = None,
        gt: Optional[float] = None,
        ge: Optional[float] = None,
        lt: Optional[float] = None,
        le: Optional[float] = None,
        multiple_of: Optional[float] = None,
        max_digits: Optional[int] = None,
        decimal_places: Optional[int] = None,
        min_items: Optional[int] = None,
        max_items: Optional[int] = None,
        unique_items: Optional[bool] = None,
        min_length: Optional[int] = None,
        max_length: Optional[int] = None,
        allow_mutation: bool = True,
        regex: Optional[str] = None,
        discriminator: Optional[str] = None,
        repr: bool = True,
        primary_key: Union[bool, UndefinedType] = Undefined,
        auto_increment: bool = False,
        foreign_key: Any = Undefined,
        ondelete: Union[OnDeleteOrUpdate, UndefinedType] = Undefined,
        onupdate: Union[OnDeleteOrUpdate, UndefinedType] = Undefined,
        unique: Union[bool, UndefinedType] = Undefined,
        nullable: Union[bool, UndefinedType] = Undefined,
        index: Union[bool, UndefinedType] = Undefined,
        schema_extra: Optional[Dict[str, Any]] = None,
) -> Any:
    current_schema_extra = schema_extra or {}

    field_info = FieldInfo(
        default,
        default_factory=default_factory,
        alias=alias,
        title=title,
        description=description,
        const=const,
        gt=gt,
        ge=ge,
        lt=lt,
        le=le,
        multiple_of=multiple_of,
        max_digits=max_digits,
        decimal_places=decimal_places,
        min_items=min_items,
        max_items=max_items,
        unique_items=unique_items,
        min_length=min_length,
        max_length=max_length,
        allow_mutation=allow_mutation,
        regex=regex,
        discriminator=discriminator,
        repr=repr,
        primary_key=primary_key,
        auto_increment=auto_increment,
        foreign_key=foreign_key,
        ondelete=ondelete,
        onupdate=onupdate,
        unique=unique,
        nullable=nullable,
        index=index,
        **current_schema_extra,
    )
    return field_info


# For one-to-one, one-to-many and many-to-one
@overload
def Relationship(
        related_model: Union[Type[NexiosModel], str, None] = None,
        relationship_type: Literal[
            RelationshipType.MANY_TO_ONE,
            RelationshipType.ONE_TO_MANY,
            RelationshipType.ONE_TO_ONE,
        ] = RelationshipType.MANY_TO_ONE,
        *,
        foreign_key: Optional[str] = None,
        related_field_name: Optional[str] = None,
        **kwargs: Any,
) -> Any: ...


# For many-to-many with through model
@overload
def Relationship(
        related_model: Union[Type[NexiosModel], str, None] = None,
        relationship_type: Literal[
            RelationshipType.MANY_TO_MANY
        ] = RelationshipType.MANY_TO_MANY,
        *,
        through: Union[Type["NexiosModel"], str, None] = None,
        local_column: Optional[str] = None,
        foreign_column: Optional[str] = None,
        **kwargs: Any,
) -> Any: ...


def Relationship(
        related_model: Union[Type[NexiosModel], str, None] = None,
        relationship_type: Optional[RelationshipType] = None,
        *,
        foreign_key: Optional[str] = None,
        related_field_name: Optional[str] = None,
        through: Optional[Union[Type["NexiosModel"], str]] = None,
        ondelete: Optional[OnDeleteOrUpdate] = None,
        onupdate: Optional[OnDeleteOrUpdate] = None,
        nullable: bool = False,
        unique: bool = False,
        back_populates: Optional[str] = None,
        lazy: LazyOp = "select",
        deferrable: Optional[bool] = None,
        initially_deferred: Optional[bool] = None,
        local_column: Optional[str] = None,
        foreign_column: Optional[str] = None,
        **kwargs: Any,
) -> Any:
    rel_model_str = None
    if related_model:
        rel_model_str = (
            related_model if isinstance(related_model, str) else related_model.__name__
        )
    through_model_str = None
    if through:
        through_model_str = (
            through
            if isinstance(through, str)
            else through.__name__
            if through
            else None
        )

    return RelationshipInfo(
        field_name="",
        related_model_name=rel_model_str or "",
        relationship_type=relationship_type or RelationshipType.MANY_TO_ONE,
        foreign_key=foreign_key,
        related_field_name=related_field_name,
        through=through_model_str,
        ondelete=ondelete,
        onupdate=onupdate,
        nullable=nullable,
        unique=unique,
        back_populates=back_populates,
        lazy=lazy,
        deferrable=deferrable,
        initially_deferred=initially_deferred,
        local_column=local_column,
        foreign_column=foreign_column,
        metadata=kwargs,
    )


@dataclass_transform(kw_only_default=True, field_specifiers=(Field, FieldInfo))
class NexiosModelMetaclass(ModelMetaclass):
    __relationships__: Dict[str, RelationshipInfo] = {}
    model_config: NexiosModelConfig
    model_fields: Dict[str, FieldInfo] = {}
    __config__: Type[NexiosModelConfig]

    def __setattr__(cls, name: str, value: Any) -> None:
        super().__setattr__(name, value)

    def __delattr__(cls, name: str) -> None:
        super().__delattr__(name)

    def __getattribute__(cls, key):
        from nexios.orm.query.expressions import ColumnExpression

        if key in ["model_fields", "__dict__", "__pydantic_fields__"]:
            return super().__getattribute__(key)

        if key in cls.model_fields:
            return ColumnExpression(cls, key)  # type: ignore

        return super().__getattribute__(key)

    def __new__(
            mcs,
            name: str,
            bases: Tuple[Type[Any], ...],
            namespace: Dict[str, Any],
            **kwargs: Any,
    ):
        namespace["__relationships__"] = {}

        relationships: Dict[str, RelationshipInfo] = {}
        relationship_items = {}
        pydantic_dict = {}
        original_annotations = namespace.get("__annotations__", {})
        pydantic_annotations = {}
        relationship_annotations = {}

        for k, v in namespace.items():
            if isinstance(v, RelationshipInfo):
                relationship_items[k] = v
                relationship_annotations[k] = original_annotations.get(k)
            else:
                pydantic_dict[k] = v
                if k in original_annotations:
                    pydantic_annotations[k] = original_annotations.get(k)
        dict_used = {
            **pydantic_dict,
            "__annotations__": pydantic_annotations,
        }
        allowed_config_keys = {"read_from_attributes", "from_attributes", "table"}

        config_kwargs = {
            key: kwargs[key]
            for key in kwargs.keys() & allowed_config_keys
        }
        for k in list(kwargs.keys()):
            if k in allowed_config_keys:
                config_kwargs[k] = kwargs.pop(k)

        cls = super().__new__(mcs, name, bases, dict_used, **config_kwargs)

        for attr_name, rel_info in relationship_items.items():
            mcs._process_relationship(
                cls, attr_name, rel_info, original_annotations, relationships
            )

        cls.__relationships__ = relationships

        cls.__annotations__ = {
            **relationship_annotations,
            **pydantic_annotations,
            **cls.__annotations__,
        }

        cls.resolve_forward_references()
        return cls

    @classmethod
    def _process_relationship(
            mcs,
            cls: Type[NexiosModel],
            attr_name: str,
            rel_info: RelationshipInfo,
            original_annotations: Dict[str, Any],
            relationships: Dict[str, RelationshipInfo],
    ):
        annotation = original_annotations.get(attr_name)
        # Parse relationship
        parsed_info = mcs._parse_relationship_annotation(annotation, rel_info)
        # Determine related model
        related_model_name = mcs._determine_related_model(parsed_info, rel_info)
        if not related_model_name:
            raise ValueError(
                f"Could not determine related model for relationship '{attr_name}' "
                f"in class '{cls.__name__}'"
            )
        # Determine relationship type
        relationship_type = mcs._determine_relationship_type(
            parsed_info, rel_info, attr_name
        )

        # Determine foreign key
        foreign_key = mcs._determine_foreign_key(
            rel_info, relationship_type, cls.__name__, related_model_name
        )

        # Resolve through model if provided
        through = mcs._resolve_through_model(rel_info)

        association_table = None
        if rel_info.through:
            if isinstance(rel_info.through, str):
                association_table = rel_info.through
            elif hasattr(rel_info.through, "__tablename__") and rel_info.through.__tablename__:
                association_table = rel_info.through.__tablename__
            else:
                association_table = getattr(rel_info.through, "__name__", None)

        # reate final relationship info
        final_info = RelationshipInfo(
            field_name=attr_name,
            related_model_name=related_model_name,
            relationship_type=relationship_type,
            foreign_key=foreign_key,
            related_field_name=rel_info.related_field_name,
            through=through,
            ondelete=rel_info.ondelete,
            onupdate=rel_info.onupdate,
            nullable=rel_info.nullable,
            unique=rel_info.unique,
            back_populates=rel_info.back_populates,
            lazy=rel_info.lazy,
            deferrable=rel_info.deferrable,
            initially_deferred=rel_info.initially_deferred,
            association_table=association_table,
            local_column=rel_info.local_column,
            foreign_column=rel_info.foreign_column,
            metadata=rel_info.metadata,
        )
        relationships[attr_name] = final_info
        setattr(cls, attr_name, RelationshipDescriptor(cls, attr_name, final_info))

    @classmethod
    def _parse_relationship_annotation(
            mcs, annotation: Any, rel_info: RelationshipInfo
    ) -> Dict[str, Any]:
        result = {
            "related_model": None,
            "relationship_type": None,
            "is_optional": False,
            "is_list": False,
        }

        if annotation is None:
            return result

        def normalize_annotation(ann: str) -> str:
            return (
                ann
                .replace("typing.", "")
                .replace("typing_extensions.", "")
            )

        # String annotations
        if isinstance(annotation, str):
            annotation = annotation.replace(" ", "")

            # Optional[T]
            normalized_annotation = normalize_annotation(annotation)
            if normalized_annotation.startswith(("Optional[", "Union[")):
                result["is_optional"] = True
                inner = normalized_annotation[normalized_annotation.find("[") + 1: -1]
                return mcs._parse_relationship_annotation(inner, rel_info)

            # List[T]
            if normalized_annotation.startswith(("List[", "list[")):
                result["is_list"] = True
                inner = normalized_annotation[normalized_annotation.find("[") + 1: -1].strip("\"'")
                result["related_model"] = inner
                result["relationship_type"] = RelationshipType.ONE_TO_MANY
                return result

            # Bare types
            result["related_model"] = annotation.strip("\"'")

            if rel_info.relationship_type:
                result["relationship_type"] = rel_info.relationship_type
            else:
                result["relationship_type"] = RelationshipType.MANY_TO_ONE
            return result

        # typing objects
        origin = get_origin(annotation)
        args = get_args(annotation)

        # Optional[T]
        if origin is Union:
            result["is_optional"] = True
            for arg in args:
                if arg is type(None):
                    continue
                nested = mcs._parse_relationship_annotation(arg, rel_info)
                result.update(nested)
                return result

        # List[T]
        if origin in (list, List):
            result["is_list"] = True
            if args:
                arg = args[0]
                if isinstance(arg, str):
                    result["related_model"] = arg
                elif isinstance(arg, ForwardRef):
                    result["related_model"] = arg.__forward_arg__
                elif isinstance(arg, type):
                    result["related_model"] = arg.__name__
            result["relationship_type"] = RelationshipType.ONE_TO_MANY
            return result

        # ForwardRef
        if isinstance(annotation, ForwardRef):
            result["related_model"] = annotation.__forward_arg__
            if rel_info.relationship_type:
                result["relationship_type"] = rel_info.relationship_type
            else:
                result["relationship_type"] = RelationshipType.MANY_TO_ONE
            return result

        # type directly
        if isinstance(annotation, type):
            result["related_model"] = annotation.__name__
            if rel_info.relationship_type:
                result["relationship_type"] = rel_info.relationship_type
            else:
                result["relationship_type"] = RelationshipType.MANY_TO_ONE
            return result

        return result

    @classmethod
    def _determine_related_model(
            mcs, parsed_info: Dict[str, Any], rel_info: RelationshipInfo
    ) -> Optional[str]:
        if rel_info.related_model:
            if isinstance(rel_info.related_model, str):
                return rel_info.related_model
            return rel_info.related_model.__name__

        if parsed_info.get("related_model"):
            return parsed_info["related_model"]

        return rel_info.related_model_name

    @classmethod
    def _determine_relationship_type(
            mcs, parsed_info: Dict[str, Any], rel_info: RelationshipInfo, attr_name: str
    ) -> RelationshipType:
        rel_type: RelationshipType = RelationshipType.MANY_TO_ONE

        if rel_info.relationship_type:
            rel_type = rel_info.relationship_type

        if parsed_info.get("relationship_type"):
            rel_type =  parsed_info["relationship_type"]
        
        if parsed_info.get("is_list"):
            rel_type = RelationshipType.ONE_TO_MANY

        if rel_info.unique:
            rel_type = RelationshipType.ONE_TO_ONE
        
        if not parsed_info.get("is_list") and rel_type == RelationshipType.MANY_TO_ONE:
            rel_type = RelationshipType.ONE_TO_ONE

        return rel_type

    @classmethod
    def _determine_foreign_key(
            mcs,
            rel_info: RelationshipInfo,
            relationship_type: RelationshipType,
            current_model_name: str,
            related_model_name: str
    ) -> Optional[str]:

        if rel_info.foreign_key:
            return rel_info.foreign_key

        current_cls = None
        try:
            current_cls = mcs.__registry__.get(current_model_name) # type: ignore
        except AttributeError:
            current_cls = None
        
        def fk_matches_target(fk_val: Any, target_name: str) -> bool:
            if not fk_val:
                return False
            if isinstance(fk_val, str):
                fk_s = fk_val.strip()
                if "." in fk_s:
                    left, _ = fk_s.rsplit(".", 1)
                    left_l = left.lower()
                    candidates = {
                        target_name.lower(),
                        _to_snake_case(target_name),
                        (get_tablename_for_class(mcs.__registry__.get(target_name)) or "").lower() # type: ignore
                    }
                    return left_l in candidates
                else:
                    if fk_s == f"{_to_snake_case(target_name)}_id" or fk_s == "id":
                        return True
            return False
        
        if current_cls is not None:
            try:
                for field_name, field_info in get_model_fields(current_cls).items():
                    fk = getattr(field_info, "foreign_key", Undefined)
                    if fk is not Undefined and fk:
                        if fk_matches_target(fk, related_model_name):
                            return field_name
            except Exception:
                pass
        
        current = _to_snake_case(current_model_name)
        related = _to_snake_case(related_model_name)

        fk = f"{related}_id"
        
        match (relationship_type):
            case RelationshipType.MANY_TO_ONE:
                return fk if current_cls is not None and fk in get_model_fields(current_cls) else None
            case RelationshipType.ONE_TO_ONE:
                return fk if current_cls is not None and fk in get_model_fields(current_cls) else None
            case RelationshipType.ONE_TO_MANY:
                return None
            case RelationshipType.MANY_TO_MANY:
                return None
            case _:
                return None

    @classmethod
    def _resolve_through_model(mcs, rel_info: RelationshipInfo) -> Optional[str]:
        if rel_info.through is None:
            return None

        if isinstance(rel_info.through, str):
            return rel_info.through

        if hasattr(rel_info.through, "__name__"):
            return rel_info.through.__name__

        return str(rel_info.through)


class RelationshipDescriptor:
    def __init__(
            self,
            model_class: Type[NexiosModel],
            field_name: str,
            relationship_info: Optional[RelationshipInfo] = None,
    ) -> types.NoneType:
        self.model_class = model_class
        self.field_name = field_name

        if relationship_info is not None:
            self._relationship_info = relationship_info
        else:
            self._relationship_info = model_class.__relationships__[
                field_name
            ]

    def __get__(self, obj: Optional[NexiosModel], objType: Type[NexiosModel]):
        if obj is None:
            return self
        
        cached = self._get_cache(obj)
        if cached is not _NOT_LOADED:
            return cached
        
        session = get_context_data('session')
        if not session:
            raise RuntimeError(
                f"No session available for loading relationship '{self.field_name}'. "
                f"Make sure you're inside a session context manager."
            )

        if self._relationship_info.lazy == "select":
            return self._load_select_lazy(obj, session)
        elif self._relationship_info.lazy == "joined":
            return self._load_select_lazy(obj, session)
        elif self._relationship_info.lazy == "dynamic":
            return self._load_dynamic(obj, session)
        elif self._relationship_info.lazy == "subquery":
            return self._load_subquery(obj, session)
        else:
            return self._load_select_lazy(obj, session)

    def __set__(self, obj: NexiosModel, value: Any):
        """Set relationship value and update foreign key if applicable."""
        # clear cache
        self._clear_cache(obj)
        self._set_cache(obj, value)

        # If setting to None, clear foreign key and return
        if value is None:
            if self._relationship_info.foreign_key:
                fk_field = self._relationship_info.foreign_key or self._find_local_foreign_key()
                if fk_field and hasattr(obj, fk_field):
                    setattr(obj, fk_field, None)
            return
        
        # set the new value in cache
        # self._set_cache(obj, value)

        local_fk = self._relationship_info.foreign_key or self._find_local_foreign_key()
        if local_fk:
            pk_val = getattr(value, self._get_pk_field(value), None)
            setattr(obj, local_fk, pk_val)

        # update foreign key on the owning side
        # if self._relationship_info.foreign_key:
        #     fk_field = self._relationship_info.foreign_key
        #     if hasattr(obj, fk_field):
        #         if value is None:
        #             setattr(obj, fk_field, None)
        #         else:
        #             pk_name = self._get_pk_field(value)
        #             pk_value = getattr(value, pk_name, None)
        #             setattr(obj, fk_field, pk_value)
        
        if self._relationship_info.back_populates:
            back_field = self._relationship_info.back_populates
            
            if hasattr(value.__class__, back_field):
                back_desc = getattr(value.__class__, back_field, None)

                if isinstance(back_desc, RelationshipDescriptor):
                    back_desc._set_cache(value, obj)
                    remote_fk = back_desc._relationship_info.foreign_key or back_desc._find_local_foreign_key()
                    if remote_fk:
                        obj_pk_name = self._get_pk_field(obj)
                        obj_pk_value = getattr(obj, obj_pk_name, None)
                        setattr(value, remote_fk, obj_pk_value)
                else:
                    setattr(value, back_field, obj)
    
    def _find_local_foreign_key(self) -> Optional[str]:
        related_model = self._relationship_info.related_model
        if not related_model:
            return None
        
        return self._find_foreign_key_on_related(related_model, self.model_class)
    
    def _set_cache(self, obj: NexiosModel, value: Any) -> None:
        if "__relationship_cache__" not in obj.__dict__:
            obj.__dict__["__relationship_cache__"] = {}
        obj.__dict__["__relationship_cache__"][self.field_name] = value
    
    def _get_cache(self, obj: NexiosModel) -> Any:
        """Get cached relationship value if exists."""
        relationship_cache = obj.__dict__.get("__relationship_cache__", {})
        return relationship_cache.get(self.field_name, _NOT_LOADED)
    
    def _clear_cache(self, obj: NexiosModel) -> None:
        """Clear existing cache"""
        if "__relationship_cache__" in obj.__dict__:
            if self.field_name in obj.__dict__["__relationship_cache__"]:
                del obj.__dict__["__relationship_cache__"][self.field_name]

    def _get_pk_field(self, model: InstanceOrType[NexiosModel]) -> Any:
        """Helper to safely get primary key."""
        pk = model.get_primary_key()
        return pk[0] if isinstance(pk, (list, tuple)) else pk
    
    def _find_foreign_key_on_related(self, related_model: Type[NexiosModel], current_model_class: Type[NexiosModel]) -> str:
        expected_name = f"{_to_snake_case(current_model_class.__name__)}_id"
        pk_name = self._get_pk_field(current_model_class)
        related_fields = get_model_fields(related_model)

        # Check explicit foreign key metadata first
        for field_name, field_info in related_fields.items():
            fk = getattr(field_info, "foreign_key", Undefined)
            if fk is not Undefined and fk:
                # fk could be "table.col" or just "col"
                if isinstance(fk, str):
                    fk_s = fk.strip()
                    if "." in fk_s:
                        left, _ = fk_s.rsplit(".", 1)
                        left_l = left.lower()
                        tablename = (get_tablename_for_class(current_model_class) or "").lower()
                        candidates = {current_model_class.__name__.lower(), _to_snake_case(current_model_class.__name__), tablename}
                        if left_l in candidates:
                            return field_name
                    else:
                        # matches column name (id, user_id, etc)
                        if fk_s == expected_name or fk_s == str(pk_name) or fk_s == field_name:
                            return field_name
        
        # fallback: find by naming convention on the related model's field names
        for field_name in related_fields.keys():
            if field_name == expected_name:
                return field_name
            if pk_name and field_name.endswith(f"_{pk_name}"):
                return field_name
        
        # last resort: if attribute exists on the related model, return it, else return the convention name
        if hasattr(related_model, expected_name):
            return expected_name
        
        return expected_name

    def _load_select_lazy(self, obj: NexiosModel, session: Any) -> Any:
        rel_type = self._relationship_info.relationship_type

        print(f"Loading relationship '{self.field_name}' of type '{rel_type.value}' using select lazy strategy.")

        if rel_type == RelationshipType.MANY_TO_ONE:
            return self._load_many_to_one(obj, session)
        elif rel_type == RelationshipType.ONE_TO_MANY:
            return self._load_one_to_many(obj, session)
        elif rel_type == RelationshipType.MANY_TO_MANY:
            return self._load_many_to_many(obj, session)
        else:  # ONE_TO_ONE
            return self._load_one_to_one(obj, session)

    def _load_subquery(self, obj: NexiosModel, session: Any) -> Any:
        """Load using subquery loading strategy."""
        return self._load_select_lazy(obj, session)

    def _load_many_to_one(self, obj: NexiosModel, session: Any) -> Any:
        from nexios.orm.misc.event_loop import NexiosEventLoop
        from nexios.orm.query.builder import select
        from nexios.orm.sessions import AsyncSession

        cached = self._get_cache(obj)
        if cached is not _NOT_LOADED:
            return cached


        loop = NexiosEventLoop()
        result: Optional[NexiosModel] = None

        related_model = self._relationship_info.related_model

        fk_field_name = self._relationship_info.foreign_key
        if not fk_field_name:
            raise ValueError(f"No foreign key defined for relationship {self._relationship_info.field_name}")

        fk_value = getattr(obj, fk_field_name, None)
        if fk_value is None:
            result = None
        
        assert related_model is not None

        related_pk_field = self._get_pk_field(related_model)

        query = select(related_model).where(
            getattr(related_model, related_pk_field) == fk_value
        )

        query._bind(session)

        if isinstance(session, AsyncSession):

            async def async_fetch():
                return await query._first_async()

            result = loop.run(async_fetch())
        else:
            result = query._first()
        
        # Cache the result
        self._set_cache(obj, result)
        
        return result

    def _load_one_to_many(self, obj: NexiosModel, session: Any) -> Any:
        from nexios.orm.misc.event_loop import NexiosEventLoop
        from nexios.orm.query.builder import select
        from nexios.orm.sessions import AsyncSession

        cached = self._get_cache(obj)
        if cached is not _NOT_LOADED:
            return cached

        loop = NexiosEventLoop()
        results: List[NexiosModel] = []
        related_model = self._relationship_info.related_model

        pk_name = self._get_pk_field(obj)
        pk_value = getattr(obj, pk_name, None)

        if related_model is None:
            raise ValueError("Related model is None")

        fk_field_name = self._find_foreign_key_on_related(related_model, obj.__class__)

        query = select(related_model).where(
            getattr(related_model, fk_field_name) == pk_value
        )

        # Bind and execute
        query._bind(session)

        if isinstance(session, AsyncSession):
            async def async_fetch():
                return await query._all_async()  # type: ignore

            results = loop.run(async_fetch())
        else:
            results = query._all()
        
        # Cache the results
        self._set_cache(obj, results)
        
        return results
        
 
    def _load_one_to_one(self, obj: NexiosModel, session: Any) -> Any:
        # return self._load_many_to_one(obj, session)
        from nexios.orm.misc.event_loop import NexiosEventLoop
        from nexios.orm.query.builder import select
        from nexios.orm.sessions import AsyncSession

        cached = self._get_cache(obj)
        print(f"Cached data: {cached}")
        if cached is not _NOT_LOADED:
            return cached
    
        loop = NexiosEventLoop()
        result: Optional[NexiosModel] = None
        related_model = self._relationship_info.related_model

        assert related_model is not None
        
        # Check if this is the side with the foreign key
        if self._relationship_info.foreign_key:
            # This side has the foreign key (like many-to-one)
            fk_field_name = self._relationship_info.foreign_key
            fk_value = getattr(obj, fk_field_name, None)
            
            if fk_value is None:
                result = None
            
            related_pk = self._get_pk_field(related_model)
            
            query = select(related_model).where(
                getattr(related_model, related_pk) == fk_value
            )
        else:
            # This side doesn't have foreign key, related side does
            pk_field_name = self._get_pk_field(obj)
            pk_value = getattr(obj, pk_field_name, None)

            if pk_value is None:
                result = None
            
            # Find the foreign key field on related model
            fk_field_name = self._find_foreign_key_on_related(related_model, obj.__class__)
            
            query = select(related_model).where(
                getattr(related_model, fk_field_name) == pk_value
            )
        
        query._bind(session)
        
        if isinstance(session, AsyncSession):
            async def async_fetch():
                return await query._first_async()
            result = loop.run(async_fetch())
        else:
            result = query._first()
        
        # Cache the result
        self._set_cache(obj, result)
        
        return result

    def _load_many_to_many(self, obj: NexiosModel, session: Any) -> List[Any]:
        from nexios.orm.misc.event_loop import NexiosEventLoop
        from nexios.orm.query.builder import select
        from nexios.orm.sessions import AsyncSession

        cached = self._get_cache(obj)
        if cached is not _NOT_LOADED:
            return cached

        loop = NexiosEventLoop()
        results: List[NexiosModel] = []
        related_model = self._relationship_info.related_model
        through_model = self._relationship_info.through_model

        association_table = self._relationship_info.association_table
    
        if not association_table:
            raise ValueError(f"No association table defined for many-to-many relationship {self._relationship_info.field_name}")

        if not through_model:
            raise ValueError(
                f"No through model specified for many-to-many relationship '{self.field_name}'"
            )

        pk_name = self._get_pk_field(obj)
        pk_value = getattr(obj, pk_name, None)

        assert related_model is not None

        related_pk = self._get_pk_field(related_model)

        assert related_model is not None

        local_col = (
                self._relationship_info.local_column
                or f"{_to_snake_case(obj.__class__.__name__)}_id"
        )
        foreign_col = (
                self._relationship_info.foreign_column
                or f"{_to_snake_case(related_model.__name__)}_id"
        )

        query_ids = select(getattr(through_model, foreign_col)).where(
            getattr(through_model, local_col) == pk_value
        )

        query_ids._bind(session)

        def _fetch_m2m():
            from nexios.orm.sessions import AsyncSession
            
            if isinstance(session, AsyncSession):
                # This needs to be run inside the loop
                async def _async_logic():
                    rows = await query_ids._all_async()
                    ids = [row[0] if isinstance(row, (list, tuple)) else row for row in rows]
                    if not ids:
                        return []
                    q = select(related_model).where(getattr(related_model, related_pk).in_(ids))
                    q._bind(session)
                    return await q._all_async()
                return loop.run(_async_logic())
            else:
                rows = query_ids._all()
                ids = [row[0] if isinstance(row, (list, tuple)) else row for row in rows]
                if not ids:
                    return []
                q = select(related_model).where(getattr(related_model, related_pk).in_(ids))
                q._bind(session)
                return q._all()
            
        results = _fetch_m2m()
        self._set_cache(obj, results)
        return results

    def _load_dynamic(self, obj: NexiosModel, session: Any) -> Select:
        from nexios.orm.query.builder import select, Select
        from nexios.orm.sessions import AsyncSession

        from nexios.orm.misc.event_loop import NexiosEventLoop

        _loop = NexiosEventLoop()

        pk_name = self._get_pk_field(obj)
        pk_value = getattr(obj, pk_name, None)

        related_model = self._relationship_info.related_model

        if self._relationship_info.relationship_type == RelationshipType.ONE_TO_MANY:

            assert related_model is not None
            fk_field_name = self._find_foreign_key_on_related(related_model, obj.__class__)

            query = select(related_model).where(
                getattr(related_model, fk_field_name) == pk_value
            )

            query._bind(session)
            return query
        elif self._relationship_info.relationship_type == RelationshipType.MANY_TO_MANY:
            through_model = self._relationship_info.through_model
            if not through_model:
                raise ValueError("No through model for many-to-many dynamic loading")

            class DynamicManyToManyQuery:
                def __init__(self, obj, rel_info, session, pk_name, loop) -> types.NoneType:
                    self.obj = obj
                    self.rel_info = rel_info
                    self.session = session
                    self.pk_name = pk_name
                    self._query = None
                    self.loop = loop

                def where(self, *conditions):
                    if not self._query:
                        self._build_query()
                    self._query = self._query.where(*conditions)  # type: ignore
                    return self

                def _build_query(self):
                    related_model = self.rel_info.related_model
                    through_model = self.rel_info.through_model

                    local_col = (
                            self.rel_info.local_column
                            or f"{self.obj.__class__.__name__.lower()}_id"
                    )
                    foreign_col = (
                            self.rel_info.foreign_column
                            or f"{related_model.__name__.lower()}_id"
                    )

                    from nexios.orm.query.builder import select

                    self._query = (
                        select(related_model)
                        .join(
                            through_model,
                            getattr(through_model, foreign_col)
                            == getattr(related_model, self.pk_name),
                        )
                        .where(
                            getattr(through_model, local_col)
                            == getattr(self.obj, self.pk_name)
                        )
                    )
                    self._query._bind(self.session)
                    return self

                @overload
                def all(self):
                    ...

                @overload
                async def all(self):
                    ...

                def all(self):
                    if not self._query:
                        self._build_query()
                    if isinstance(self.session, AsyncSession):
                        async def all_async():
                            return await self._query._all_async()  # type: ignore

                        return self.loop.run(all_async())
                    else:
                        return self._query._all()  # type: ignore

            return cast(
                Select,
                DynamicManyToManyQuery(
                    obj,
                    self._relationship_info,
                    session,
                    pk_name,
                    _loop
                ),
            )
        elif self._relationship_info.relationship_type == RelationshipType.MANY_TO_ONE:
            fk_field = self._relationship_info.foreign_key
            if not fk_field:
                raise ValueError(f"No foreign key specified for many to one relationship {fk_field}")
            fk_value = getattr(obj, fk_field, None)

            class DynamicManyToOneQuery:
                def __init__(self, obj, rel_info, session, fk_field, fk_value) -> types.NoneType:
                    self.obj = obj
                    self.rel_info = rel_info
                    self.session = session
                    self.fk_field = fk_field
                    self.fk_value = fk_value
                    self._query = None

                def where(self, *conditions):
                    if not self._query:
                        self._build_query()
                    self._query = self._query.where(*conditions)  # type: ignore
                    return self

                def _build_query(self):
                    related_model = self.rel_info.related_model
                    from nexios.orm.query.builder import select

                    if self.fk_value is None:
                        # Return a query that will always yield empty results
                        self._query = select(related_model).where(False)
                    else:
                        pk_field = related_model.get_primary_key()
                        if isinstance(pk_field, (list, tuple)):
                            pk_field = pk_field[0]
                        self._query = select(related_model).where(
                            getattr(related_model, pk_field) == self.fk_value
                        )
                    return self

                def first(self):
                    if not self._query:
                        self._build_query()
                    return self._query._first()  # type: ignore

                async def first_async(self):
                    if not self._query:
                        self._build_query()
                    return await self._query._first_async()  # type: ignore

                def all(self):
                    if not self._query:
                        self._build_query()
                    result = self._query._first()  # type: ignore
                    return [result] if result is not None else []

                async def all_async(self):
                    if not self._query:
                        self._build_query()
                    # For MANY_TO_ONE, _all_async() should return a list with 0 or 1 item
                    result = await self._query._first_async()  # type: ignore
                    return [result] if result is not None else []

            return cast(
                Select,
                DynamicManyToOneQuery(
                    obj,
                    self._relationship_info,
                    session,
                    fk_field,
                    fk_value
                )
            )
        else:
            raise ValueError(
                f"Unsupported relationship type: {self._relationship_info.relationship_type}"
            )


class NexiosModel(
    PydanticBaseModel, ResolveForwardRefs, metaclass=NexiosModelMetaclass
):
    __tablename__: ClassVar[Optional[str]] = None
    __registry__: ClassVar[Dict[str, Type[NexiosModel]]] = {}
    __relationships__: ClassVar[Dict[str, RelationshipInfo]] = {}
    __primary_key__: ClassVar[Union[Tuple[str, ...], List[str], str, None]] = None

    if IS_PYDANTIC_V2:
        model_config = NexiosModelConfig(from_attributes=True)
    else:

        class Config:
            orm_mode = True

    def __init_subclass__(cls, table: Optional[bool] = None, **kwargs):
        super().__init_subclass__(**kwargs)

        cls.__registry__[cls.__name__] = cls

        if table is not None:
            set_config_value(model=cls, parameter="table", value=table)

        tablename = get_tablename_for_class(cls)
        cls.__tablename__ = tablename

    def __setattr__(self, name: str, value: Any) -> types.NoneType:
        if name not in self.__relationships__:
            super().__setattr__(name, value)

    @classmethod
    def _resolve_relationships(cls):
        for rel_name, rel_info in cls.__relationships__.items():
            if not rel_info.is_resolved:
                if rel_info.back_populates:
                    related_model = rel_info.related_model
                    if related_model and hasattr(
                            related_model, "__relationships__"
                    ):
                        related_rel = related_model.__relationships__.get(
                            rel_info.back_populates
                        )

                        if related_rel:
                            related_rel.back_populates = rel_name
                            related_rel.is_resolved = True
                            rel_info.is_resolved = True
                rel_info.is_resolved = True

    @classmethod
    def get_fields(cls) -> Dict[str, FieldInfo]:
        return cls.model_fields

    @classmethod
    def get_relationships(cls) -> Dict[str, RelationshipInfo]:
        return cls.__relationships__

    @classmethod
    def get_primary_key(cls) -> Any:
        from nexios.orm.query.expressions import ColumnExpression

        pk = getattr(cls, "__primary_key__", None)
        if pk:
            if isinstance(pk, (tuple, list)):
                return tuple(pk) if len(pk) > 1 else pk[0]  # type: ignore
            return pk

        for field_name, field_info in get_model_fields(cls).items():
            if getattr(field_info, "primary_key", Undefined):
                field_ = getattr(cls, field_name)
                if isinstance(field_, ColumnExpression):
                    return field_.field_name
                else:
                    return field_
        return None


def get_model_fields(
        model: InstanceOrType[PydanticBaseModel],
) -> Dict[str, PydanticFieldInfo]:
    if IS_PYDANTIC_V2:
        return model.model_fields  # type: ignore
    else:
        return model.__fields__  # type: ignore


def get_tablename(model_class: InstanceOrType[NexiosModel]) -> str:
    if not isinstance(model_class, type):
        model_class = model_class.__class__

    tablename = getattr(model_class, "__tablename__", None)
    if tablename is None and hasattr(model_class, "__tablename__"):
        tablename = model_class.__tablename__
    return tablename if tablename else ""
