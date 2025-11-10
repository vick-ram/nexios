from typing_extensions import (
    Any,
    Literal,
    Type,
    TypeVar,
    Optional,
    List,
    Callable,
    Union,
)
from pydantic.fields import FieldInfo as PydanticFieldInfo
from datetime import datetime, date
from nexios.orm.field import (
    BaseConstraint,
    FieldType,
    ForeignConstraint,
    CheckConstraint,
)


class FieldInfo(PydanticFieldInfo):
    def __init__(
        self,
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
        python_type: Optional[Type] = None,
        **extra: Any,
    ):
        super().__init__(
            default=default,
            default_factory=default_factory,
            alias=alias,
            title=title,
            description=description,
            exclude=exclude,
            gt=gt,
            ge=ge,
            lt=lt,
            le=le,
            multiple_of=multiple_of,
            min_length=min_length,
            max_length=max_length,
            **extra,
        )
        self.field_type = field_type
        self.primary_key = primary_key
        self.nullable = nullable
        self.unique = unique
        self.index = index
        self.constraints = constraints or []
        self.choices = choices
        self.foreign_key = foreign_key
        self.check_constraints = check_constraints or []
        self.auto_increment = auto_increment
        self.auto_now = auto_now
        self.auto_now_add = auto_now_add
        self.db_column = db_column
        self.comment = comment
        self.python_type = python_type
        self.max_length = max_length
        self.min_length = min_length

        if foreign_key:
            self.constraints.append(foreign_key)

        # Store validation constraints in metadata (the way Pydantic does it)
        self.metadata = getattr(self, "metadata", [])

        # Add validation constraints to metadata
        validation_kwargs = {}
        if const:
            validation_kwargs["const"] = const

    def get_constraints_sql(self) -> List[str]:
        """Generate SQL for all constraints"""
        sql_constraints = []

        for constraint in self.constraints:
            sql_constraints.append(constraint.to_sql())

        for check in self.check_constraints:
            sql_constraints.append(check.to_sql())

        return sql_constraints

    def get_default_value(self) -> Any:
        """Get the actual default value, handling callables and special cases"""
        if self.auto_now_add or self.auto_now:
            return datetime.now()
        if self.default_factory is not None:
            return self.default_factory
        if callable(self.default):
            return self.default()
        return self.default

    def get_sql_definition(self) -> str:
        """Generate SQL column definition"""
        length = self.max_length or getattr(self, "max_length", 255) or 255
        # Determine type definition
        if (
            self.field_type == FieldType.VARCHAR
            or hasattr(self, "max_length")
            or self.max_length
        ):
            type_def = f"VARCHAR({length})"
        elif (
            self.field_type == FieldType.CHAR
            or hasattr(self, "max_length")
            or self.max_length
        ):
            type_def = f"CHAR({length})"
        else:
            type_def = self.field_type.value if self.field_type else "TEXT"

        parts = [type_def]

        # Add constraints and modifiers
        if not self.nullable:
            parts.append("NOT NULL")

        if self.primary_key:
            parts.append("PRIMARY KEY")

        if self.unique:
            parts.append("UNIQUE")

        # if self.default is not None and self.default is not ...:
        #     default_value = self._format_default_value()
        #     parts.append(f"DEFAULT {default_value}")

        # Add custom constraints
        if self.constraints or self.check_constraints:
            parts.extend(self.get_constraints_sql())

        return " ".join(parts)

    def _format_default_value(self) -> str:
        """Format default value for SQL"""
        default_value = self.get_default_value()

        if isinstance(default_value, str):
            return f"'{default_value}'"
        elif isinstance(default_value, bool):
            return "TRUE" if default_value else "FALSE"
        elif isinstance(default_value, (date, datetime)):
            return f"'{default_value.isoformat()}'"
        elif default_value is None:
            return "NULL"
        else:
            return str(default_value)

    def validate_value(self, value: Any) -> Any:
        """Validate value against field constraints"""
        if value is None:
            if not self.nullable:
                raise ValueError("Field cannot be null")
            return None

        # Type validation
        if self.python_type and not isinstance(value, self.python_type):
            try:
                value = self.python_type(value)
            except (ValueError, TypeError) as e:
                raise ValueError(f"Invalid type for field: {e}")

        # Choices validation
        if self.choices and value not in self.choices:
            raise ValueError(f"Value {value} not in choices {self.choices}")

        return value
