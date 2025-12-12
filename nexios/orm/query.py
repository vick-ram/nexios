from __future__ import annotations
from typing import TypeAlias, cast

from typing_extensions import (
    Type,
    TypeVar,
    Any,
    Tuple,
    List,
    Union,
    Optional,
    Generic,
    Literal,
    Self,
    Dict,
    overload,
    TYPE_CHECKING
)
from nexios.orm.sessions import Session, AsyncSession

if TYPE_CHECKING:
    from nexios.orm.config import Dialect
    from nexios.orm.model import BaseModel

_T = TypeVar("_T", bound="BaseModel")
_M = TypeVar("_M", bound="BaseModel")


class BinaryExpression:
    def __init__(self, column_expr: ColumnExpression, operator: str, value: Any):
        self.column = column_expr
        self.operator = operator
        self.value = value

    def to_sql(self, placeholder: str = "?") -> Tuple[str, List[Any]]:
        col = str(self.column)

        col = self.column.field_name
        if self.value is None:
            if self.operator == "=":
                return f"{col} IS NULL", []
            if self.operator == "!=":
                return f"{col} IS NOT NULL", []
        
        if self.operator in ("IN", "NOT IN"):
            if not isinstance(self.value, (list, tuple)):
                raise ValueError(f"{self.operator} requires a list or tuple")
        
            if not self.value:
                if self.operator == "IN":
                    return '1 = 0', []
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
            if '%' not in value and '_' not in value:
                value = f"%{value}%"
            
            return f"{col} {self.operator} {placeholder}", [self.value]
        
        return f"{col} {self.operator} {placeholder}", [self.value]
    

class ColumnExpression(Generic[_T]):
    """Represents a column in a select expression"""

    def __init__(self, model_cls: Type[_T], field_name: str):
        self.model_cls = model_cls
        self.field_name = field_name

    def _binary(self, operator: str, value: Any) -> BinaryExpression:
        return BinaryExpression(self, operator, value)

    def __eq__(self, other: Any) -> BinaryExpression: # type: ignore[override]
        return self._binary("=", other)

    def __ne__(self, other: Any) -> BinaryExpression: # type: ignore[override]
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
    
    def in_(self, values: List[Any]) -> BinaryExpression:
        """IN operator for list values"""
        return self._binary("IN", values)
    
    def not_in(self, values: List[Any]) -> BinaryExpression:
        """NOT IN operator for list values"""
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
    
    def asc(self) -> str:
        """Order by ascending"""
        return f"{self} ASC"
    
    def desc(self) -> str:
        """Order by descending"""
        return f"{self} DESC"

    def label(self, alias: str) -> ColumnExpression[_T]:
        """Create an aliased column expression"""
        # For simplicity, we'll handle aliasing in the SQL builder
        self._alias = alias
        return self

    def __str__(self) -> str:
        if hasattr(self, "_alias"):
            return f'"{self.field_name}" AS "{self._alias}"'
        return f'"{self.field_name}"'

class ResultSet(Generic[_T]):
    """Base class for result sets"""
    def __init__(self, statement: Select[_T]) -> None:
        self.statement = statement

    def all(self) -> List[_T]:
        raise NotImplementedError

    def first(self) -> Optional[_T]:
        raise NotImplementedError

    def one(self) -> _T:
        raise NotImplementedError

    def count(self) -> int:
        raise NotImplementedError

    def exists(self) -> bool:
        raise NotImplementedError

class SyncResultSet(ResultSet[_T]):
    """Synchronous result set"""
    def __init__(self, statement: Select[_T], session: Session) -> None:
        super().__init__(statement)
        self.statement._bind(session)
    
    def all(self) -> List[_T]:
        return self.statement._all()

    def first(self) -> Optional[_T]:
        return self.statement._first()

    def one(self) -> _T:
        result = self.first()
        if result is None:
            raise ValueError("No row was found for one()")
        return result

    def count(self) -> int:
        return self.statement._count()

    def exists(self) -> bool:
        return self.statement._exists()


class AsyncResultSet(ResultSet[_T]):
    """Asynchronous result set"""
    def __init__(self, statement: Select[_T], session: AsyncSession) -> None:
        super().__init__(statement)
        self.statement._bind(session)

    async def all(self) -> List[_T]: # type: ignore[override]
        return await self.statement._all_async()

    async def first(self) -> Optional[_T]: # type: ignore[override]
        return await self.statement._first_async()

    async def one(self) -> _T: # type: ignore[override]
        result = await self.first()
        if result is None:
            raise ValueError("No row was found for one()")
        return result

    async def count(self) -> int: # type: ignore[override]
        return await self.statement._async_count()

    async def exists(self) -> bool: # type: ignore[override]
        return await self.statement._async_exists()

binary_expr_tuple: TypeAlias = Tuple[BinaryExpression]

class Select(Generic[_T]):
    def __init__(self, *entities: Any):
        self.entities = entities
        self._where: List[BinaryExpression] = []
        self._params: List[Any] = []
        self._order_by: List[Union[ColumnExpression, str]] = []
        self._limit: Optional[int] = None
        self._offset: Optional[int] = None
        self._session: Union[Session, AsyncSession, None] = None
        self._joins: List[Tuple[str, Type[BaseModel], Optional[str], Optional[BinaryExpression]]] = []
        self._distinct: bool = False
        self._group_by: List[Union[ColumnExpression, str]] = []
        self._having: List[BinaryExpression] = []
        self._table_aliases: Dict[Type[BaseModel], str] = {}
        self._alias_counter = 0
    
    def _generate_alias(self, model: Type[BaseModel]) -> str:
        """Generate unique table alias"""
        if model in self._table_aliases:
            return self._table_aliases[model]
        
        # Try to use model name as alias
        base_alias = model.__name__.lower()[:10]
        alias = base_alias
        
        # Ensure uniqueness
        counter = 1
        while alias in self._table_aliases.values():
            alias = f"{base_alias}{counter}"
            counter += 1
        
        self._table_aliases[model] = alias
        return alias

    def _bind(self, session: Any):
        self._session = session
    
    def where(self, *conditions: bool) -> Self:
        expr = cast(binary_expr_tuple, conditions)
        self._where.extend(expr)
        return self
    
    def and_where(self, *conditions: bool) -> Self:
        return self.where(*conditions)

    def order_by(self, *fields: Union[ColumnExpression[_T], str]) -> Self:
        self._order_by.extend(fields)
        return self

    def limit(self, n: int) -> Self:
        self._limit = n
        return self

    def offset(self, n: int) -> Self:
        self._offset = n
        return self
    
    def distinct(self) -> Self:
        """Add DISTINCT clause"""
        self._distinct = True
        return self

    def group_by(self, *fields: Union[ColumnExpression, str]) -> Self:
        """Add GROUP BY clause"""
        self._group_by.extend(fields)
        return self

    def having(self, *conditions: BinaryExpression) -> Self:
        """Add HAVING clause"""
        self._having.extend(conditions)
        return self
    
    def _transform_count(self, rows: List[Tuple[Any, ...]]) -> int:
            return rows[0][0] if rows else 0
    
    async def _async_count(self) -> int:
        count_select = self._clone()
        count_select.entities = ("COUNT(*)",)
        count_select._order_by = []  # Remove ordering for count
        count_select._limit = None
        count_select._offset = None

        rows = await count_select._execute_async()
        return self._transform_count(rows)


    def _count(self) -> int:
        """Return count of records matching the query"""
        count_select = self._clone()
        count_select.entities = ("COUNT(*)",)
        count_select._order_by = []  # Remove ordering for count
        count_select._limit = None
        count_select._offset = None
    
        rows = count_select._execute_sync()
        return self._transform_count(rows)
    
    def _transform_exists(self, rows: List[Tuple[Any, ...]]) -> bool:
            return len(rows) > 0
    
 
    async def _async_exists(self) -> bool:
        exists_select = self._clone()
        exists_select._limit = 1
        exists_select.entities = "1"

        rows = await exists_select._execute_async()
        return self._transform_exists(rows)

    def _exists(self) -> bool:
        """Check if any records match the query"""
        exists_select = self._clone()
        exists_select._limit = 1
        exists_select.entities = "1"

        rows = exists_select._execute_sync()
        return self._transform_exists(rows)

    def join(
        self,
        right_model: Type[BaseModel],
        on_condition: Union[BinaryExpression, str, None] = None,
        join_type: Literal["inner", "left", "right", "full", "cross"] = "left",
        alias: Optional[str] = None,
    ) -> Self:
        """Add JOIN clause on the query"""
        join_alias = alias or self._generate_alias(right_model)

        self._joins.append(join_type, right_model, join_alias, on_condition) # type: ignore
        return self

    def left_join(
        self,
        right_model: Type[BaseModel],
        on_condition: Union[BinaryExpression, str, None] = None,
        alias: Optional[str] = None,
    ) -> Self:
        return self.join(right_model, on_condition, "left", alias)

    def inner_join(
        self,
        right_model: Type[BaseModel],
        on_condition: Union[BinaryExpression, str, None] = None,
        alias: Optional[str] = None,
    ) -> Self:
        """Convenience method for INNER JOIN"""
        return self.join(right_model, on_condition, "inner", alias)

    def right_join(
        self,
        right_model: Type[BaseModel],
        on_condition: Union[BinaryExpression, str, None] = None,
        alias: Optional[str] = None,
    ) -> Self:
        """Convenience method for RIGHT JOIN"""
        return self.join(right_model, on_condition, "right", alias)

    def _infer_join_condition(self, left_model: Type[BaseModel], right_model: Type[BaseModel]) -> BinaryExpression:
        """Try to infer condition based on field names"""
        left_fields = left_model.get_fields()
        right_fields = right_model.get_fields()

        # 1. Check foreign keys in left model pointing to right model
        for left_field_name, left_info in left_fields.items():
            if left_info.foreign_key:
                fk_parts = left_info.foreign_key.split('.')
                if len(fk_parts) == 2 and fk_parts[0] == right_model.__name__:
                    left_col = ColumnExpression(left_model, left_field_name)
                    right_col = ColumnExpression(right_model, fk_parts[1])
                    return BinaryExpression(left_col, "=", right_col)

        # 2. Check foreign keys in right model pointing to left model
        for right_field_name, right_info in right_fields.items():
            if right_info.foreign_key:
                fk_parts = right_info.foreign_key.split('.')
                if len(fk_parts) == 2 and fk_parts[0] == left_model.__name__:
                    left_col = ColumnExpression(left_model, fk_parts[1])
                    right_col = ColumnExpression(right_model, right_field_name)
                    return BinaryExpression(left_col, "=", right_col)
        
        # 3. Check relationships defined in ORM config
        left_relationships = left_model.__orm_config__.relationships
        for rel_name, rel_info in left_relationships.items():
            if rel_info.get('related_class') == right_model:
                fk = rel_info.get('foreign_key')
                if fk:
                    fk_parts = fk.split('.')
                    if len(fk_parts) == 2:
                        left_col = ColumnExpression(left_model, fk_parts[1])
                        right_col = ColumnExpression(right_model, fk_parts[0])
                        return BinaryExpression(left_col, "=", right_col)
        
        # 4. Common naming conventions
        possible_fks = [
            f"{left_model.__name__.lower()}_id",
            f"{left_model.__orm_config__.table_name}_id",
            f"{left_model.__name__}Id",
            f"{left_model.__name__}ID",
        ]

        for fk_name in possible_fks:
            if fk_name in right_fields:
                left_pk = left_model.get_primary_key()
                if left_pk:
                    left_col = ColumnExpression(left_model, left_pk)
                    right_col = ColumnExpression(right_model, fk_name)
                    return BinaryExpression(left_col, "=", right_col)
        
        # 5. Reverse
        reverse_fks = [
            f"{right_model.__name__.lower()}_id",
            f"{right_model.__orm_config__.table_name}_id",
            f"{right_model.__name__}Id",
            f"{right_model.__name__}ID",
        ]

        for fk_name in reverse_fks:
            if fk_name in left_model.get_fields():
                right_pk = right_model.get_primary_key()
                if right_pk:
                    left_col = ColumnExpression(left_model, fk_name)
                    right_col = ColumnExpression(right_model, right_pk)
                    return BinaryExpression(left_col, "=", right_col)
        
        # Lastly: if models have same primary key name
        left_pk = left_model.get_primary_key()
        right_pk = right_model.get_primary_key()
        
        if left_pk and right_pk and left_pk == right_pk:
            left_col = ColumnExpression(left_model, left_pk)
            right_col = ColumnExpression(right_model, right_pk)
            return BinaryExpression(left_col, "=", right_col)
        
        raise ValueError(
            f"Cannot infer join condition between {left_model.__name__} "
            f"and {right_model.__name__}. Please provide explicit condition.\n"
            f"Left model fields: {list(left_model.get_fields().keys())}\n"
            f"Right model fields: {list(right_model.get_fields().keys())}\n"
            f"Left model relationships: {list(left_model.__orm_config__.relationships.keys())}"
        )

    def _get_primary_model(self) -> Optional[Type["BaseModel"]]:
        from nexios.orm.model import BaseModel
        
        """Get the primary model from selected entities"""
        for entity in self.entities:
            if isinstance(entity, type) and issubclass(entity, BaseModel):
                return entity
            elif isinstance(entity, ColumnExpression):
                return entity.model_cls
        return None

    def _get_param_placeholder(self, dialect: Dialect) -> str:
        from nexios.orm.config import MySQLDialect, PostgreSQLDialect

        if isinstance(dialect, PostgreSQLDialect):
            return "%s"
        elif isinstance(dialect, MySQLDialect):
            return "%s"
        else:
            return "?"

    def _build_sql(self, dialect: Dialect):
        from nexios.orm.model import BaseModel
        param_placeholder = self._get_param_placeholder(dialect)
        params: List[Any] = []
        primary_model = self._get_primary_model()

        if not primary_model:
            raise ValueError("Could not determine primary model from selected entities")
        
        select_parts = []
        map_to_model = False

        for entity in self.entities:
            if isinstance(entity, type) and issubclass(entity, BaseModel):
                if entity == primary_model:
                    table_name = entity.__orm_config__.table_name
                    assert table_name is not None
                    quoted_table = dialect.quote_identifier(table_name)
                    
                    for field_name in entity.get_fields().keys():
                        quoted_field = dialect.quote_identifier(field_name)
                        select_parts.append(f"{quoted_table}.{quoted_field}")
                    map_to_model = True
                else:
                    alias = self._table_aliases.get(entity, entity.__orm_config__.table_name)
                    quoted_alias = dialect.quote_identifier(alias) # type: ignore

                    for field_name in entity.get_fields().keys():
                        quoted_field = dialect.quote_identifier(field_name)
                        select_alias = dialect.quote_identifier(f"{alias}_{field_name}")
                        select_parts.append(f"{quoted_alias}.{quoted_field} AS {select_alias}")
            elif isinstance(entity, ColumnExpression):
                select_parts.append(str(entity))
            elif isinstance(entity, str):
                select_parts.append(entity)


        # Build SELECT clause with distinct
        distinct_clause = "DISTINCT " if self._distinct else ""
        select_clause = f"SELECT {distinct_clause}{', '.join(select_parts)}"

        primary_table = primary_model.__orm_config__.table_name
        primary_alias = self._table_aliases.get(primary_model, primary_table)
        assert primary_alias is not None
        assert primary_table is not None
        from_clause = f"FROM {dialect.quote_identifier(primary_table)}"
        if primary_alias != primary_table:
            from_clause += f" AS {dialect.quote_identifier(primary_alias)}"
        
        sql_parts = [select_clause, from_clause]

        # JOIN clauses
        for join_type, right_model, alias, condition in self._joins:
            right_table = right_model.__orm_config__.table_name
            quoted_right_table = dialect.quote_identifier(right_table) # type: ignore
            quoted_alias = dialect.quote_identifier(alias) # type: ignore

            if condition is None:
                condition = self._infer_join_condition(primary_model, right_model)
            
            if isinstance(condition, BinaryExpression):
                on_sql, on_params = condition.to_sql(param_placeholder)
                params.append(on_params)
            elif isinstance(condition, str):
                on_sql = condition
            else:
                on_sql = "1=1"
            
            join_sql = f"{join_type} JOIN {quoted_right_table} AS {quoted_alias} ON {on_sql}"
            sql_parts.append(join_sql)           

        # WHERE
        if self._where:
            where_parts = []
            for cond in self._where:
                sql_part, p = cond.to_sql(param_placeholder)
                where_parts.append(sql_part)
                params.extend(p)
            where_clause = " AND ".join(where_parts)
            sql_parts.append(f"WHERE {where_clause}")

        # GROUP BY clause
        if self._group_by:
            group_parts = []
            for field in self._group_by:
                if isinstance(field, ColumnExpression):
                    group_parts.append(str(field))
                else:
                    group_parts.append(field)
            group_clause = "GROUP BY " + ", ".join(group_parts)
            sql_parts.append(group_clause)

        # HAVING clause
        if self._having:
            having_parts = []
            for condition in self._having:
                cond_sql, cond_params = condition.to_sql(param_placeholder)
                params.extend(cond_params)
                having_parts.append(cond_sql)
            having_clause = "HAVING " + " AND ".join(having_parts)
            sql_parts.append(having_clause)

        # ORDER BY
        if self._order_by:
            order_parts = []
            for field in self._order_by:
                if isinstance(field, ColumnExpression):
                    order_parts.append(str(field))
                else:
                    order_parts.append(field)
            
            order_clause = "ORDER BY " + ", ".join(order_parts)
            sql_parts.append(order_clause)

        # LIMIT and OFFSET
        if self._limit is not None:
            sql_parts.append(f"LIMIT {self._limit}")

        if self._offset is not None:
            sql_parts.append(f"OFFSET {self._offset}")

        sql = " ".join(sql_parts)

        return sql, params, primary_model, map_to_model

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

    # Sync methods
    def _all(self) -> List[_T]:
        """Execute and return all results"""
        rows = self._execute_sync()
        if self._session:
            sql, params, model, map_to_model = self._build_sql(self._session.engine.dialect)
            return self._rows_to_models(rows, model, map_to_model)
        else:
            raise ValueError("Session not bound to query.")

    def _first(self) -> Optional[_T]:
        """Execute and return first result - OPTIMIZED"""
        original_limit = self._limit
        self._limit = 1

        try:
            rows = self._execute_sync()
            if not self._session:
                raise ValueError("Session not bound to query.")
            sql, params, model, map_to_model = self._build_sql(
                self._session.engine.dialect
            )
            results = self._rows_to_models(rows, model, map_to_model)
            return results[0] if results else None
        finally:
            self._limit = original_limit

    # Async methods
    async def _all_async(self) -> List[_T]:
        """Execute and return all results asynchronously"""
        rows = await self._execute_async()
        if self._session:
            sql, params, model, map_to_model = self._build_sql(
                self._session.engine.dialect
            )
            return self._rows_to_models(rows, model, map_to_model)
        raise ValueError("Session not bound to query.")

    async def _first_async(self) -> Optional[_T]:
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
    
    def _rows_to_models(self, rows: List[Tuple[Any, ...]], model: Type[BaseModel], map_to_model: bool) -> List[Any]:
        """Convert DB rows into model instances (uses pydantic parsing when available)."""
        results: List[Any] = []
        if not rows:
            return results

        if map_to_model:
            # assume columns for the primary model come first in the result set
            field_names = list(model.get_fields().keys())
            n = len(field_names)
            for row in rows:
                values = row[:n]
                data = {name: val for name, val in zip(field_names, values)}
                # prefer pydantic-style parsing if provided
                if hasattr(model, "model_validate"):
                    inst = model.model_validate(data)
                else:
                    inst = model(**data)
                results.append(inst)
            return results

        # Not mapping to a model: return scalar for single-column selects, else tuples
        for row in rows:
            if len(row) == 1:
                results.append(row[0])
            else:
                results.append(row)
        return results

    def _clone(self) -> "Select[_T]":
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
        new_select._table_aliases = self._table_aliases.copy()
        new_select._alias_counter = self._alias_counter
        return new_select

@overload
def select(entity: Type[_T]) -> Select[_T]:
    """Single model select"""
    
@overload
def select(*entities: Type[_M]) -> Select[_M]:
    """"""

@overload
def select(*entities: ColumnExpression[Any]) -> Select[Any]:
    ...

@overload
def select(*entities: Union[Type[_M], ColumnExpression[Any], str]) -> Select[Any]:
    ...

def select(
    entity: Union[Type[_T], ColumnExpression[Any], str],
    *entities: Union[Type[_M], ColumnExpression[Any], str],
):
    """Create a SELECT query.
    
    Examples:
        >>> query = select(User)  # Select[User]
        >>> query = select(User, Post)  # Select[Any] (tuple/union)
        >>> query = select(User.name, User.email)  # Select[Any] (tuple)
    """
    return Select(entity, *entities)
