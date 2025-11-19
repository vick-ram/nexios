from __future__ import annotations
from typing_extensions import (
    Type,
    TypeVar,
    Any,
    Tuple,
    List,
    Union,
    Awaitable,
    Optional,
    Generic,
    Literal,
    Self,
)
from nexios.orm.backends.config import DatabaseDialect
from nexios.orm.model import Model
from nexios.orm.backends.sessions import Session, AsyncSession

T = TypeVar("T", bound="Model")


class BinaryExpression:
    def __init__(self, column_expr: "ColumnExpression", operator: str, value: Any):
        self.column = column_expr
        self.operator = operator
        self.value = value

    def to_sql(self, placeholder):
        col = self.column.field_name
        if self.value is None:
            if self.operator == "=":
                return f"{col} IS NULL", []
            if self.operator == "!=":
                return f"{col} IS NOT NULL", []
        return f"{col} {self.operator} {placeholder}", [self.value]


class ColumnExpression(Generic[T]):
    """Represents a column in a select expression"""

    def __init__(self, model_cls: Type[T], field_name: str):
        self.model_cls = model_cls
        self.field_name = field_name

    def _binary(self, operator: str, value: Any) -> BinaryExpression:
        return BinaryExpression(self, operator, value)

    def __eq__(self, other: Any) -> BinaryExpression:  # type: ignore
        return self._binary("=", other)

    def __ne__(self, other: Any) -> BinaryExpression:  # type: ignore
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

    def label(self, alias: str) -> "ColumnExpression[T]":
        """Create an aliased column expression"""
        # For simplicity, we'll handle aliasing in the SQL builder
        self._alias = alias
        return self

    def __str__(self) -> str:
        if hasattr(self, "_alias"):
            return f'"{self.field_name}" AS "{self._alias}"'
        return f'"{self.field_name}"'


class Select(Generic[T]):
    def __init__(self, *entities: Any):
        self.entities = entities  # fields or models
        self._where: List[BinaryExpression] = []
        self._params: List[Any] = []
        self._order_by: List[Union[ColumnExpression[T], str]] = []
        self._limit: Optional[int] = None
        self._offset: Optional[int] = None
        self._session: Optional[Union["Session", "AsyncSession"]] = None
        self._joins: List[str] = []
        self._distinct: bool = False
        self._group_by: List[str] = []
        self._having: List[str] = []
        self._having_params: List[Any] = []

    def bind(self, session: Union["Session", "AsyncSession"]) -> Self:
        """Bind a session to this query"""
        self._session = session
        return self

    def where(self, *conditions: BinaryExpression) -> Self:
        self._where.extend(conditions)
        return self

    def order_by(self, *fields: Union[ColumnExpression[T], str]) -> Self:
        self._order_by.extend(fields)
        return self

    def limit(self, n: int) -> Self:
        self._limit = n
        return self

    def offset(self, n: int) -> Self:
        self._offset = n
        return self

    def count(self) -> Union[int, Awaitable[int]]:
        """Return count of records matching the query"""
        count_select = self._clone()
        count_select.entities = ("COUNT(*)",)
        count_select._order_by = []  # Remove ordering for count
        count_select._limit = None
        count_select._offset = None

        def transform_count(rows: List[Tuple[Any, ...]]) -> int:
            return rows[0][0] if rows else 0

        if isinstance(self._session, AsyncSession):

            async def async_count() -> int:
                rows = await count_select._execute_async()
                return transform_count(rows)

            return async_count()
        else:
            rows = count_select._execute_sync()
            return transform_count(rows)

        return self

    def exists(self) -> Union[bool, Awaitable[bool]]:
        """Check if any records match the query"""
        exists_select = self._clone()
        exists_select._limit = 1
        exists_select.entities = "1"

        def transform_exists(rows: List[Tuple[Any, ...]]) -> bool:
            return len(rows) > 0

        if isinstance(self._session, AsyncSession):

            async def async_exists() -> bool:
                rows = await exists_select._execute_async()
                return transform_exists(rows)

            return async_exists()
        else:
            rows = exists_select._execute_sync()
            return transform_exists(rows)

    def join(
        self,
        right_model: Type["Model"],
        on_condition: Union[BinaryExpression, str, None] = None,
        type: Literal["inner", "left", "right", "full", "cross"] = "left",
        alias: Optional[str] = None,
    ) -> Self:
        """Add JOIN clause on the query"""
        join_map = {
            "inner": "INNER JOIN",
            "left": "LEFT JOIN",
            "right": "RIGHT JOIN",
            "full": "FULL JOIN",
            "cross": "CROSS JOIN",
        }
        join_type = join_map.get(type, "LEFT JOIN")
        table_name = right_model.get_table_name()
        table_ref = ""
        if alias:
            table_ref = f'"{table_name}" AS "{alias}"'
        else:
            table_ref = f'"{table_name}"'

        # Build on condition
        on_sql = ""
        if on_condition is None:
            # Try infer foreign key relationship
            on_condition = self._infer_join_condition(right_model)
        elif isinstance(on_condition, BinaryExpression):
            # Convert Binary expression to sql
            on_sql, on_params = on_condition.to_sql("%s")
            self._params.extend(on_params)
        elif isinstance(on_condition, str):
            on_sql = on_condition
        else:
            raise ValueError("on_condition must be BinaryExpression, str, or None")

        self._joins.append(f"{join_type} {table_ref} ON {on_sql}")
        return self

    def distinct(self) -> Self:
        """Add DISTINCT clause"""
        self._distinct = True
        return self

    def group_by(self, *fields: str) -> Self:
        """Add GROUP BY clause"""
        self._group_by.extend(fields)
        return self

    def having(self, condition: str, *params: Any) -> Self:
        """Add HAVING clause"""
        self._having.append(condition)
        self._having_params.extend(params)
        return self

    def left_join(
        self,
        right_model: Type["Model"],
        on_condition: Union[BinaryExpression, str, None] = None,
    ) -> Self:
        return self.join(right_model, on_condition, type="left")

    def inner_join(
        self,
        right_model: Type["Model"],
        on_condition: Union[BinaryExpression, str, None] = None,
    ) -> Self:
        """Convenience method for INNER JOIN"""
        return self.join(right_model, on_condition, type="inner")

    def right_join(
        self,
        right_model: Type["Model"],
        on_condition: Union[BinaryExpression, str, None] = None,
    ) -> Self:
        """Convenience method for RIGHT JOIN"""
        return self.join(right_model, on_condition, type="right")

    def _infer_join_condition(self, right_model: Type["Model"]) -> str:
        """Try to infer condition based on field names"""
        # Get primary model from select
        primary_model = self._get_primary_model()
        if not primary_model:
            raise ValueError("Cannot infer join condition: no primary model found")

        possible_fks = [
            f"{primary_model.__name__.lower()}_id",
            f"{primary_model.get_table_name()}_id",
            "user_id",
            "parent_id",
        ]

        # Look for matching fields
        for fk_field in possible_fks:
            if fk_field in right_model._fields:
                # Found potential foreign key
                primary_pk = self._get_primary_key(primary_model)
                if primary_pk:
                    return f'"{primary_model.get_table_name()}"."{primary_pk}" = "{right_model.get_table_name()}"."{fk_field}"'
        raise ValueError(
            f"Cannot infer join condition between {primary_model.__name__} and {right_model.__name__}. Please provide explicit on_condition."
        )

    def _get_primary_model(self) -> Optional[Type["Model"]]:
        """Get the primary model from selected entities"""
        for entity in self.entities:
            if isinstance(entity, type) and issubclass(entity, Model):
                return entity
            elif isinstance(entity, ColumnExpression):
                return entity.model_cls
        return None

    def _get_primary_key(self, model: Type["Model"]) -> Optional[str]:
        """Get the primary key field for model"""
        for field_name, field_info in model._fields.items():
            if getattr(field_info, "primary_key", False):
                return field_name

            # Fallback to primary key names
            common_pks = ["id", f"{model.__name__.lower()}_id", "pk"]
            for pk in common_pks:
                if pk in model._fields:
                    return pk
            return None

    def _build_sql(self, dialect: "DatabaseDialect") -> Tuple[Any, ...]:
        placeholder = (
            "%s"
            if dialect in (DatabaseDialect.POSTGRES, DatabaseDialect.MYSQL)
            else "?"
        )

        # Determine table and what we're selecting
        if (
            len(self.entities) == 1
            and isinstance(self.entities[0], type)
            and issubclass(self.entities[0], Model)
        ):
            model = self.entities[0]
            fields = list(model._fields.keys())
            select_str = ", ".join(f'"{f}"' for f in fields)
            map_to_model = True
        else:
            map_to_model = False
            select_parts = []
            model = None

            for ent in self.entities:
                if isinstance(ent, ColumnExpression):
                    select_parts.append(str(ent))
                    if model is None:
                        model = ent.model_cls
                elif isinstance(ent, type) and issubclass(ent, Model):
                    # Multiple models selected
                    fields = [f'"{f}"' for f in ent._fields.keys()]
                    select_parts.extend(fields)
                    if model is None:
                        model = ent
                elif isinstance(ent, str):
                    select_parts.append(ent)

            select_str = ", ".join(select_parts)

            if model is None:
                raise ValueError("Could not determine model from selected entities")

        # Build SELECT clause with distinct
        distinct_clause = "DISTINCT " if self._distinct else ""
        select_str = f"SELECT {distinct_clause}{select_str}"

        table = model.get_table_name()
        sql = f"SELECT {select_str} FROM {table}"

        # JOIN clauses
        if self._joins:
            sql += " " + " ".join(self._joins)

        # WHERE
        params = []
        if self._where:
            parts = []
            for cond in self._where:
                sql_part, p = cond.to_sql(placeholder)
                parts.append(sql_part)
                params.extend(p)
            sql += " WHERE " + " AND ".join(parts)

        # GROUP BY clause
        if self._group_by:
            sql += " GROUP BY " + ", ".join(self._group_by)

        # HAVING clause
        if self._having:
            sql += " HAVING " + " AND ".join(self._having)
            params.extend(self._having_params)

        # ORDER BY
        if self._order_by:
            order_sql = []
            for f in self._order_by:
                if isinstance(f, ColumnExpression):
                    order_sql.append(str(f))
                else:
                    order_sql.append(f)
            sql += " ORDER BY " + ", ".join(order_sql)

        # LIMIT and OFFSET
        if self._limit is not None:
            sql += f" LIMIT {self._limit}"
        if self._offset is not None:
            sql += f" OFFSET {self._offset}"

        return sql, params, model, map_to_model

    def _execute_sync(self) -> List[Tuple[Any, ...]]:
        """Execute query synchronously"""
        if not self._session or not isinstance(self._session, Session):
            raise ValueError("No sync session bound to this query")

        sql, params, model, map_to_model = self._build_sql(self._session.engine.dialect)
        self._session.execute(sql, tuple(params))
        return self._session.fetchall()

    async def _execute_async(self) -> List[Tuple[Any, ...]]:
        """Execute query asynchronously"""
        if not self._session or not isinstance(self._session, AsyncSession):
            raise ValueError("No async session bound to this query")

        sql, params, model, map_to_model = self._build_sql(self._session.engine.dialect)
        await self._session.execute(sql, tuple(params))
        return await self._session.fetchall()

    def _rows_to_models(
        self, rows: List[Tuple[Any, ...]], model: Type[T], map_to_model: bool
    ) -> List[T]:
        """Convert rows to model instances or tuples"""
        if map_to_model:
            # Selecting entire model(s)
            results = []
            for row in rows:
                kwargs = {}
                field_names = list(model._fields.keys())
                for i, field_name in enumerate(field_names):
                    if i < len(row):
                        field_obj = model._fields.get(field_name)
                        value = row[i]
                        if field_obj and value is not None:
                            value = field_obj.to_python(value)
                        kwargs[field_name] = value
                results.append(model(**kwargs))
            return results
        else:
            # Selecting specific columns - return tuples for now
            return rows  # type: ignore

    # Sync methods
    def all(self) -> List[T]:
        """Execute and return all results"""
        rows = self._execute_sync()
        if self._session:
            sql, params, model, map_to_model = self._build_sql(
                self._session.engine.dialect
            )  # type: ignore
            return self._rows_to_models(rows, model, map_to_model)
        raise ValueError("Session not bound to query.")

    def first(self) -> Optional[T]:
        """Execute and return first result - OPTIMIZED"""
        original_limit = self._limit
        self._limit = 1

        try:
            rows = self._execute_sync()
            if not self._session:
                raise ValueError("Session not bound to query.")
            sql, params, model, map_to_model = self._build_sql(
                self._session.engine.dialect
            )  # type: ignore

            results = self._rows_to_models(rows, model, map_to_model)
            return results[0] if results else None
        finally:
            self._limit = original_limit

    # Async methods
    async def all_async(self) -> List[T]:
        """Execute and return all results asynchronously"""
        rows = await self._execute_async()
        if self._session:
            sql, params, model, map_to_model = self._build_sql(
                self._session.engine.dialect
            )  # type: ignore
            return self._rows_to_models(rows, model, map_to_model)
        raise ValueError("Session not bound to query.")

    async def first_async(self) -> Optional[T]:
        """Execute and return first result asynchronously - OPTIMIZED"""
        original_limit = self._limit
        self._limit = 1

        try:
            rows = await self._execute_async()
            if not self._session:
                raise ValueError("Session not bound to query.")
            sql, params, model, map_to_model = self._build_sql(
                self._session.engine.dialect
            )  # type: ignore

            results = self._rows_to_models(rows, model, map_to_model)
            return results[0] if results else None
        finally:
            self._limit = original_limit

    def _clone(self) -> "Select[T]":
        """Create a copy of the current Select instance"""
        new_select = Select(*self.entities)
        new_select._where = self._where[:]
        new_select._params = self._params[:]
        new_select._order_by = self._order_by[:]
        new_select._limit = self._limit
        new_select._offset = self._offset
        new_select._session = self._session
        new_select._joins = self._joins[:]
        new_select._distinct = self._distinct
        new_select._group_by = self._group_by[:]
        new_select._having = self._having[:]
        new_select._having_params = self._having_params[:]
        return new_select


def select(*entities):
    return Select(*entities)
