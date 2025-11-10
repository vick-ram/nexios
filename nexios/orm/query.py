import re
from typing import TYPE_CHECKING
from typing_extensions import (
    Type,
    TypeVar,
    Any,
    Self,
    Tuple,
    List,
    Union,
    Awaitable,
    Callable,
    Optional,
    Generic,
    Literal,
)
from nexios.orm.model import Model
from nexios.orm.backends.sessions import Session, AsyncSession

T = TypeVar("T", bound="Model")
R = TypeVar("R")

operator_map = {
    "eq": "=",
    "ne": "!=",
    "lt": "<",
    "lte": "<=",
    "gt": ">",
    "gte": ">=",
    "in": "IN",
    "not_in": "NOT IN",
    "like": "LIKE",
    "ilike": "ILIKE",  # Postgres specific
    "is_null": "IS NULL",
    "is_not_null": "IS NOT NULL",
    "contains": "LIKE",
}


class Query(Generic[T]):
    def __init__(self, session: Union["Session", "AsyncSession"], model_class: Type[T]) -> None:
        self.model_class: Type[T] = model_class
        self.session = session
        self._where: List[str] = []
        self._params: List[Any] = []
        self._order_by: List[str] = []
        self._limit: Optional[int] = None
        self._offset: Optional[int] = None
        self._joins: List[str] = []
        self._distinct: bool = False
        self._group_by: List[str] = []
        self._having: List[str] = []
        self._select_fields: List[str] = []

    def filter(self, **kwargs) -> Self:
        """Add WHERE condition to the query"""
        for key, value in kwargs.items():
            if "__" in key:
                field_name, operator = key.split("__", 1)

                sql_operator = self._get_operator_sql(operator)

                if operator in ("is_null", "is_not_null"):
                    self._where.append(f"{field_name} {sql_operator}")
                elif operator in ("in", "not_in"):
                    if not value:
                        # Handle empty IN clauses
                        self._where.append("1=0" if operator == "in" else "1=1")
                    else:
                        placeholder = ", ".join(["?"] * len(value))
                        self._where.append(
                            f"{field_name} {sql_operator} ({placeholder})"
                        )
                        self._params.extend(value)
                elif operator == "contains":
                    self._where.append(f"{field_name} {sql_operator} ?")
                    self._params.append(f"%{value}%")
                else:
                    self._where.append(f"{field_name} {sql_operator} ?")
                    self._params.append(value)
            else:
                # Handle simple equality
                if value is None:
                    self._where.append(f"{key} IS NULL")
                else:
                    self._where.append(f"{key} = ?")
                    self._params.append(value)
        return self

    def order_by(self, *fields: str) -> Self:
        """Add ORDER BY clause to the query"""
        for field in fields:
            if field.startswith("-"):
                self._order_by.append(f"{field[1:]} DESC")
            else:
                self._order_by.append(field)
        return self

    def limit(self, count: int) -> Self:
        """Set LIMIT for the query"""
        self._limit = count
        return self

    def offset(self, count: int) -> Self:
        """Set OFFSET for the query"""
        self._offset = count
        return self

    def join(
        self,
        table: str,
        on: str,
        type: Literal["inner", "left", "right", "full", "cross"] = "left",
    ) -> Self:
        """Add JOIN clause on the query"""
        query = self._clone()
        _join: str = 'inner'

        if type == 'inner':
            _join = 'INNER JOIN'
        elif type == 'left':
            _join = 'LEFT JOIN'
        elif type == 'right':
            _join = 'RIGHT JOIN'
        elif type == 'full':
            _join = 'FULL JOIN'
        elif type == 'cross':
            _join = 'CROSS JOIN'
        else:
            _join = 'INNER JOIN'

        # self._joins.append(f"JOIN {table} ON {on}")
        query._joins.append(f"{_join} {table} ON {on}")
        return query

    def select(self, *fields: str) -> Self:
        """Select specific fields instead of all"""
        self._select_fields.extend(fields)
        return self

    def count(self) -> Union[int, Awaitable[int]]:
        """Return count of records matching the query"""
        count_query = self._clone()
        count_query._select_fields = ["COUNT(*)"]
        count_query._order_by = []  # Remove ordering for count

        def transform_count(rows: List[Tuple[Any, ...]]) -> int:
            return rows[0][0] if rows else 0

        return self._execute(transform_count)

    def exists(self) -> Union[bool, Awaitable[bool]]:
        """Check if any recors match the query"""
        exist_query = self._clone()
        exist_query._limit = 1

        def transform_exists(rows: List[Tuple[Any, ...]]) -> bool:
            return len(rows) > 0

        return self._execute(transform_exists)

    def distinct(self) -> Self:
        """Add DISTINCT"""
        query = self._clone()

        if query._select_fields == ["*"]:
            query._select_fields = list(query.model_class._fields.keys())
        query._distinct = True
        return query

    def group_by(self, *fields: str) -> Self:
        """Add GROUP BY clause"""
        self._group_by.extend(fields)
        return self

    def having(self, condition: str, *params: Any) -> Self:
        """Add HAVING clause"""
        query = self._clone()
        query._having.append(condition)
        query._params.extend(params)
        return query

    def paginate(self, page: int = 1, per_page: int = 20) -> Self:
        """Pagination to the query"""
        if page < 1:
            raise ValueError("Page number must be >= 1")
        if per_page < 1:
            raise ValueError("Per page must be >= 1")

        query = self._clone()
        query._limit = per_page
        query._offset = (page - 1) * per_page
        return self

    def all(self) -> Union[List[T], Awaitable[List[T]]]:
        """Execute query to return all results"""
        return self._execute(self._rows_to_models)

    def first(self) -> Union[Optional[T], Awaitable[Optional[T]]]:
        query = self._clone()
        query._limit = 1

        def transform_first(rows: List[Tuple[Any, ...]]) -> Optional[T]:
            models = query._rows_to_models(rows)
            return models[0] if models else None

        return self._execute(transform_first)

    def _execute(
        self, result_transformer: Callable[[List[Tuple[Any, ...]]], R]
    ) -> Union[R, Awaitable[R]]:
        """Generic executon method that transforms results."""
        sql, params = self._build_sql()

        params_tuple = tuple(params)

        if isinstance(self.session, AsyncSession):

            async def async_exec() -> R:
                await self.session.execute(sql, params_tuple)
                rows = await self.session.fetchall() # type: ignore
                return result_transformer(rows)

            return async_exec()
        else:
            self.session.execute(sql, params_tuple)
            rows = self.session.fetchall()
            return result_transformer(rows)

    def _build_sql(self) -> Tuple[str, List[Any]]:
        """Build the SQL Query string and parameters."""
        query = self._clone()
        tablename = query.model_class.get_table_name()

        # Validate table name
        if not re.match(r"^[a-zA-Z_][a-zA-Z0-9_]*$", tablename):
            raise ValueError(f"Invalid table name: {tablename}")

        # Build SELECT with DISTINCT
        select_clause = "SELECT"
        if query._distinct:
            select_clause += "DISTINCT"

        if query._select_fields:
            escaped_fields = [f'"{field}"' for field in query._select_fields]
            selected_fields = ", ".join(escaped_fields)
        else:
            selected_fields = "*"

        # Build base query
        sql = f"{select_clause} {selected_fields} FROM {tablename}" 

        if query._joins:
            sql += " " + " ".join(query._joins)
        if query._where:
            sql += " WHERE " + " AND ".join(query._where)
        if query._group_by:
            sql += " GROUP BY " + ", ".join(query._group_by)
        if query._having:
            sql += " HAVING " + " AND ".join(query._having)
        if query._order_by:
            sql += " ORDER BY " + ", ".join(query._order_by)
        if query._limit is not None:
            sql += f" LIMIT {self._limit}"
        if query._offset is not None:
            sql += f" OFFSET {self._offset}"

        return sql, query._params

    def _rows_to_models(self, rows: List[Tuple[Any, ...]]) -> List[T]:
        """Convert database rows to model instances."""
        results: List[T] = []
        query = self._clone()

        # Get field mapping considering selected fields
        if query._select_fields and query._select_fields != ["*"]:
            field_names = query._select_fields
            # Validate that selected field exists in model
            for field in field_names:
                if field != "*" and field not in query.model_class._fields:
                    raise ValueError(
                        f"Field '{field}' does not exist in model '{query.model_class.__name__}'"
                    )
        else:
            field_names = list(query.model_class._fields.keys())

        for row in rows:
            if len(row) != len(field_names):
                raise ValueError(
                    f"Row length {len(row)} doesn't match model fields {len(field_names)}"
                )

            kwargs = {}
            for field_name, value in zip(field_names, row):
                # Handle field type conversion
                field_obj = query.model_class._fields.get(field_name) # type: ignore
                if field_obj and value is not None: # type: ignore
                    value = field_obj.to_python(value) # type: ignore
        
                kwargs[field_name] = value

            model = query.model_class(**kwargs)
            results.append(model)

        return results

    @staticmethod
    def _get_operator_sql(operator: str) -> str:
        """Convert a high-level operator to its SQL equivalent."""
        if operator not in operator_map:
            raise ValueError(f"Unsupported operator: {operator}")
        return operator_map[operator]

    def _clone(self) -> Self:
        """Create a copy of the current Query instance for immutability."""
        new_query = self.__class__(self.session, self.model_class)
        new_query._where = self._where[:]
        new_query._params = self._params[:]
        new_query._order_by = self._order_by[:]
        new_query._limit = self._limit
        new_query._offset = self._offset
        new_query._joins = self._joins[:]
        new_query._distinct = self._distinct
        new_query._group_by = self._group_by[:]
        new_query._having = self._having[:]
        new_query._select_fields = self._select_fields[:]
        return new_query
