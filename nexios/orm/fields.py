from __future__ import annotations

from typing import (
    Union,
    Optional,
    Dict,
    Callable,
    Any,
    overload,
)

from pydantic_core import (
    PydanticUndefined as Undefined,
    PydanticUndefinedType as UndefinedType,
)
from pydantic.fields import FieldInfo as PydanticFieldInfo

from nexios.orm.utils import OnDeleteOrUpdate


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
