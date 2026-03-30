from __future__ import annotations

from typing import Any, Generic, List, Optional, Self, Tuple, Type, TypeVar, Union, TYPE_CHECKING

if TYPE_CHECKING:
    from nexios.orm.config import Dialect
    from nexios.orm.model import NexiosModel
    from nexios.orm.query.builder import Select


Expression = Union["BinaryExpression", "CompoundExpression"]
_T = TypeVar("_T", bound="NexiosModel")


class CompoundExpression:
    """Represents AND/OR combination of expressions"""

    def __init__(self, left: Expression, operator: str, right: Expression):
        self.left = left
        self.operator = operator  # 'AND' or 'OR'
        self.right = right

    def __and__(self, other: Expression) -> "CompoundExpression":
        return CompoundExpression(self, "AND", other)

    def __or__(self, other: Expression) -> "CompoundExpression":
        return CompoundExpression(self, "OR", other)

    def to_sql(
        self, placeholder: str = "?", dialect: Optional[Any] = None, driver: Optional[Any] = None
    ) -> Tuple[str, List[Any]]:
        left_sql, left_params = self.left.to_sql(placeholder, dialect, driver)
        right_sql, right_params = self.right.to_sql(placeholder, dialect, driver)

        sql = f"({left_sql} {self.operator} {right_sql})"
        params = left_params + right_params
        return sql, params


class TSVectorExpression:
    def __init__(
        self, column: ColumnExpression, query: str, config: Optional[str] = None
    ):
        self.column = column
        self.query = query
        self.config = config

    def to_sql(
        self, placeholder: str = "?", dialect: Optional[Any] = None, driver: Optional[Any] = None
    ) -> Tuple[str, List[Any]]:
        quoted_column = dialect.quote_identifier(self.column.field_name)  # type: ignore
        if self.config:
            return (
                f"to_tsvector('{self.config}',{quoted_column})@@ plainto_tsquery('{self.config}',{placeholder})",
                [self.query],
            )
        else:
            return f"{quoted_column}@@ plainto_tsquery({placeholder})", [self.query]


class MatchExpression:
    def __init__(self, column: ColumnExpression, query: str, mode: str = "BOOLEAN"):
        self.column = column
        self.query = query
        self.mode = mode

    def to_sql(
        self, placeholder: str = "?", dialect: Optional[Any] = None, driver: Optional[Any] = None
    ) -> Tuple[str, List[Any]]:
        quoted_column = dialect.quote_identifier(self.column.field_name)  # type: ignore
        if self.mode == "BOOLEAN":
            return f"MATCH({quoted_column}) AGAINST({placeholder} IN BOOLEAN MODE)", [
                self.query
            ]
        else:
            return f"MATCH({quoted_column}) AGAINST({placeholder})", [self.query]


class BM25Expression:
    def __init__(self, column: ColumnExpression, query: str):
        self.column = column
        self.query = query

    def to_sql(
        self, placeholder: str = "?", dialect: Optional[Any] = None, driver: Optional[Any] = None
    ) -> Tuple[str, List[Any]]:
        quoted_column = dialect.quote_identifier(self.column.field_name)  # type: ignore
        return f"{quoted_column} MATCH {placeholder}", [self.query]


class AlwaysTrueExpression:
    """An expression that's always true"""
    def to_sql(self, placeholder: str = "?", dialect=None, driver=None) -> Tuple[str, List[Any]]:
        return "1 = 1", []

class AlwaysFalseExpression:
    """An expression that's always false"""
    def to_sql(self, placeholder: str = "?", dialect=None, driver=None) -> Tuple[str, List[Any]]:
        return "1 = 0", []

class BinaryExpression:  # type: ignore
    def __init__(self, column_expr: ColumnExpression, operator: str, value: Any):
        self.column = column_expr
        self.operator = operator
        self.value = value

    def __and__(self, other: Expression) -> CompoundExpression:
        return CompoundExpression(self, "AND", other)

    def __or__(self, other: Expression) -> CompoundExpression:
        return CompoundExpression(self, "OR", other)

    def to_sql(
        self,
        placeholder: str = "?",
        dialect: Optional[Any] = None,
        driver: Optional[Any] = None,
    ) -> Tuple[str, List[Any]]:
        from nexios.orm.query.builder import Select

        col = self.column.field_name
        if self.value is None:
            if self.operator == "=":
                return f"{col} IS NULL", []
            if self.operator == "!=":
                return f"{col} IS NOT NULL", []

        if isinstance(self.value, ColumnExpression):
            right_col = self.value.field_name
            return f"{col} {self.operator} {right_col}", []

        if self.operator in ("IN", "NOT IN"):
            if isinstance(self.value, Select):
                subquery_sql, subquery_params, _, _ = self.value._build_sql(
                    dialect, driver # type: ignore
                )
                return f"{col} {self.operator} ({subquery_sql})", subquery_params

            if not isinstance(self.value, (list, tuple)):
                raise ValueError(f"{self.operator} requires a list or tuple")

            if not self.value:
                if self.operator == "IN":
                    return "1 = 0", []
                else:
                    return "1 = 1", []

            placeholders = ", ".join([placeholder] * len(self.value))
            return f"{col} {self.operator} ({placeholders})", list(self.value)

        if self.operator == "BETWEEN":
            if not isinstance(self.value, (list, tuple)) or len(self.value) != 2:
                raise ValueError("BETWEEN requires a 2-tuple (lower, upper)")

            return f"{col} BETWEEN {placeholder} AND {placeholder}", list(self.value)

        if self.operator in ("LIKE", "ILIKE"):
            value = str(self.value)
            if "%" not in value and "_" not in value:
                value = f"%{value}%"

            return f"{col} {self.operator} {placeholder}", [value]

        return f"{col} {self.operator} {placeholder}", [self.value]


class ColumnExpression(Generic[_T]):
    """Represents a column in a select expression"""

    def __init__(self, model_cls: Type[_T], field_name: str):
        self.model_cls = model_cls
        self.field_name = field_name
        self._alias = None
        self._order_desc = False

    def _binary(self, operator: str, value: Any) -> BinaryExpression:
        return BinaryExpression(self, operator, value)

    def __eq__(self, other: Any) -> BinaryExpression:  # type: ignore[override]
        return self._binary("=", other)

    def __ne__(self, other: Any) -> BinaryExpression:  # type: ignore[override]
        return self._binary("!=", other)

    def __lt__(self, other: Any) -> BinaryExpression:
        return self._binary("<", other)

    def __le__(self, other: Any) -> BinaryExpression:
        return self._binary("<=", other)

    def __gt__(self, other: Any) -> BinaryExpression:
        return self._binary(">", other)

    def __ge__(self, other: Any) -> BinaryExpression:
        return self._binary(">=", other)

    def like(self, value: str):
        return self._binary("LIKE", value)

    def ilike(self, value):
        return self._binary("ILIKE", value)

    def in_(self, values: Union[List[Any], Select]):
        """IN operator for list values or subquery"""
        return self._binary("IN", values)

    def not_in(self, values: Union[List[Any], Select]):
        return self._binary("NOT IN", values)

    def between(self, lower: Any, upper: Any) -> BinaryExpression:
        """BETWEEN operator"""
        return self._binary("BETWEEN", (lower, upper))

    def is_null(self) -> BinaryExpression:
        """IS NULL operator"""
        return self._binary("IS", None)

    def is_not_null(self) -> BinaryExpression:
        """IS NULL operator"""
        return self._binary("IS NOT", None)

    def asc(self) -> Self:
        """Order by ascending"""
        # return f"{self} ASC"
        import copy

        new_expr = copy.copy(self)
        new_expr._order_desc = False
        return new_expr

    def desc(self) -> Self:
        """Order by descending"""
        # return f"{self} DESC"
        import copy

        new_expr = copy.copy(self)
        new_expr._order_desc = True
        return new_expr

    def label(self, alias: str) -> ColumnExpression[_T]:
        """Create an aliased column expression"""
        # For simplicity, we'll handle aliasing in the SQL builder
        self._alias = alias
        return self

    def to_sql(self, dialect: Dialect, table_alias: Optional[str] = None) -> str:
        """Generate SQL with proper quoting and table qualification"""
        quoted_field = dialect.quote_identifier(self.field_name)

        if table_alias:
            quoted_table = dialect.quote_identifier(table_alias)
            sql = f"{quoted_table}.{quoted_field}"
        else:
            table_name = self.model_cls.__tablename__
            quoted_table = dialect.quote_identifier(table_name)  # type: ignore
            sql = f"{quoted_table}.{quoted_field}"

        if self._alias:
            quoted_alias = dialect.quote_identifier(self._alias)
            sql += f" AS {quoted_alias}"

        return sql

    def match(self, query: str, mode: str = "NATURAL"):
        from nexios.orm.config import PostgreSQLDialect, MySQLDialect, SQLiteDialect

        class GenericMatch:
            def __init__(self, c, q, m):
                self._column = c
                self._query = q
                self._mode = m

            def to_sql(
                self, placeholder: str = "?", dialect: Optional[Dialect] = None
            ) -> tuple[str, list[Any]]:
                if isinstance(dialect, PostgreSQLDialect):
                    return TSVectorExpression(self._column, self._query).to_sql(
                        placeholder, dialect
                    )
                elif isinstance(dialect, MySQLDialect):
                    return MatchExpression(self._column, self._query).to_sql(
                        placeholder, dialect
                    )
                elif isinstance(dialect, SQLiteDialect):
                    return BM25Expression(self._column, self._query).to_sql(
                        placeholder, dialect
                    )
                else:
                    raise NotImplementedError()

        return GenericMatch(self, query, mode)

    def __str__(self) -> str:
        return f"{self.field_name}"
