from __future__ import annotations

from collections import defaultdict
import re
from typing import TypeAlias, cast, Callable, Any

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
    TYPE_CHECKING,
)
from pydantic_core import PydanticUndefined as Undefined
from nexios.orm.query.expressions import ColumnExpression, BinaryExpression, AlwaysTrueExpression, AlwaysFalseExpression
from nexios.orm.sessions import Session, AsyncSession

if TYPE_CHECKING:
    from nexios.orm.config import Dialect
    from nexios.orm.model import NexiosModel
    from nexios.orm.model import RelationshipType
    from nexios.orm.model import InstanceOrType

_T = TypeVar("_T", bound="NexiosModel")
_M = TypeVar("_M", bound="NexiosModel")


_BinaryExpressionTuple: TypeAlias = Tuple[BinaryExpression]
_UnionBinaryExpression: TypeAlias = Union[BinaryExpression, str, None]


class Select(Generic[_T]):
    def __init__(self, *entities: Any):
        self.entities = entities
        self._where: List[BinaryExpression] = []
        self._params: List[Any] = []
        self._order_by: List[Union[ColumnExpression, str]] = []
        self._limit: Optional[int] = None
        self._offset: Optional[int] = None
        self._session: Union[Session, AsyncSession, None] = None
        self._joins: List[
            Tuple[str, Type[NexiosModel], Optional[str], Optional[BinaryExpression]]
        ] = []
        self._distinct: bool = False
        self._group_by: List[Union[ColumnExpression, str]] = []
        self._having: List[BinaryExpression] = []
        self._table_aliases: Dict[Type[NexiosModel], str] = {}
        self._alias_counter = 0

        self._eager_load: Dict[str, List[str]] = {}
        self._joined_load: Dict[str, List[str]] = {}

    def _generate_alias(self, model: Type[NexiosModel]) -> str:
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
        expr = cast(_BinaryExpressionTuple, cast(object, conditions))

        for condition in expr:
            if condition is True:
                self._where.append(AlwaysTrueExpression()) # type: ignore
            elif condition is False:
                self._where.append(AlwaysFalseExpression()) # type: ignore
            else:
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
        primary_model = self._get_primary_model()
        count_select.entities = ("COUNT(*)", primary_model)
        count_select._order_by = []  # Remove ordering for count
        count_select._limit = None
        count_select._offset = None

        rows = await count_select._execute_async()
        return self._transform_count(rows)

    def _count(self) -> int:
        """Return count of records matching the query"""
        count_select = self._clone()
        primary_model = self._get_primary_model()
        count_select.entities = ("COUNT(*)", primary_model)
        count_select._order_by = []  # Remove ordering for count
        count_select._limit = None
        count_select._offset = None

        rows = count_select._execute_sync()
        return self._transform_count(rows)

    def _transform_exists(self, rows: List[Tuple[Any, ...]]) -> bool:
        return len(rows) > 0

    async def _async_exists(self) -> bool:
        exists_select = self._clone()
        primary_model = self._get_primary_model()
        exists_select._limit = 1
        exists_select.entities = ("1", primary_model)

        rows = await exists_select._execute_async()
        return self._transform_exists(rows)

    def _exists(self) -> bool:
        """Check if any records match the query"""
        exists_select = self._clone()
        primary_model = self._get_primary_model()
        exists_select._limit = 1
        exists_select.entities = ("1", primary_model)

        rows = exists_select._execute_sync()
        return self._transform_exists(rows)

    def join(
        self,
        right_model: Type[NexiosModel],
        on_condition: Optional[bool] = None,
        join_type: Literal["inner", "left", "right", "full", "cross"] = "left",
        alias: Optional[str] = None,
    ) -> Self:
        """Add JOIN clause on the query"""
        expression = cast(_UnionBinaryExpression, on_condition)
        join_alias = alias or self._generate_alias(right_model)

        self._joins.append((join_type, right_model, join_alias, expression))  # type: ignore
        return self

    def left_join(
        self,
        right_model: Type[NexiosModel],
        on_condition: Optional[bool] = None,
        alias: Optional[str] = None,
    ) -> Self:
        return self.join(right_model, on_condition, "left", alias)

    def inner_join(
        self,
        right_model: Type[NexiosModel],
        on_condition: Optional[bool] = None,
        alias: Optional[str] = None,
    ) -> Self:
        """Convenience method for INNER JOIN"""
        return self.join(right_model, on_condition, "inner", alias)

    def right_join(
        self,
        right_model: Type[NexiosModel],
        on_condition: Optional[bool] = None,
        alias: Optional[str] = None,
    ) -> Self:
        """Convenience method for RIGHT JOIN"""
        return self.join(right_model, on_condition, "right", alias)

    def eager_load(self, *relationships: str) -> Self:
        """Add eager loading to the query"""
        for rel_path in relationships:
            print(f"Relationship path: {rel_path}")
            parts = rel_path.split(".") or rel_path.split("_")
            if len(parts) == 1:
                self._eager_load.setdefault("*", []).append(rel_path)
            else:
                parent = parts[0]
                child = ".".join(parts[1:])
                self._eager_load.setdefault(parent, []).append(child)
        return self

    def joined_load(self, *relationships: str) -> Self:
        """Add joined loading to the query"""
        for rel_path in relationships:
            parts = rel_path.split(".") or rel_path.split("_")
            if len(parts) == 1:
                self._joined_load.setdefault("*", []).append(rel_path)
            else:
                parent = parts[0]
                child = ".".join(parts[1:]) or "_".join(parts[1:])
                self._joined_load.setdefault(parent, []).append(child)
        return self

    def _infer_join_condition(
        self, left_model: Type[NexiosModel], right_model: Type[NexiosModel]
    ) -> BinaryExpression:
        """Try to infer condition based on field names"""
        left_fields = left_model.get_fields()
        right_fields = right_model.get_fields()

        # 1. Check foreign keys in left model pointing to right model
        for left_field_name, left_info in left_fields.items():
            left_fk = getattr(left_info, "foreign_key", Undefined)
            if left_fk is not Undefined:
                fk_parts = left_info.foreign_key.split(
                    "."
                ) or left_info.foreign_key.split("_")
                if len(fk_parts) == 2 and fk_parts[0] == right_model.__name__:
                    left_col = ColumnExpression(left_model, left_field_name)
                    right_col = ColumnExpression(right_model, fk_parts[1])
                    return BinaryExpression(left_col, "=", right_col)

        # 2. Check foreign keys in right model pointing to left model
        for right_field_name, right_info in right_fields.items():
            right_fk = getattr(right_info, "foreign_key", Undefined)
            if right_fk is not Undefined:
                fk_parts = right_info.foreign_key.split(
                    "."
                ) or right_info.foreign_key.split("_")
                if len(fk_parts) == 2 and fk_parts[0] == left_model.__name__:
                    left_col = ColumnExpression(left_model, fk_parts[1])
                    right_col = ColumnExpression(right_model, right_field_name)
                    return BinaryExpression(left_col, "=", right_col)

        # 3. Check relationships defined in ORM config
        left_relationships = left_model.get_relationships()
        for rel_name, rel_info in left_relationships.items():
            if rel_info.related_model == right_model:
                fk = rel_info.foreign_key
                if fk:
                    fk_parts = re.split(r"[._]", fk)
                    if len(fk_parts) == 2:
                        left_col = ColumnExpression(left_model, fk_parts[1])
                        right_col = ColumnExpression(right_model, fk_parts[0])
                        return BinaryExpression(left_col, "=", right_col)

        # 4. Common naming conventions
        possible_fks = [
            f"{left_model.__name__.lower()}_id",
            f"{left_model.__tablename__}_id",
            f"{left_model.__name__}Id",
            f"{left_model.__name__}ID",
        ]

        for fk_name in possible_fks:
            if fk_name in right_fields:
                left_pk = self._get_primary_key_field(left_model)
                if left_pk:
                    left_col = ColumnExpression(left_model, left_pk)
                    right_col = ColumnExpression(right_model, fk_name)
                    return BinaryExpression(left_col, "=", right_col)

        # 5. Reverse
        reverse_fks = [
            f"{right_model.__name__.lower()}_id",
            f"{right_model.__tablename__}_id",
            f"{right_model.__name__}Id",
            f"{right_model.__name__}ID",
        ]

        for fk_name in reverse_fks:
            if fk_name in left_model.get_fields():
                right_pk = self._get_primary_key_field(right_model)
                if right_pk:
                    left_col = ColumnExpression(left_model, fk_name)
                    right_col = ColumnExpression(right_model, right_pk)
                    return BinaryExpression(left_col, "=", right_col)

        # Lastly: if models have same primary key name
        left_pk = self._get_primary_key_field(left_model)
        right_pk = self._get_primary_key_field(right_model)

        if left_pk and right_pk and left_pk == right_pk:
            left_col = ColumnExpression(left_model, left_pk)
            right_col = ColumnExpression(right_model, right_pk)
            return BinaryExpression(left_col, "=", right_col)

        raise ValueError(
            f"Cannot infer join condition between {left_model.__name__} "
            f"and {right_model.__name__}. Please provide explicit condition.\n"
            f"Left model fields: {list(left_model.get_fields().keys())}\n"
            f"Right model fields: {list(right_model.get_fields().keys())}\n"
            f"Left model relationships: {list(left_model.get_relationships().keys())}"
        )

    def _get_primary_model(self) -> Optional[Type["NexiosModel"]]:
        from nexios.orm.model import NexiosModel

        for entity in self.entities:
            if isinstance(entity, type) and issubclass(entity, NexiosModel):
                return entity
            elif isinstance(entity, ColumnExpression):
                return entity.model_cls
        return None

    def _build_sql(self, dialect: Dialect, driver):
        from nexios.orm.model import NexiosModel
        from nexios.orm.config import get_param_placeholder

        param_placeholder = get_param_placeholder(driver)
        params: List[Any] = []
        primary_model = self._get_primary_model()

        if not primary_model:
            raise ValueError("Could not determine primary model from selected entities")

        select_parts = []
        map_to_model = False

        has_count = any(
            isinstance(entity, str) and entity.startswith("COUNT")
            for entity in self.entities
        )
        has_exists = any(
            isinstance(entity, str) and entity.startswith("1")
            for entity in self.entities
        )

        for entity in self.entities:
            if isinstance(entity, type) and issubclass(entity, NexiosModel):
                if has_count or has_exists:
                    continue

                if entity == primary_model:
                    table_name = entity.__tablename__
                    assert table_name is not None
                    quoted_table = dialect.quote_identifier(table_name)

                    for field_name in entity.get_fields().keys():
                        quoted_field = dialect.quote_identifier(field_name)
                        select_parts.append(f"{quoted_table}.{quoted_field}")
                    # map_to_model = True
                else:
                    alias = self._table_aliases.get(entity, entity.__tablename__)
                    quoted_alias = dialect.quote_identifier(alias)  # type: ignore

                    for field_name in entity.get_fields().keys():
                        quoted_field = dialect.quote_identifier(field_name)
                        select_alias = dialect.quote_identifier(f"{alias}_{field_name}")
                        select_parts.append(
                            f"{quoted_alias}.{quoted_field} AS {select_alias}"
                        )
            elif isinstance(entity, ColumnExpression):
                # select_parts.append(str(entity))
                table_name = entity.model_cls.__tablename__
                table_alias = self._table_aliases.get(entity.model_cls, table_name)

                select_parts.append(entity.to_sql(dialect, table_alias))
            elif isinstance(entity, str):
                select_parts.append(entity)

        model_entities = [
            e
            for e in self.entities
            if isinstance(e, type) and issubclass(e, NexiosModel)
        ]
        if len(model_entities) == 1 and not has_count and not has_exists:
            map_to_model = True

        # Build SELECT clause with distinct
        distinct_clause = "DISTINCT " if self._distinct else ""
        select_clause = f"SELECT {distinct_clause}{', '.join(select_parts)}"

        primary_table = primary_model.__tablename__
        primary_alias = self._table_aliases.get(primary_model, primary_table)
        assert primary_alias is not None
        assert primary_table is not None
        from_clause = f"FROM {dialect.quote_identifier(primary_table)}"
        if primary_alias != primary_table:
            from_clause += f" AS {dialect.quote_identifier(primary_alias)}"

        sql_parts = [select_clause, from_clause]

        # JOIN clauses
        for join_type, right_model, alias, condition in self._joins:
            right_table = right_model.__tablename__
            quoted_right_table = dialect.quote_identifier(right_table)  # type: ignore
            quoted_alias = dialect.quote_identifier(alias)  # type: ignore

            if condition is None:
                condition = self._infer_join_condition(primary_model, right_model)

            if isinstance(condition, BinaryExpression):
                left_col = condition.column
                right_val = condition.value

                left_table_alias = self._table_aliases.get(
                    left_col.model_cls, left_col.model_cls.__tablename__
                )

                quoted_left = (
                    dialect.quote_identifier(left_table_alias) # type: ignore
                    + "."
                    + dialect.quote_identifier(  # type: ignore
                        left_col.field_name
                    )
                )

                if isinstance(right_val, ColumnExpression):
                    right_table_alias = self._table_aliases.get(
                        right_val.model_cls, right_val.model_cls.__tablename__
                    )
                    quoted_right = (
                        dialect.quote_identifier(right_table_alias) # type: ignore
                        + "."
                        + dialect.quote_identifier(  # type: ignore
                            right_val.field_name
                        )
                    )
                    on_sql = f"{quoted_left} {condition.operator} {quoted_right}"
                    on_params = []
                else:
                    on_sql = f"{quoted_left} {condition.operator} {param_placeholder}"
                    on_params = [right_val] if right_val is not None else []
                # on_sql, on_params = condition.to_sql(param_placeholder, dialect)
                params.extend(on_params)
            elif isinstance(condition, str):
                on_sql = condition
            else:
                on_sql = "1=1"

            join_sql = (
                f"{join_type} JOIN {quoted_right_table} AS {quoted_alias} ON {on_sql}"
            )
            sql_parts.append(join_sql)

        # WHERE
        if self._where:
            where_parts = []
            for cond in self._where:
                if self._joins:
                    left_col = cond.column
                    left_table_alias = self._table_aliases.get(
                        left_col.model_cls, left_col.model_cls.__tablename__
                    )
                    quoted_left = (
                        dialect.quote_identifier(left_table_alias) # type: ignore
                        + "."
                        + dialect.quote_identifier(  # type: ignore
                            left_col.field_name
                        )
                    )
                    if isinstance(cond.value, ColumnExpression):
                        right_col = cond.value
                        right_table_alias = self._table_aliases.get(
                            right_col.model_cls, right_col.model_cls.__tablename__
                        )
                        quoted_right = (
                            dialect.quote_identifier(right_table_alias) # type: ignore
                            + "."
                            + dialect.quote_identifier(  # type: ignore
                                right_col.field_name
                            )
                        )
                        sql_part = f"{quoted_left} {cond.operator} {quoted_right}"
                        p = []
                    else:
                        # Value comparison
                        sql_part = f"{quoted_left} {cond.operator} {param_placeholder}"
                        p = [cond.value] if cond.value is not None else []
                else:
                    sql_part, p = cond.to_sql(param_placeholder, dialect, driver)

                where_parts.append(sql_part)
                params.extend(p)
            where_clause = " AND ".join(where_parts)
            sql_parts.append(f"WHERE {where_clause}")

        # GROUP BY clause
        if self._group_by:
            group_parts = []
            for field in self._group_by:
                if isinstance(field, ColumnExpression):
                    # group_parts.append(str(field))
                    table_name = field.model_cls.__tablename__
                    table_alias = self._table_aliases.get(field.model_cls, table_name)
                    group_parts.append(field.to_sql(dialect, table_alias))
                else:
                    group_parts.append(field)
            group_clause = "GROUP BY " + ", ".join(group_parts)
            sql_parts.append(group_clause)

        # HAVING clause
        if self._having:
            having_parts = []
            for condition in self._having:
                cond_sql, cond_params = condition.to_sql(param_placeholder, dialect)
                params.extend(cond_params)
                having_parts.append(cond_sql)
            having_clause = "HAVING " + " AND ".join(having_parts)
            sql_parts.append(having_clause)

        # ORDER BY
        if self._order_by:
            order_parts = []
            for field in self._order_by:
                if isinstance(field, ColumnExpression):
                    # order_parts.append(str(field))
                    table_name = field.model_cls.__tablename__
                    table_alias = self._table_aliases.get(field.model_cls, table_name)

                    sql = field.to_sql(dialect, table_alias)
                    if getattr(field, "_order_desc", False):
                        sql += " DESC"
                    order_parts.append(sql)
                else:
                    order_parts.append(field)

            order_clause = "ORDER BY " + ", ".join(order_parts)
            sql_parts.append(order_clause)

        # LIMIT and OFFSET
        limit_sql = dialect.get_limit_offset_sql(self._limit, self._offset)
        if limit_sql:
            sql_parts.append(limit_sql)

        sql = " ".join(sql_parts)

        return sql, params, primary_model, map_to_model

    def _execute_sync(self) -> List[Tuple[Any, ...]]:
        """Execute query synchronously"""
        if not self._session or not isinstance(self._session, Session):
            raise ValueError("No sync session bound to this query")

        sql, params, model, map_to_model = self._build_sql(
            self._session.engine.dialect, self._session.engine.driver
        )
        return self._session.execute(sql, tuple(params)).fetchall()

    async def _execute_async(self) -> List[Tuple[Any, ...]]:
        """Execute query asynchronously"""
        if not self._session or not isinstance(self._session, AsyncSession):
            raise ValueError("No async session bound to this query")

        sql, params, model, map_to_model = self._build_sql(
            self._session.engine.dialect, self._session.engine.driver
        )
        return await (await self._session.execute(sql, tuple(params))).fetchall()

    def _execute_with_eager_loading(self, rows_func: Callable):
        """Execute query with eager loading support"""
        # First, get the main results
        results = rows_func()

        if not results or not self._eager_load:
            return results

        # Load eager relationships
        self._load_eager_relationships(results)

        return results

    def _load_eager_relationships(self, instances: List[Any]):
        """Load eager relationships for a list of instances"""
        from nexios.orm.model import RelationshipType

        if not instances:
            return

        session = self._session
        if not session:
            return

        # Group relationships by type for batch loading
        relationships_to_load = defaultdict(list)

        for rel_name in self._eager_load.get("*", []):
            for instance in instances:
                relationships_to_load[rel_name].append(instance)

        # Batch load each relationship
        for rel_name, rel_instances in relationships_to_load.items():
            if not rel_instances:
                continue

            # Get relationship info from first instance
            first_instance = rel_instances[0]
            model_class = type(first_instance)

            if rel_name not in model_class.__relationships__:
                continue

            rel_info = model_class.__relationships__[rel_name]

            # Batch load based on relationship type
            if rel_info.relationship_type in (RelationshipType.MANY_TO_ONE, RelationshipType.ONE_TO_ONE):
                self._batch_load_many_to_one(rel_instances, rel_name, rel_info, session)
            elif rel_info.relationship_type == RelationshipType.ONE_TO_MANY:
                self._batch_load_one_to_many(rel_instances, rel_name, rel_info, session)

    def _batch_load_many_to_one(self, instances, rel_name, rel_info, session: Any):
        """Batch load many-to-one relationships to avoid N+1"""
        # Collect foreign key values
        fk_values = []
        instance_map = {}
        
        is_inverse_one_to_one = rel_info.relationship_type == RelationshipType.ONE_TO_ONE and not rel_info.foreign_key

        if is_inverse_one_to_one:
            # For inverse 1:1, we load like a 1:M but expect single result
            return self._batch_load_one_to_many(instances, rel_name, rel_info, session)

        if not rel_info.foreign_key:
            return

        for instance in instances:
            fk_value = getattr(instance, rel_info.foreign_key, None)
            if fk_value is not None:
                fk_values.append(fk_value)
                instance_map[fk_value] = instance

        if not fk_values:
            return

        # Fetch all related objects in one query
        related_model = rel_info.related_model
        pk_field = self._get_primary_key_field(related_model)

        query = select(related_model).where(
            getattr(related_model, pk_field).in_(fk_values)
        )
        query._bind(session)

        related_objects = query._all()

        # Map back to instances
        for obj in related_objects:
            pk_value = getattr(obj, pk_field)
            if pk_value in instance_map:
                instance = instance_map[pk_value]
                self._set_relationship_cache(instance, rel_name, obj)

    def _batch_load_one_to_many(self, instances, rel_name, rel_info, session):
        """Batch load one-to-many relationships to avoid N+1"""
        if not rel_info.foreign_key:
            return

        # Collect primary key values
        pk_values = []
        instance_map = {}

        for instance in instances:
            pk_name = self._get_primary_key_field(instance)
            pk_value = getattr(instance, pk_name)
            pk_values.append(pk_value)
            instance_map[pk_value] = instance

        if not pk_values:
            return

        # Fetch all related objects in one query
        related_model = rel_info.related_model

        query = select(related_model).where(
            getattr(related_model, rel_info.foreign_key).in_(pk_values)
        )
        query._bind(session)

        all_related = query._all()

        # Group by foreign key
        related_by_fk = defaultdict(list)
        for obj in all_related:
            fk_value = getattr(obj, rel_info.foreign_key)
            related_by_fk[fk_value].append(obj)

        # Map back to instances
        for pk_value, instance in instance_map.items():
            self._set_relationship_cache(
                instance, rel_name, related_by_fk.get(pk_value, [])
            )

    async def _async_load_eager_relationships(self, instances: List[Any]):
        from nexios.orm.model import RelationshipType

        if not instances or not self._eager_load:
            return
        relationships_to_load = defaultdict(list)

        for rel_name in self._eager_load.get("*", []):
            for instance in instances:
                relationships_to_load[rel_name].append(instance)

        for parent_rel, child_rels in self._eager_load.items():
            if parent_rel == "*":
                continue
            for instance in instances:
                pass
        if not self._session:
            raise ValueError("Session not bound to query.")

        for rel_name, rel_instances in relationships_to_load.items():
            if not rel_instances:
                continue

            firs_instance = rel_instances[0]
            model_class = type(firs_instance)

            if rel_name not in model_class.__relationships__:
                continue

            rel_info = model_class.__relationships__[rel_name]

            if rel_info.relationship_type in (RelationshipType.MANY_TO_ONE, RelationshipType.ONE_TO_ONE):
                await self._async_batch_load_many_to_one(
                    rel_instances, rel_name, rel_info, self._session
                )
            elif rel_info.relationship_type == RelationshipType.ONE_TO_MANY:
                await self._async_batch_load_one_to_many(
                    rel_instances, rel_name, rel_info, self._session
                )
            elif rel_info.relationship_type == RelationshipType.MANY_TO_MANY:
                await self._async_batch_load_many_to_many(
                    rel_instances, rel_name, rel_info, self._session
                )

    async def _async_batch_load_many_to_one(
        self, instances, rel_name, rel_info, session
    ):
        is_inverse_one_to_one = rel_info.relationship_type == RelationshipType.ONE_TO_ONE and not rel_info.foreign_key
        
        if is_inverse_one_to_one:
            await self._async_batch_load_one_to_many(instances, rel_name, rel_info, session)
            return

        if not rel_info.foreign_key:
            return

        fk_values = []
        instance_map = {}

        for instance in instances:
            fk_value = getattr(instance, rel_info.foreign_key, None)
            if fk_value is not None:
                fk_values.append(fk_value)
                instance_map[fk_value] = instance

        if not fk_values:
            return

        related_model = rel_info.related_model
        pk_field = self._get_primary_key_field(related_model)

        query = select(related_model).where(
            getattr(related_model, pk_field).in_(fk_values)
        )
        related_objects = await query._all_async()

        for obj in related_objects:
            pk_value = getattr(obj, pk_field)
            if pk_value in instance_map:
                instance = instance_map[pk_value]
                self._set_relationship_cache(instance, rel_name, obj)

    async def _async_batch_load_one_to_many(
        self, instances, rel_name, rel_info, session
    ):
        if not rel_info.foreign_key:
            return

        pk_values = []
        instance_map = {}

        for instance in instances:
            pk_name = self._get_primary_key_field(instance)
            pk_value = getattr(instance, pk_name)
            pk_values.append(pk_value)
            instance_map[pk_value] = instance

        if not pk_values:
            return

        related_model = rel_info.related_model

        query = select(related_model).where(
            getattr(related_model, rel_info.foreign_key).in_(pk_values)
        )

        all_related = await query._all_async()

        related_by_fk = defaultdict(list)
        for obj in all_related:
            fk_value = getattr(obj, rel_info.foreign_key)
            related_by_fk[fk_value].append(obj)

        for pk_value, instance in instance_map.items():
            self._set_relationship_cache(
                instance, rel_name, related_by_fk.get(pk_value, [])
            )

    async def _async_batch_load_many_to_many(
        self, instances, rel_name, rel_info, session
    ):
        through_model = rel_info.through_model
        related_model = rel_info.related_model

        if not through_model:
            return

        pk_values = []
        instance_map = {}

        for instance in instances:
            pk_name = self._get_primary_key_field(instance)
            pk_value = getattr(instance, pk_name)
            pk_values.append(pk_value)
            instance_map[pk_value] = instance

        if not pk_values:
            return

        local_col = rel_info.local_column or f"{type(instances[0]).__name__.lower()}_id"
        foreign_col = rel_info.foreign_column or f"{related_model.__name__.lower()}_id"

        query1 = select(getattr(through_model, foreign_col)).where(
            getattr(through_model, local_col).in_(pk_values)
        )
        rows = await query1._all_async()

        for row in rows:
            source_id = row[0]  # Assuming first column is local ID
            related_id = row[1] if len(row) > 1 else row[0]

        all_related_ids = set()
        id_mapping = defaultdict(list)

        for row in rows:
            if len(row) >= 2:
                source_id = row[0]
                related_id = row[1]
                all_related_ids.add(related_id)
                id_mapping[source_id].append(related_id)

        if not all_related_ids:
            return

        query2 = select(related_model).where(
            getattr(related_model, "id").in_(list(all_related_ids))
        )

        all_related = await query2._all_async()

        # Create mapping of ID -> related object
        related_by_id = {getattr(obj, "id"): obj for obj in all_related}

        # Map back to instances
        for pk_value, instance in instance_map.items():
            related_ids = id_mapping.get(pk_value, [])
            related_objects = [
                related_by_id.get(rid) for rid in related_ids if rid in related_by_id
            ]
            self._set_relationship_cache(instance, rel_name, related_objects)

    # Sync methods
    def _all(self) -> List[_T]:
        """Execute and return all results"""
        from nexios.orm.model import NexiosModel

        if self._eager_load:
            return self._execute_with_eager_loading(self._execute_sync)

        rows = self._execute_sync()
        if self._session:
            sql, params, model, map_to_model = self._build_sql(
                self._session.engine.dialect, self._session.engine.driver
            )
            model_entities = [
                e
                for e in self.entities
                if isinstance(e, type) and issubclass(e, NexiosModel)
            ]
            return self._rows_to_models(rows, model, map_to_model, model_entities)
        else:
            raise ValueError("Session not bound to query.")

    def _first(self) -> Optional[_T]:
        """Execute and return first result - OPTIMIZED"""
        from nexios.orm.model import NexiosModel

        original_limit = self._limit
        self._limit = 1

        try:
            rows = self._execute_sync()
            if not self._session:
                raise ValueError("Session not bound to query.")
            sql, params, model, map_to_model = self._build_sql(
                self._session.engine.dialect, self._session.engine.driver
            )
            model_entities = [
                e
                for e in self.entities
                if isinstance(e, type) and issubclass(e, NexiosModel)
            ]
            results = self._rows_to_models(rows, model, map_to_model, model_entities)
            return results[0] if results else None
        finally:
            self._limit = original_limit

    # Async methods
    async def _all_async(self) -> List[_T]:
        """Execute and return all results asynchronously"""
        from nexios.orm.model import NexiosModel

        rows = await self._execute_async()
        if not self._session:
            raise ValueError("Session not bound to query.")

        sql, params, model, map_to_model = self._build_sql(
            self._session.engine.dialect, self._session.engine.driver
        )
        model_entities = [
            a
            for a in self.entities
            if isinstance(a, type) and issubclass(a, NexiosModel)
        ]
        results = self._rows_to_models(rows, model, map_to_model, model_entities)

        if self._eager_load:
            await self._async_load_eager_relationships(results)
        return results

    async def _first_async(self) -> Optional[_T]:
        """Execute and return first result asynchronously - OPTIMIZED"""
        from nexios.orm.model import NexiosModel

        original_limit = self._limit
        self._limit = 1

        try:
            rows = await self._execute_async()
            if not self._session:
                raise ValueError("Session not bound to query.")
            sql, params, model, map_to_model = self._build_sql(
                self._session.engine.dialect, self._session.engine.driver
            )
            model_entities = [
                a
                for a in self.entities
                if isinstance(a, type) and issubclass(a, NexiosModel)
            ]
            results = self._rows_to_models(rows, model, map_to_model, model_entities)
            if self._eager_load:
                await self._async_load_eager_relationships(results)
            return results[0] if results else None
        finally:
            self._limit = original_limit

    def _rows_to_models(
        self,
        rows: List[Tuple[Any, ...]],
        model: Type[NexiosModel],
        map_to_model: bool,
        model_entities: List[Any],
    ) -> List[Any]:
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
        elif len(model_entities) > 1:
            model_field_counts = []
            for model_cls in model_entities:
                model_field_counts.append(len(model_cls.get_fields()))

            for row in rows:
                model_instances = []
                start_idx = 0

                for i, model_cls in enumerate(model_entities):
                    field_count = model_field_counts[i]
                    model_slice = row[start_idx : start_idx + field_count]

                    field_names = list(model_cls.get_fields().keys())
                    data = {name: val for name, val in zip(field_names, model_slice)}

                    if hasattr(model_cls, "model_validate"):
                        inst = model_cls.model_validate(data)
                    else:
                        inst = model_cls(**data)

                    model_instances.append(inst)
                    start_idx += field_count
                results.append(tuple(model_instances))
            return results
        else:
            # Not mapping to a model: return scalar for single-column selects, else tuples
            for row in rows:
                if len(row) == 1:
                    results.append(row[0])
                else:
                    results.append(row)
            return results
    
    def _get_primary_key_field(self, model: InstanceOrType[NexiosModel]) -> Any:
        pk_field = model.get_primary_key()
        return pk_field[0] if isinstance(pk_field, (list, tuple)) else pk_field
    
    def _set_relationship_cache(self, instance: Any, rel_name: str, value: Any):
        """Set the relationship cache for an instance"""
        if "__relationship_cache__" not in instance.__dict__:
            instance.__dict__["__relationship_cache__"] = {}
        instance.__dict__["__relationship_cache__"][rel_name] = value

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
def select(*entities: ColumnExpression[Any]) -> Select[Any]: ...


@overload
def select(*entities: Union[Type[_M], ColumnExpression[Any], str]) -> Select[Any]: ...


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
