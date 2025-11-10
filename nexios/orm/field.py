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

# class Field:
#     def __init__(
#         self,
#         field_type: FieldType,
#         python_type: Type[T],
#         primary_key: bool = False,
#         nullable: bool = True,
#         default: Optional[Any] = None,
#         unique: bool = False,
#         index: bool = False,
#         constraints: Optional[List[BaseConstraint]] = None,
#         choices: Optional[List[T]] = None,
#         max_length: Optional[int] = None,
#         min_length: Optional[int] = None,
#         foreign_key: Optional[ForeignConstraint] = None,
#         check_constraints: Optional[List[CheckConstraint]] = None,
#         auto_increment: bool = False,
#         auto_now: bool = False,
#         auto_now_add: bool = False,
#         db_column: Optional[str] = None,
#         comment: Optional[str] = None,
#     ) -> None:
#         self.field_type = field_type
#         self.python_type = python_type
#         self.primary_key = primary_key
#         self.nullable = nullable
#         self.default = default
#         self.unique = unique
#         self.index = index
#         self.constraints = constraints
#         self.choices = choices
#         self.max_length = max_length
#         self.min_length = min_length
#         self.foreign_key = foreign_key
#         self.check_constraints = check_constraints or []
#         self.auto_increment = auto_increment
#         self.auto_now = auto_now
#         self.auto_now_add = auto_now_add
#         self.db_column = db_column
#         self.comment = comment

#         if foreign_key:
#             self.constraints.append(foreign_key) if self.constraints else [foreign_key]

#     def get_constraints_sql(self) -> List[str]:
#         sql_constraints = []

#         if self.constraints:
#             if isinstance(self.constraints, str):
#                 sql_constraints.append(self.constraints)
#             else:
#                 for constraint in self.constraints:
#                     sql_constraints.append(constraint.to_sql())

#         if self.foreign_key:
#             sql_constraints.append(self.foreign_key.to_sql())

#         for check in self.check_constraints:
#             sql_constraints.append(check.to_sql())

#         return sql_constraints

#     def get_default_value(self) -> Any:
#         """Get the actual default value, handling callables and special cases"""
#         if self.auto_now_add or self.auto_now:
#             return datetime.now()
#         if callable(self.default):
#             return self.default()
#         return self.default

#     def get_sql_definition(self) -> str:
#         parts = [self.field_type.value]

#         if self.field_type == FieldType.VARCHAR and self.max_length:
#             type_def = f"VARCHAR({self.max_length})"
#         elif self.field_type == FieldType.CHAR and self.max_length:
#             type_def = f"CHAR({self.max_length})"
#         else:
#             type_def = self.field_type.value 
        
#         parts = [type_def]

#         if not self.nullable:
#             parts.append("NOT NULL")

#         if self.primary_key:
#             parts.append("PRIMARY KEY")

#         if self.unique:
#             parts.append("UNIQUE")
        
#         if self.auto_increment:
#             parts.append("AUTOINCREMENT")

#         if self.default is not None:
#             default_value = self._format_default_value()
#             parts.append(f"DEFAULT {default_value}")

#         if self.constraints:
#             parts.extend(self.get_constraints_sql())

#         return " ".join(parts)
    
#     def _format_default_value(self) -> str:
#         if callable(self.default):
#             return self.get_default_value()

#         if isinstance(self.default, str):
#             return f"'{self.default}'"
#         elif isinstance(self.default, bool):
#             return "TRUE" if self.default else "FALSE"
#         elif isinstance(self.default, (date, datetime)):
#             return f"'{self.default.isoformat()}'"
#         elif self.default is None:
#             return "NULL"
#         else:
#             return str(self.default)
