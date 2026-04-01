from __future__ import annotations
import re
from typing import Literal, Optional, TypeVar, Any, Type, Union, Dict, TYPE_CHECKING
from packaging import version
from pydantic import ConfigDict, BaseModel as PydanticBaseModel
from pydantic.fields import FieldInfo as PydanticFieldInfo
import pydantic

if TYPE_CHECKING:
    from nexios.orm.model import NexiosModel


_TNexiosModel = TypeVar("_TNexiosModel", bound=Any)

PYDANTIC_VERSION = version.parse(pydantic.__version__)

IS_PYDANTIC_V2 = PYDANTIC_VERSION.major >= 2

OnDeleteOrUpdate = Literal[
    "CASCADE", "SET NULL", "SET DEFAULT", "RESTRICT", "NO ACTION"
]
LazyOp = Literal["select", "joined", "subquery", "dynamic"]
T = TypeVar("T")
InstanceOrType = Union[T, Type[T]]

def to_snake_case(name: str) -> str:
        """Converts CamelCase to snake_case."""
        s1 = re.sub('(.)([A-Z][a-z]+)', r'\1_\2', name)
        return re.sub('([a-z0-9])([A-Z])', r'\1_\2', s1).lower()

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

def get_model_fields(
        model: InstanceOrType[PydanticBaseModel],
) -> Dict[str, PydanticFieldInfo]:
    if IS_PYDANTIC_V2:
        return model.model_fields  # type: ignore
    else:
        return model.__fields__  # type: ignore


def get_tablename(model_class: InstanceOrType[Any]) -> str:
    if not isinstance(model_class, type):
        model_class = model_class.__class__

    tablename = getattr(model_class, "__tablename__", None)
    if tablename is None and hasattr(model_class, "__tablename__"):
        tablename = model_class.__tablename__
    return tablename if tablename else ""