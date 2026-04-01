from __future__ import annotations

import types

from typing import Type, Optional, Any, List, overload, cast, TYPE_CHECKING
from pydantic_core import PydanticUndefined as Undefined

from nexios.orm.relationships import RelationshipInfo, RelationshipType
from nexios.orm.misc.context import get_context_data

if TYPE_CHECKING:
    from nexios.orm.model import NexiosModel
    from nexios.orm import Select
    from nexios.orm.utils import (
        to_snake_case,
        get_tablename_for_class,
        InstanceOrType,
    )


_NOT_LOADED = object()


class ColumnDescriptor:
    """Descriptor that returns ColumnExpression when accessed from class"""

    def __init__(self, field_name: str, model_class: Type[NexiosModel]) -> None:
        self.field_name = field_name
        self.model_class = model_class

    def __get__(self, instance, owner):
        from nexios.orm.query.expressions import ColumnExpression

        if instance is None:
            return ColumnExpression(self.model_class, self.field_name)
        return instance.__dict__.get(self.field_name, None)

    def __set__(self, instance, value):
        instance.__dict__[self.field_name] = value

    def __delete__(self, instance):
        if self.field_name in instance.__dict__:
            del instance.__dict__[self.field_name]


class RelationshipDescriptor:
    def __init__(
        self,
        model_class: Type[NexiosModel],
        field_name: str,
        relationship_info: Optional[RelationshipInfo] = None,
    ) -> types.NoneType:
        self.model_class = model_class
        self.field_name = field_name

        if relationship_info is not None:
            self._relationship_info = relationship_info
        else:
            self._relationship_info = model_class.__relationships__[field_name]

    def __get__(self, obj: Optional[NexiosModel], objType: Type[NexiosModel]):
        if obj is None:
            return self

        cached = self._get_cache(obj)
        if cached is not _NOT_LOADED:
            return cached

        session = get_context_data("session")
        if not session:
            raise RuntimeError(
                f"No session available for loading relationship '{self.field_name}'. "
                f"Make sure you're inside a session context manager."
            )

        if self._relationship_info.lazy == "select":
            return self._load_select_lazy(obj, session)
        elif self._relationship_info.lazy == "joined":
            return self._load_select_lazy(obj, session)
        elif self._relationship_info.lazy == "dynamic":
            return self._load_dynamic(obj, session)
        elif self._relationship_info.lazy == "subquery":
            return self._load_subquery(obj, session)
        else:
            return self._load_select_lazy(obj, session)

    def __set__(self, obj: NexiosModel, value: Any):
        """Set relationship value and update foreign key if applicable."""
        # clear cache
        self._clear_cache(obj)
        self._set_cache(obj, value)

        # If setting to None, clear foreign key and return
        if value is None:
            if self._relationship_info.foreign_key:
                fk_field = (
                    self._relationship_info.foreign_key
                    or self._find_local_foreign_key()
                )
                if fk_field and hasattr(obj, fk_field):
                    setattr(obj, fk_field, None)
            return

        local_fk = self._relationship_info.foreign_key or self._find_local_foreign_key()
        if local_fk:
            pk_val = getattr(value, self._get_pk_field(value), None)
            setattr(obj, local_fk, pk_val)

        if self._relationship_info.back_populates:
            back_field = self._relationship_info.back_populates

            if hasattr(value.__class__, back_field):
                back_desc = getattr(value.__class__, back_field, None)

                if isinstance(back_desc, RelationshipDescriptor):
                    back_desc._set_cache(value, obj)
                    remote_fk = (
                        back_desc._relationship_info.foreign_key
                        or back_desc._find_local_foreign_key()
                    )
                    if remote_fk:
                        obj_pk_name = self._get_pk_field(obj)
                        obj_pk_value = getattr(obj, obj_pk_name, None)
                        setattr(value, remote_fk, obj_pk_value)
                else:
                    setattr(value, back_field, obj)

    def _find_local_foreign_key(self) -> Optional[str]:
        related_model = self._relationship_info.related_model
        if not related_model:
            return None

        return self._find_foreign_key_on_related(related_model, self.model_class)

    def _set_cache(self, obj: NexiosModel, value: Any) -> None:
        if "__relationship_cache__" not in obj.__dict__:
            obj.__dict__["__relationship_cache__"] = {} #type: ignore
        obj.__dict__["__relationship_cache__"][self.field_name] = value

    def _get_cache(self, obj: NexiosModel) -> Any:
        """Get cached relationship value if exists."""
        relationship_cache = obj.__dict__.get("__relationship_cache__", {})
        return relationship_cache.get(self.field_name, _NOT_LOADED)

    def _clear_cache(self, obj: NexiosModel) -> None:
        """Clear existing cache"""
        if "__relationship_cache__" in obj.__dict__:
            if self.field_name in obj.__dict__["__relationship_cache__"]:
                del obj.__dict__["__relationship_cache__"][self.field_name]

    def _get_pk_field(self, model: InstanceOrType[NexiosModel]) -> Any:
        """Helper to safely get primary key."""
        pk = model.get_primary_key()
        return pk[0] if isinstance(pk, (list, tuple)) else pk

    def _find_foreign_key_on_related(
        self, related_model: Type[NexiosModel], current_model_class: Type[NexiosModel]
    ) -> str:
        """Find foreign key on related model that points to current model"""
        from nexios.orm.utils import to_snake_case, get_model_fields, get_tablename_for_class


        # For one-to-one, the foreign key could be on either side
        # Check if current model has a field that points to related model first
        current_fields = get_model_fields(current_model_class)
        expected_name = f"{to_snake_case(related_model.__name__)}_id"

        # Check if foreign key exists on current model pointing to related
        for field_name, field_info in current_fields.items():
            fk = getattr(field_info, "foreign_key", Undefined)
            if fk is not Undefined and fk:
                if isinstance(fk, str):
                    fk_s = fk.strip()
                    if "." in fk_s:
                        left, _ = fk_s.rsplit(".", 1)
                        left_l = left.lower()
                        tablename = (
                            get_tablename_for_class(related_model) or ""
                        ).lower()
                        candidates = {
                            related_model.__name__.lower(),
                            to_snake_case(related_model.__name__),
                            tablename,
                        }
                        if left_l in candidates:
                            return field_name
                    else:
                        if fk_s == expected_name or fk_s == field_name:
                            return field_name

        # If not found, check the related model (original logic)
        expected_name_on_related = f"{to_snake_case(current_model_class.__name__)}_id"
        pk_name = self._get_pk_field(current_model_class)
        related_fields = get_model_fields(related_model)

        # Check explicit foreign key metadata first
        for field_name, field_info in related_fields.items():
            fk = getattr(field_info, "foreign_key", Undefined)
            if fk is not Undefined and fk:
                if isinstance(fk, str):
                    fk_s = fk.strip()
                    if "." in fk_s:
                        left, _ = fk_s.rsplit(".", 1)
                        left_l = left.lower()
                        tablename = (
                            get_tablename_for_class(current_model_class) or ""
                        ).lower()
                        candidates = {
                            current_model_class.__name__.lower(),
                            to_snake_case(current_model_class.__name__),
                            tablename,
                        }
                        if left_l in candidates:
                            return field_name
                    else:
                        if (
                            fk_s == expected_name_on_related
                            or fk_s == str(pk_name)
                            or fk_s == field_name
                        ):
                            return field_name

        # fallback: find by naming convention on the related model's field names
        for field_name in related_fields.keys():
            if field_name == expected_name_on_related:
                return field_name
            if pk_name and field_name.endswith(f"_{pk_name}"):
                return field_name

        # last resort: if attribute exists on the related model, return it
        if hasattr(related_model, expected_name_on_related):
            return expected_name_on_related

        return expected_name_on_related

    def _load_select_lazy(self, obj: NexiosModel, session: Any) -> Any:
        rel_type = self._relationship_info.relationship_type

        if rel_type == RelationshipType.MANY_TO_ONE:
            return self._load_many_to_one(obj, session)
        elif rel_type == RelationshipType.ONE_TO_MANY:
            return self._load_one_to_many(obj, session)
        elif rel_type == RelationshipType.MANY_TO_MANY:
            return self._load_many_to_many(obj, session)
        else:  # ONE_TO_ONE
            return self._load_one_to_one(obj, session)

    def _load_subquery(self, obj: NexiosModel, session: Any) -> Any:
        """Load using subquery loading strategy."""
        return self._load_select_lazy(obj, session)

    def _load_many_to_one(self, obj: NexiosModel, session: Any) -> Any:
        from nexios.orm.misc.event_loop import NexiosEventLoop
        from nexios.orm.query.builder import select
        from nexios.orm.sessions import AsyncSession

        cached = self._get_cache(obj)
        if cached is not _NOT_LOADED:
            return cached

        loop = NexiosEventLoop()
        result: Optional[NexiosModel] = None

        related_model = self._relationship_info.related_model

        fk_field_name = self._relationship_info.foreign_key
        if not fk_field_name:
            raise ValueError(
                f"No foreign key defined for relationship {self._relationship_info.field_name}"
            )

        fk_value = getattr(obj, fk_field_name, None)
        if fk_value is None:
            result = None

        assert related_model is not None

        related_pk_field = self._get_pk_field(related_model)

        query = select(related_model).where(
            getattr(related_model, related_pk_field) == fk_value
        )

        query._bind(session)

        if isinstance(session, AsyncSession):

            async def async_fetch():
                return await query._first_async()

            result = loop.run(async_fetch())
        else:
            result = query._first()

        # Cache the result
        self._set_cache(obj, result)

        return result

    def _load_one_to_many(self, obj: NexiosModel, session: Any) -> Any:
        from nexios.orm.misc.event_loop import NexiosEventLoop
        from nexios.orm.query.builder import select
        from nexios.orm.sessions import AsyncSession

        cached = self._get_cache(obj)
        if cached is not _NOT_LOADED:
            return cached

        loop = NexiosEventLoop()
        results: List[NexiosModel] = []
        related_model = self._relationship_info.related_model

        pk_name = self._get_pk_field(obj)
        pk_value = getattr(obj, pk_name, None)

        if related_model is None:
            raise ValueError("Related model is None")

        fk_field_name = self._find_foreign_key_on_related(related_model, obj.__class__)

        query = select(related_model).where(
            getattr(related_model, fk_field_name) == pk_value
        )

        # Bind and execute
        query._bind(session)

        if isinstance(session, AsyncSession):

            async def async_fetch():
                return await query._all_async()  # type: ignore

            results = loop.run(async_fetch())
        else:
            results = query._all()

        # Cache the results
        self._set_cache(obj, results)

        return results

    def _load_one_to_one(self, obj: NexiosModel, session: Any) -> Any:
        # return self._load_many_to_one(obj, session)
        from nexios.orm.misc.event_loop import NexiosEventLoop
        from nexios.orm.query.builder import select
        from nexios.orm.sessions import AsyncSession

        cached = self._get_cache(obj)
        print(f"Cached data: {cached}")
        if cached is not _NOT_LOADED:
            return cached

        loop = NexiosEventLoop()
        result: Optional[NexiosModel] = None
        related_model = self._relationship_info.related_model

        assert related_model is not None

        # Check if this is the side with the foreign key
        if self._relationship_info.foreign_key:
            # This side has the foreign key (like many-to-one)
            fk_field_name = self._relationship_info.foreign_key
            fk_value = getattr(obj, fk_field_name, None)

            if fk_value is None:
                result = None

            related_pk = self._get_pk_field(related_model)

            query = select(related_model).where(
                getattr(related_model, related_pk) == fk_value
            )
        else:
            # This side doesn't have foreign key, related side does
            pk_field_name = self._get_pk_field(obj)
            pk_value = getattr(obj, pk_field_name, None)

            if pk_value is None:
                result = None

            # Find the foreign key field on related model
            fk_field_name = self._find_foreign_key_on_related(
                related_model, obj.__class__
            )

            query = select(related_model).where(
                getattr(related_model, fk_field_name) == pk_value
            )

        query._bind(session)

        if isinstance(session, AsyncSession):

            async def async_fetch():
                return await query._first_async()

            result = loop.run(async_fetch())
        else:
            result = query._first()

        # Cache the result
        self._set_cache(obj, result)

        return result

    def _load_many_to_many(self, obj: NexiosModel, session: Any) -> List[Any]:
        from nexios.orm.misc.event_loop import NexiosEventLoop
        from nexios.orm.query.builder import select
        from nexios.orm.sessions import AsyncSession

        cached = self._get_cache(obj)
        if cached is not _NOT_LOADED:
            return cached

        loop = NexiosEventLoop()
        results: List[NexiosModel] = []
        related_model = self._relationship_info.related_model
        through_model = self._relationship_info.through_model

        association_table = self._relationship_info.association_table

        if not association_table:
            raise ValueError(
                f"No association table defined for many-to-many relationship {self._relationship_info.field_name}"
            )

        if not through_model:
            raise ValueError(
                f"No through model specified for many-to-many relationship '{self.field_name}'"
            )

        pk_name = self._get_pk_field(obj)
        pk_value = getattr(obj, pk_name, None)

        assert related_model is not None

        related_pk = self._get_pk_field(related_model)

        assert related_model is not None

        local_col = (
            self._relationship_info.local_column
            or f"{to_snake_case(obj.__class__.__name__)}_id"
        )
        foreign_col = (
            self._relationship_info.foreign_column
            or f"{to_snake_case(related_model.__name__)}_id"
        )

        query_ids = select(getattr(through_model, foreign_col)).where(
            getattr(through_model, local_col) == pk_value
        )

        query_ids._bind(session)

        def _fetch_m2m():
            from nexios.orm.sessions import AsyncSession

            if isinstance(session, AsyncSession):
                # This needs to be run inside the loop
                async def _async_logic():
                    rows = await query_ids._all_async()
                    ids = [
                        row[0] if isinstance(row, (list, tuple)) else row
                        for row in rows
                    ]
                    if not ids:
                        return []
                    q = select(related_model).where(
                        getattr(related_model, related_pk).in_(ids)
                    )
                    q._bind(session)
                    return await q._all_async()

                return loop.run(_async_logic())
            else:
                rows = query_ids._all()
                ids = [
                    row[0] if isinstance(row, (list, tuple)) else row for row in rows
                ]
                if not ids:
                    return []
                q = select(related_model).where(
                    getattr(related_model, related_pk).in_(ids)
                )
                q._bind(session)
                return q._all()

        results = _fetch_m2m()
        self._set_cache(obj, results)
        return results

    def _load_dynamic(self, obj: NexiosModel, session: Any) -> Select:
        from nexios.orm.query.builder import select, Select
        from nexios.orm.sessions import AsyncSession

        from nexios.orm.misc.event_loop import NexiosEventLoop

        _loop = NexiosEventLoop()

        pk_name = self._get_pk_field(obj)
        pk_value = getattr(obj, pk_name, None)

        related_model = self._relationship_info.related_model

        if self._relationship_info.relationship_type == RelationshipType.ONE_TO_MANY:
            assert related_model is not None
            fk_field_name = self._find_foreign_key_on_related(
                related_model, obj.__class__
            )

            query = select(related_model).where(
                getattr(related_model, fk_field_name) == pk_value
            )

            query._bind(session)
            return query
        elif self._relationship_info.relationship_type == RelationshipType.MANY_TO_MANY:
            through_model = self._relationship_info.through_model
            if not through_model:
                raise ValueError("No through model for many-to-many dynamic loading")

            class DynamicManyToManyQuery:
                def __init__(
                    self, obj, rel_info, session, pk_name, loop
                ) -> types.NoneType:
                    self.obj = obj
                    self.rel_info = rel_info
                    self.session = session
                    self.pk_name = pk_name
                    self._query = None
                    self.loop = loop

                def where(self, *conditions):
                    if not self._query:
                        self._build_query()
                    self._query = self._query.where(*conditions)  # type: ignore
                    return self

                def _build_query(self):
                    related_model = self.rel_info.related_model
                    through_model = self.rel_info.through_model

                    local_col = (
                        self.rel_info.local_column
                        or f"{self.obj.__class__.__name__.lower()}_id"
                    )
                    foreign_col = (
                        self.rel_info.foreign_column
                        or f"{related_model.__name__.lower()}_id"
                    )

                    from nexios.orm.query.builder import select

                    self._query = (
                        select(related_model)
                        .join(
                            through_model,
                            getattr(through_model, foreign_col)
                            == getattr(related_model, self.pk_name),
                        )
                        .where(
                            getattr(through_model, local_col)
                            == getattr(self.obj, self.pk_name)
                        )
                    )
                    self._query._bind(self.session)
                    return self

                @overload
                def all(self): ...

                @overload
                async def all(self): ...

                def all(self):
                    if not self._query:
                        self._build_query()
                    if isinstance(self.session, AsyncSession):

                        async def all_async():
                            return await self._query._all_async()  # type: ignore

                        return self.loop.run(all_async())
                    else:
                        return self._query._all()  # type: ignore

            return cast(
                Select,
                DynamicManyToManyQuery(
                    obj, self._relationship_info, session, pk_name, _loop
                ),
            )
        elif self._relationship_info.relationship_type == RelationshipType.MANY_TO_ONE:
            fk_field = self._relationship_info.foreign_key
            if not fk_field:
                raise ValueError(
                    f"No foreign key specified for many to one relationship {fk_field}"
                )
            fk_value = getattr(obj, fk_field, None)

            class DynamicManyToOneQuery:
                def __init__(
                    self, obj, rel_info, session, fk_field, fk_value
                ) -> types.NoneType:
                    self.obj = obj
                    self.rel_info = rel_info
                    self.session = session
                    self.fk_field = fk_field
                    self.fk_value = fk_value
                    self._query = None

                def where(self, *conditions):
                    if not self._query:
                        self._build_query()
                    self._query = self._query.where(*conditions)  # type: ignore
                    return self

                def _build_query(self):
                    related_model = self.rel_info.related_model
                    from nexios.orm.query.builder import select

                    if self.fk_value is None:
                        # Return a query that will always yield empty results
                        self._query = select(related_model).where(False)
                    else:
                        pk_field = related_model.get_primary_key()
                        if isinstance(pk_field, (list, tuple)):
                            pk_field = pk_field[0]
                        self._query = select(related_model).where(
                            getattr(related_model, pk_field) == self.fk_value
                        )
                    return self

                def first(self):
                    if not self._query:
                        self._build_query()
                    return self._query._first()  # type: ignore

                async def first_async(self):
                    if not self._query:
                        self._build_query()
                    return await self._query._first_async()  # type: ignore

                def all(self):
                    if not self._query:
                        self._build_query()
                    result = self._query._first()  # type: ignore
                    return [result] if result is not None else []

                async def all_async(self):
                    if not self._query:
                        self._build_query()
                    # For MANY_TO_ONE, _all_async() should return a list with 0 or 1 item
                    result = await self._query._first_async()  # type: ignore
                    return [result] if result is not None else []

            return cast(
                Select,
                DynamicManyToOneQuery(
                    obj, self._relationship_info, session, fk_field, fk_value
                ),
            )
        else:
            raise ValueError(
                f"Unsupported relationship type: {self._relationship_info.relationship_type}"
            )
