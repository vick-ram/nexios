from typing_extensions import Any, Literal, TYPE_CHECKING, TypeVar, Optional, List, Callable
from enum import Enum
from datetime import datetime, date


T = TypeVar("T")

class ConstraintType(Enum):
    CHECK = "CHECK"
    FOREIGN_KEY = "FOREIGN_KEY"
    UNIQUE_CONSTRAINT = "UNIQUE_CONSTRAINT"
    EXCLUSION = "EXCLUSION"  # Postgresql
    DEFAULT = "DEFAULT"


class BaseConstraint:
    def to_sql(self) -> str:
        raise NotImplementedError


class CheckConstraint(BaseConstraint):
    def __init__(self, condition: str):
        self.condition = condition

    def to_sql(self) -> str:
        return f"CHECK ({self.condition})"


class ForeignConstraint(BaseConstraint):
    def __init__(
        self,
        table: str,
        column: str,
        on_delete: Literal["CASCADE", "SET NULL", "RESTRICT"] = "CASCADE",
        on_update: Literal[
            "CASCADE", "SET NULL", "RESTRICT", "NO ACTION"
        ] = "NO ACTION",
    ) -> None:
        if not table or not column:
            raise ValueError("ForeignConstraint requires both table and column names.")

        self.table = table
        self.column = column
        self.on_delete = on_delete
        self.on_update = on_update

    def to_sql(self) -> str:
        return f"REFERENCES {self.table}({self.column}) ON DELETE {self.on_delete} ON UPDATE {self.on_update}"


class UniqueConstraint(BaseConstraint):
    def __init__(self, name: Optional[str] = None) -> None:
        self.name = name

    def to_sql(self) -> str:
        if self.name:
            return f"CONSTRAINT {self.name} UNIQUE"
        return "UNIQUE"


class FieldType(Enum):
    INTEGER = "INTEGER" or "INT"
    SMALLINT = "SMALLINT"
    BIGINT = "BIGINT"
    VARCHAR = "VARCHAR"
    TEXT = "TEXT"
    CHAR = "CHAR"
    BOOLEAN = "BOOLEAN"
    FLOAT = "FLOAT"
    DECIMAL = "DECIMAL"
    DATE = "DATE"
    TIME = "TIME"
    DATETIME = "DATETIME"
    TIMESTAMP = "TIMESTAMP"
    JSON = "JSON"
    BINARY = "BINARY"
    BLOB = "BLOB"
    ENUM = "ENUM"
    ARRAY = "ARRAY"
    UUID = "UUID"

def Field(
      default: Any = ...,
    default_factory: Optional[Callable[[], Any]] = None,
    alias: Optional[str] = None,
    title: Optional[str] = None,
    description: Optional[str] = None,
    exclude: bool = False,
    include: bool = False,
    const: bool = False,
    gt: Optional[float] = None,
    ge: Optional[float] = None,
    lt: Optional[float] = None,
    le: Optional[float] = None,
    multiple_of: Optional[float] = None,
    min_items: Optional[int] = None,
    max_items: Optional[int] = None,
    min_length: Optional[int] = None,
    max_length: Optional[int] = None,
    regex: Optional[str] = None,
    # Database parameters
    field_type: Optional[FieldType] = None,
    primary_key: bool = False,
    nullable: bool = True,
    unique: bool = False,
    index: bool = False,
    constraints: Optional[List[BaseConstraint]] = None,
    choices: Optional[List[Any]] = None,
    foreign_key: Optional[ForeignConstraint] = None,
    check_constraints: Optional[List[CheckConstraint]] = None,
    auto_increment: bool = False,
    auto_now: bool = False,
    auto_now_add: bool = False,
    db_column: Optional[str] = None,
    comment: Optional[str] = None,
    **kwargs: Any,  
) -> Any:
    from nexios.orm.backends.fieldinfo import FieldInfo
    validation_metadata = {}

    if any([min_length, max_length, regex]):
        validation_metadata['min_length'] = min_length
        validation_metadata['max_length'] = max_length
        validation_metadata['regex'] = regex
    
    # Handle numeric constraints
    if any([gt, ge, lt, le, multiple_of]):
        validation_metadata.update({
            'gt': gt,
            'ge': ge,
            'lt': lt,
            'le': le,
            'multiple_of': multiple_of
        })
    
    # Handle list constraints
    if any([min_items, max_items]):
        validation_metadata.update({
            'min_items': min_items,
            'max_items': max_items
        })
    
    field_info = FieldInfo(
        default=default,
        default_factory=default_factory,
        alias=alias,
        title=title,
        description=description,
        exclude=exclude,
        include=include,
        const=const,
        # Database parameters
        field_type=field_type,
        primary_key=primary_key,
        nullable=nullable,
        unique=unique,
        index=index,
        constraints=constraints,
        choices=choices,
        foreign_key=foreign_key,
        check_constraints=check_constraints,
        auto_increment=auto_increment,
        auto_now=auto_now,
        auto_now_add=auto_now_add,
        db_column=db_column,
        comment=comment
    )

    return field_info

