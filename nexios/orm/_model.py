from __future__ import annotations

import asyncio
import builtins
import inspect
import re
import sys
import threading
import types
from typing_extensions import Unpack
from packaging import version
from enum import Enum
from dataclasses import dataclass, field
from contextvars import ContextVar
from typing import (
    TYPE_CHECKING,
    Awaitable,
    Coroutine,
    Union,
    Optional,
    List,
    Type,
    Tuple,
    Dict,
    Set,
    Callable,
    Any,
    Literal,
    TypeVar,
    ClassVar,
    ForwardRef,
    get_origin,
    get_args,
    dataclass_transform,
    get_type_hints,
    overload,
    cast
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

from nexios.orm.sessions import AsyncSession, Session

OnDeleteType = Literal["CASACDE", "SET NULL", "SET DEFAULT", "RESTRICT", "NO ACTION"]
T = TypeVar("T")
M = TypeVar("M")# represents Callable method in loop
InstanceOrType = Union[T, Type[T]]
_TNexiosModel = TypeVar("_TNexiosModel", bound="NexiosModel")

PYDANTIC_VERSION = version.parse(pydantic.__version__)

IS_PYDANTIC_V2 = PYDANTIC_VERSION.major >= 2

class NexiosModelConfig(ConfigDict, total=False):
    table: Optional[bool]

class RelationshipType(Enum):
    ONE_TO_ONE = "one_to_one"
    ONE_TO_MANY = "one_to_many"
    MANY_TO_ONE = "many_to_one"
    MANY_TO_MANY = "many_to_many"

_SESSION: Union[Any, None] = None

# Dummy helper function, i don't even know if it can work
def set_session(session: Any):
    _SESSION = session

class NexiosEventLoop:
    _thread_local = threading.local()

    @classmethod
    def get_event_loop(cls) -> asyncio.AbstractEventLoop:
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
        
        cls._thread_local = loop
        return loop
    
    @classmethod
    def run(cls, coroutine: Coroutine[Any, Any, M],loop: Optional[asyncio.AbstractEventLoop] = None) -> M:
        if loop is None:
            loop = cls.get_event_loop()
        
        try:
            asyncio.get_running_loop()
            raise RuntimeError(
                "Use await in async context. This function is for sync context only"
            )
        except RuntimeError:
            pass

        if loop.is_running():
            future = asyncio.run_coroutine_threadsafe(coroutine, loop)
            return future.result()
        else:
            return loop.run_until_complete(coroutine)
    
    @classmethod
    def ensure_result(cls, func: Callable, *args, **kwargs) -> Coroutine[Any, Any, Any]:
        result = func(*args, **kwargs)

        if inspect.iscoroutine(result):
            return result
        else:
            async def wrapper():
                return result
            return wrapper()

class FieldInfo(PydanticFieldInfo):
    def __init__(self, default: Any = Undefined, **kwargs: Any) -> None:
        primary_key = kwargs.pop("primary_key", False)
        nullable = kwargs.pop("nullable", Undefined)
        foreign_key = kwargs.pop("foreign_key", Undefined)
        ondelete = kwargs.pop("ondelete", Undefined)
        unique = kwargs.pop("unique", False)
        index = kwargs.pop("index", Undefined)
        auto_increment = kwargs.pop("auto_increment", False)

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
    ondelete: Optional[OnDeleteType] = None
    onupdate: Optional[Literal["CASCADE", "SET NULL", "SET DEFAULT", "RESTRICT", "NO ACTION"]] = None
    nullable: bool = False
    unique: bool = False
    back_populates: Optional[str] = None
    lazy: Literal["select", "joined", "subquery", "dynamic"]= "select"
    
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
            self._through_model = get_model(self.through)
        return self._through_model
    
    @property
    def related_model(self) -> Optional[Type["NexiosModel"]]:
        if self._related_model is None and self.related_model_name:
            self._related_model = get_model(self.related_model_name)
        return self._related_model
    
    def create_foreign_key_constraint_sql(self, model_name: str) -> Optional[str]:
        if not self.foreign_key or not self.related_model_name:
            return None
        
        constraint_name = f"fk_{model_name.lower()}_{self.field_name}"
        sql_parts = [
            f"CONSTRAINT {constraint_name}",
            f"FOREIGN KEY ({self.foreign_key})",
            f"REFERENCES {self.related_model_name.lower()}s(id)"
        ]

        if self.ondelete:
            sql_parts.append(f"ON DELETE {self.ondelete}")
        if self.onupdate:
            sql_parts.append(f"ON UPDATE {self.onupdate}")
        if self.deferrable is not None:
            sql_parts.append("DEFERRABLE" if self.deferrable else "NOT DEFERRABLE")
        if self.initially_deferred is not None:
            sql_parts.append("INITIALLY DEFERRED" if self.initially_deferred else "INITIALLY IMMEDIATE")
        
        return " ".join(sql_parts)

def get_model(model_name: str) -> Type["NexiosModel"]:
    """Resolve a model name string to a model class."""
    if model_name not in NexiosModel.__registry__:
        raise ValueError(f"Model '{model_name}' not found in registry.")
    return NexiosModel.__registry__[model_name]

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
    foreign_key: str,
    ondelete: Union[OnDeleteType, UndefinedType] = Undefined,
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
    foreign_key: Any = Undefined,
    ondelete: Union[OnDeleteType, UndefinedType] = Undefined,
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
        foreign_key=foreign_key,
        ondelete=ondelete,
        unique=unique,
        nullable=nullable,
        index=index,
        **current_schema_extra,
    )
    return field_info

def relationship(
    related_model: Union[Type["NexiosModel"], str],
    relationship_type: RelationshipType = RelationshipType.MANY_TO_ONE,
    *,
    foreign_key: Optional[str] = None,
    related_field_name: Optional[str] = None,
    through: Optional[Union[Type["NexiosModel"], str]] = None,
    ondelete: Optional[OnDeleteType] = None,
    onupdate: Optional[Literal["CASCADE", "SET NULL", "SET DEFAULT", "RESTRICT", "NO ACTION"]] = None,
    nullable: bool = False,
    unique: bool = False,
    back_populates: Optional[str] = None,
    lazy: str = "select",
    deferrable: Optional[bool] = None,
    initially_deferred: Optional[bool] = None,
    **kwargs: Any,
) -> Any:
    
    def decorator(func):
        rel_info = {
            "related_model": (
                related_model if isinstance(related_model, str) else related_model.__name__
            ),
            "relationship_type": relationship_type,
            "foreign_key": foreign_key,
            "related_field_name": related_field_name,
            "through": through,
            "ondelete": ondelete,
            "onupdate": onupdate,
            "nullable": nullable,
            "unique": unique,
            "back_populates": back_populates,
            "lazy": lazy,
            "deferrable": deferrable,
            "initially_deferred": initially_deferred,
            "metadata": kwargs,
        }

        if not hasattr(func, '__relationship_info__'):
            setattr(func, '__relationship_info__', rel_info)
        return func
    return decorator

def one_to_one(
    related_model: Union[str, Type[_TNexiosModel]],
    **kwargs
) -> Any:
    return relationship(related_model, RelationshipType.ONE_TO_ONE, **kwargs)

def one_to_many(
    related_model: Union[str, Type[_TNexiosModel]],
    **kwargs
) -> Any:
    return relationship(related_model, RelationshipType.ONE_TO_MANY, **kwargs)

def many_to_one(
    related_model: Union[str, Type[_TNexiosModel]],
    **kwargs
) -> Any:
    return relationship(related_model, RelationshipType.MANY_TO_ONE, **kwargs)

def many_to_many(
    related_model: Union[str, Type[_TNexiosModel]],
    *,
    through: Union[str, Type[_TNexiosModel]],
    local_column: Optional[str] = None,
    foreign_column: Optional[str] = None,
    **kwargs
) -> Any:
    return relationship(
        related_model,
        RelationshipType.MANY_TO_MANY,
        through=through,
        **kwargs
    )

@dataclass_transform(kw_only_default=True, field_specifiers=(Field, FieldInfo))
class NexiosModelMetaclass(ModelMetaclass):
    __nexios_model_relationships__: Dict[str, RelationshipInfo] = {}
    model_config: NexiosModelConfig
    model_fields: Dict[str, FieldInfo] = {}
    __config__: Type[NexiosModelConfig]

    def __setattr__(cls, name: str, value: Any) -> None:
        super().__setattr__(name, value)

    def __delattr__(cls, name: str) -> None:
        super().__delattr__(name)

    def __getattribute__(cls, key):
        if TYPE_CHECKING:
            from nexios.orm.query import ColumnExpression

        if key in ["model_fields", "__dict__", "__pydantic_fields__"]:
            return super().__getattribute__(key)
        if key not in cls.model_fields:
            return super().__getattribute__(key)
        return ColumnExpression(cls, key) # type: ignore
    
    def __new__(mcs, name: str, bases: Tuple[Type[Any], ...], namespace: Dict[str, Any], **kwargs: Any):
        namespace['__nexios_model_relationships__'] = {}
        
        relationships: Dict[str, RelationshipInfo] = {}
        pydantic_dict = {}
        original_annotations = namespace.get("__annotations__", {})
        pydantic_annotations = {}
        relationship_annotations = {}

        for k, v in namespace.items():
            if isinstance(v, RelationshipInfo):
                relationships[k] = v
            else:
                pydantic_dict[k] = v
        for k, v in original_annotations.items():
            if k in relationships:
                relationship_annotations[k] = v
            else:
                pydantic_annotations[k] = v
        dict_used = {
            **pydantic_dict,
            "__nexios_model_relationships__": relationships,
            "__annotations__": pydantic_annotations
        }
        kwargs_to_skip: Set[str] = {
            key
            for key in dir(NexiosModelConfig)
            if not key.startswith("__") and key.endswith("__")
        }
        allowed_config_keys = {"table", "read_from_attributes", "from_attributes"}

        config_kwargs = {
            key: kwargs[key] for key in kwargs.keys() & kwargs_to_skip & allowed_config_keys
        }
        for k in list(kwargs.keys()):
            if k in allowed_config_keys:
                config_kwargs[k] = kwargs.pop(k)
    
        cls = super().__new__(mcs, name, bases, dict_used, **config_kwargs)
        cls.__annotations__ = {
            **relationship_annotations,
            **pydantic_annotations,
            **cls.__annotations__
        }

        for attr_name, attr_value in cls.__dict__.items():
            if hasattr(attr_value, '__relationship_info__'):
                rel_info = attr_value.__relationship_info__
                
                related_model = rel_info['related_model']
                print(f"Does it have an attribute called __registry__?: {hasattr(cls, '__registry__')}")
                if isinstance(related_model, str):
                    related_model = cls.__registry__[related_model]
                
                if not related_model:
                    raise ValueError(f"Related model '{rel_info['related_model']}' not found in registry")
                
                through = rel_info.get('through')
                if isinstance(through, str):
                    through = cls.__registry__[through]
                
                foreign_key = rel_info.get('foreign_key')
                if not foreign_key:
                    if rel_info['relationship_type'] in [RelationshipType.MANY_TO_ONE, RelationshipType.ONE_TO_ONE]:
                        foreign_key = f"{cls.__name__.lower()}_id"
                
                relationship_info = RelationshipInfo(
                    field_name=attr_name,
                    related_model_name=related_model.__name__,
                    relationship_type=rel_info['relationship_type'],
                    foreign_key=foreign_key,
                    related_field_name=rel_info.get('related_field_name'),
                    through=through,
                    ondelete=rel_info.get('ondelete'),
                    onupdate=rel_info.get('onupdate'),
                    nullable=rel_info.get('nullable'),
                    unique=rel_info.get('unique'),
                    back_populates=rel_info.get('back_populates'),
                    lazy=rel_info.get('lazy'),
                    deferrable=rel_info.get('deferrable'),
                    initially_deferred=rel_info.get('initially_deferred'),
                    metadata=rel_info.get('metadata'),
                )

                relationships[attr_name] = relationship_info

                setattr(cls, attr_name, RelationshipDescriptor(cls, attr_name))
                try:
                    delattr(cls, attr_name + '__relationship_info__')
                except AttributeError:
                    pass
        # cls.__nexios_model_relationships__ = relationships

        # Resolve forward references
        cls._resolve_forward_references()
       
        return cls

class RelationshipDescriptor:
    def __init__(self, model_class: Type[NexiosModel], field_name: str) -> types.NoneType:
        self.model_class = model_class
        self.field_name = field_name
        self._relationship_info = model_class.__nexios_model_relationships__[field_name]
    
    def _get_current_session(self):
        if hasattr(self, '_session'):
            return self._session # type: ignore
        
        try:
            if hasattr(threading.current_thread(), 'session'):
                return threading.current_thread().session # type: ignore
        except Exception:
            pass

        try:
            task = asyncio.current_task()
            if hasattr(task, 'session'):
                return task.session # type: ignore
        except Exception:
            pass

        for frame_info in inspect.stack():
            frame = frame_info.frame
            if 'self' in frame.f_locals:
                obj = frame.f_locals['self']
                if isinstance(obj, (Session, AsyncSession)):
                    return obj
        return None
    
    def __get__(self, obj: Optional[NexiosModel], objType: Type[NexiosModel]):
        _event_loop = NexiosEventLoop()

        if obj is None:
            return self
        
        relationship_cache = obj.__dict__.get('__relationship_cache__', {})

        if self.field_name in relationship_cache:
            return relationship_cache[self.field_name]
        
        session = self._get_current_session()
        if not session:
            raise RuntimeError(
                f"No session available for loading relationship '{self.field_name}'. "
                f"Make sure you're inside a session context manager."
            )
        
        if self._relationship_info.lazy == 'select':
            return self._load_select_lazy(obj, session)
        elif self._relationship_info.lazy == 'joined':
            # SHould have loaded already
            return self._load_select_lazy(obj, session)
        elif self._relationship_info.lazy == 'dynamic':
            return self._load_dynamic(obj, session)
        elif self._relationship_info.lazy == 'subquery':
            return self._load_subquery(obj, session)
        else:
            return self._load_select_lazy(obj, session)
        
        # related = _event_loop.run(self._load_relationship(obj))

        # if '__relationship_cache__' not in obj.__dict__:
        #     obj.__dict__['__relationship_cache__'] = {}
        # obj.__dict__['__relationship_cache__'][self.field_name] = related

        # return related
    
    def __set__(self, obj: NexiosModel, value: Any):
        if '__relationship_cache__' not in obj.__dict__:
            obj.__dict__['__relationship_cache__'] = {}
        obj.__dict__['__relationship_cache__'][self.field_name] = value
        
        if self._relationship_info.foreign_key:
            fk_field = self._relationship_info.foreign_key
            if hasattr(obj, fk_field):
                if value is None:
                    setattr(obj, fk_field, None)
                else:
                    pk_name = self._get_primary_key_name(value)
                    pk_value = getattr(value, pk_name, None)
                    setattr(obj, fk_field, pk_value)
    
    def _load_select_lazy(self, obj: NexiosModel, session: Any) -> Any:
        rel_type = self._relationship_info.relationship_type

        if rel_type == RelationshipType.MANY_TO_ONE:
            return self._load_many_to_one(obj, session)
        elif rel_type == RelationshipType.ONE_TO_MANY:
            return self._load_one_to_many(obj, session)
        elif rel_type == RelationshipType.MANY_TO_MANY:
            return self._load_many_to_many(obj, session)
        else:  # ONE_TO_ONE
            return self._load_one_to_one(obj, session)
    
    async def _load_relationship(self, obj: NexiosModel) -> Any:
        rel_info = self._relationship_info

        if not rel_info.is_resolved:
            rel_info._related_model = get_model(rel_info.related_model_name)

            if rel_info.through:
                rel_info._through_model = get_model(rel_info.through)
            rel_info.is_resolved = True


        if rel_info.relationship_type == RelationshipType.MANY_TO_ONE:
            return await self._load_many_to_one(obj, rel_info)
        
        elif rel_info.relationship_type == RelationshipType.ONE_TO_MANY:
            return await self._load_one_to_many(obj, rel_info)
        
        elif rel_info.relationship_type == RelationshipType.ONE_TO_ONE:
            return await self._load_one_to_one(obj, rel_info)
        
        elif rel_info.relationship_type == RelationshipType.MANY_TO_MANY:
            return await self._load_many_to_many(obj, rel_info)
        else:
            raise ValueError(f"Unknown relationship type: {rel_info.relationship_type}")

    async def _load_many_to_one(self, obj: NexiosModel, session: Any) -> Any:
        if not self._relationship_info.foreign_key:
            return None
        
        fk_value = getattr(obj, self._relationship_info.foreign_key, None)
        if fk_value is None:
            return None
        
        related_model = self._relationship_info.related_model
        assert related_model is not None
        pk_field = self._get_primary_key_name(related_model)

        from nexios.orm.query import select
        query = select(related_model).where(getattr(related_model, pk_field) == fk_value)
        # Bind session and execute TODO

        if isinstance(session, AsyncSession):
            async def asyn_fetch():
                return await query._first_async()
        # if not related_model:
        #     return None
        
        # query = f"""
        #     SELECT * FROM {related_model.__tablename__}
        #     WHERE {self._get_primary_key_name(related_model)} = ?
        # """

        # await self._execute(query, (fk_value))
        # result = await self._fetchone()
        # if result:
        #     return related_model.model_validate(result)
        # return None
    
    async def _load_one_to_many(self, obj: NexiosModel, rel_info: RelationshipInfo) -> List[NexiosModel]:
        related_model = rel_info.related_model
        if not related_model:
            return []
        
        pk_name = self._get_primary_key_name(obj.__class__)
        pk_value = getattr(obj, pk_name, None)

        if pk_value is None:
            return []
        if not rel_info.foreign_key:
            fk_in_ralated = f"{obj.__class__.__name__.lower()}_id"

            for rel_name, rel in related_model.__nexios_model_relationships__.items():
                if (rel.related_model_name == obj.__class__.__name__ and rel.relationship_type == RelationshipType.MANY_TO_ONE):
                    fk_in_ralated = rel.foreign_key or fk_in_ralated
                    break
        else:
            fk_in_ralated = rel_info.foreign_key
        
        query = f"""
            SELECT * FROM {related_model.__tablename__}
            WHERE {fk_in_ralated} = ?
        """
        await self._execute(query, (pk_value,))
        results = await self._fetchall()
        return [related_model.model_validate(row) for row in results]

    async def _load_one_to_one(self, obj: NexiosModel, rel_info: RelationshipInfo) -> Optional[NexiosModel]:
        if rel_info.foreign_key:
            fk_value = getattr(obj, rel_info.foreign_key, None)
            if fk_value is None:
                return None
            
            related_model = rel_info.related_model
            if not related_model:
                return None
            
            query = f"""
                SELECT * FROM {related_model.__tablename__}
                WHERE {self._get_primary_key_name(related_model)} = ?
            """
            await self._execute(query, (fk_value,))
            result = await self._fetchone()
            if result:
                return related_model.model_validate(result)
        else:
            related_model = rel_info.related_model
            if not related_model:
                return None
            
            back_rel = None
            for rel_name, rel in related_model.__nexios_model_relationships__.items():
                if (rel.related_model_name == obj.__class__.__name__ and rel.relationship_type == RelationshipType.ONE_TO_ONE):
                    back_rel = rel
                    break
            if back_rel and back_rel.foreign_key:
                pk_name = self._get_primary_key_name(obj.__class__)
                pk_value = getattr(obj, pk_name, None)

                if pk_value is None:
                    return None
                
                query = f"""
                    SELECT * FROM {related_model.__tablename__}
                    WHERE {back_rel.foreign_key} = ?
                """
                await self._execute(query, (pk_value,))
                result = self._fetchone()
                if result:
                    return related_model.model_validate(result)
        return None
    
    async def _load_many_to_many(self, obj: NexiosModel, rel_info: RelationshipInfo) -> List[NexiosModel]:
        related_model= rel_info.related_model
        through_model = rel_info.through_model

        if not related_model or not through_model:
            return []
        
        pk_name = self._get_primary_key_name(obj.__class__)
        pk_value = getattr(obj, pk_name, None)

        if pk_value is None:
            return []
        
        local_col = rel_info.local_column or f"{obj.__class__.__name__.lower()}_id"
        foreign_col = rel_info.foreign_column or f"{related_model.__name__.lower()}_id"

        query = f"""
            SELECT r.* FROM {related_model.__tablename__} r
            INNER JOIN {through_model.__tablename__} a ON r.id = a.{foreign_col}
            WHERE a.{local_col} = ?
        """
        await self._execute(query, (pk_value,))
        results = await self._fetchall()
        return [related_model.model_validate(row) for row in results]

    def _get_primary_key_name(self, model_class: Type[NexiosModel]) -> str:
        for field_name, field_info in get_model_fields(model_class).items():
            if isinstance(field_info, FieldInfo) and field_info.primary_key:
                return field_name
            
        return 'id' # default
    
    async def _execute(self, sql: str, params: Tuple[Any, ...]):
        from nexios.orm.sessions import AsyncSession
        if isinstance(self.session, AsyncSession):
            return await self.session.execute(sql, params)
        else:
            return self.session.execute(sql, params)
    
    async def _fetchone(self):
        from nexios.orm.sessions import AsyncSession
        if isinstance(self.session, AsyncSession):
            return await self.session.fetchone()
        else:
            return self.session.fetchone()
    
    async def _fetchall(self):
        from nexios.orm.sessions import AsyncSession
        if isinstance(self.session, AsyncSession):
            return await self.session.fetchall()
        else:
            return self.session.fetchall()
        

class NexiosModel(PydanticBaseModel, metaclass=NexiosModelMetaclass):
    __tablename__: ClassVar[Optional[str]] = None
    __registry__: ClassVar[Dict[str, Type[NexiosModel]]] = {}
    __nexios_model_relationships__: ClassVar[Dict[str, RelationshipInfo]] = {}
    __session__: ClassVar[Optional[Any]] = None

    if IS_PYDANTIC_V2:
        model_config = NexiosModelConfig(from_attributes=True)
    else:
        class Config:
            orm_mode = True


    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)
    
        cls.__registry__[cls.__name__] = cls

        if is_table_model_class(cls):
            if hasattr(cls, "__tablename__"):
                tbname = getattr(cls, "__tablename__")
                cls.__tablename__ = tbname
            else:
                name = cls.__name__.lower() + "s"
                cls.__tablename__ = name
        else:
            cls.__tablename__ = None
    
    def __setattr__(self, name: str, value: Any) -> types.NoneType:
        if name not in self.__nexios_model_relationships__:
           super().__setattr__(name, value)
    
    @classmethod
    def _resolve_relationships(cls):
        for rel_name, rel_info in cls.__nexios_model_relationships__.items():
            if not rel_info.is_resolved:
                if rel_info.back_populates:
                    related_model = rel_info.related_model
                    if related_model and hasattr(related_model, '__nexios_model_relationships__'):
                        related_rel = related_model.__nexios_model_relationships__.get(rel_info.back_populates)

                        if related_rel:
                            related_rel.back_populates = rel_name
                            related_rel.is_resolved = True
                            rel_info.is_resolved = True
                rel_info.is_resolved = True
    
    @classmethod
    def get_fields(cls) -> Dict[str, FieldInfo]:
        return cls.model_fields

    @classmethod
    def _resolve_forward_references(cls):
        localns = cls._get_local_namespacce()
        globalns = cls._get_global_namespace()

        try:
            resolved_hints = get_type_hints(cls, globalns=globalns, localns=localns)
            cls.__annotations__.update(resolved_hints)
        except Exception:
            cls._custom_resolve_forward_references(globalns, localns)

    @classmethod
    def _get_global_namespace(cls)  -> Dict[str, Any]:
        globalns = {**builtins.__dict__}
        import typing

        globalns.update(typing.__dict__)
        try:
            import typing_extensions
            globalns.update(typing_extensions.__dict__)
        except ImportError:
            pass
        globalns.update(cls.__registry__) # type: ignore
        module = sys.modules.get(cls.__module__)
        if module:
            globalns.update(getattr(module, "__dict__", {}))
        return globalns

    @classmethod
    def _get_local_namespacce(cls)  -> Dict[str, Any]:
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
    def _custom_resolve_forward_references(cls, globalns: Dict[str, Any], localns: Dict[str, Any]):
        for field_name, annotation in list(cls.__annotations__.items()):
            try:
                if isinstance(annotation, str):
                    resolved = cls._resolve_single_forward_ref(annotation, globalns, localns)
                    if resolved is not None:
                        cls.__annotations__[field_name] = resolved
                elif isinstance(annotation, ForwardRef):
                    resolved = cls._resolve_forward_ref_instance(annotation, globalns, localns)
                    if resolved is not None:
                        cls.__annotations__[field_name] = resolved
            except Exception as e:
                print(
                    f"Warning: Could not resolve forward reference for {cls.__name__}.{field_name}: {e}"
                )
                continue
    
    @classmethod
    def _resolve_single_forward_ref(cls, annotation: str, globalns: Dict[str, Any], localns: Dict[str, Any]) -> Any:
        if re.match(r"^[A-Z][a-zA-Z_]*\[", annotation):
            return cls._resolve_generic_forward_ref(annotation, globalns, localns)
        
        if annotation in localns:
            return localns[annotation]
        
        if annotation in globalns:
            return globalns[annotation]
        
        for key, model_class in cls.__registry__.items(): # type: ignore[no-def]
            if key.endswith(f".{annotation}") or model_class.__name__ == annotation:
                return model_class
        
        try:
            return get_type_hints(annotation, globalns, localns)
        except Exception:
            pass
        return None
    
    @classmethod
    def _resolve_generic_forward_ref(cls, annotation: str, globalns: Dict[str, Any], localns: Dict[str, Any]) -> Any:
        try:
            match = re.match(r"^([A-Z][a-zA-Z_]*)\[(.*)\]$", annotation)
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
                    resolved_inner = cls._resolve_single_forward_ref(inner_type.strip(), globalns, localns)
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
    def _resolve_forward_ref_instance(cls, forward_ref: ForwardRef, globalns: Dict[str, Any], localns: Dict[str, Any]) -> Any:
        try:
            if hasattr(forward_ref, "_evaluate"):
                return get_type_hints(cls, globalns=globalns, localns=localns)
            else:
                return get_type_hints(forward_ref.__forward_arg__, globalns=globalns, localns=localns)
        except Exception:
            return None

    @classmethod
    def get_relationships(cls) -> Dict[str, RelationshipInfo]:
        return cls.__nexios_model_relationships__
    
    @classmethod
    def set_session(cls, session: Any) -> None:
        cls.__session__ = session

def get_config_value(
    *, model: InstanceOrType[NexiosModel], parameter: str, default: Any = None
) -> Any:
    if IS_PYDANTIC_V2:
        return model.model_config.get(parameter, default)
    else:
        return getattr(model.__config__, parameter, default)


def set_config_value(
    *, model: InstanceOrType[NexiosModel], parameter: str, value: Any
) -> None:
    if IS_PYDANTIC_V2:
        model.model_config[parameter] = value
    else:
        setattr(model.__config__, parameter, value)


def get_model_fields(model: InstanceOrType[PydanticBaseModel]) -> Dict[str, PydanticFieldInfo]:
    if IS_PYDANTIC_V2:
        return model.model_fields  # type: ignore
    else:
        return model.__fields__ # type: ignore

def is_table_model_class(cls: Type[Any]) -> bool:
    is_table = False
    config = getattr(cls, "model_config", {})
    
    if config:
        table = config.get("table")
        if table:
            is_table = table
        elif not table and hasattr(cls, "__tablename__"):
            is_table = True
        else:
            is_table = False
    return is_table
