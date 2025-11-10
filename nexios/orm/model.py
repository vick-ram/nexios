from decimal import Decimal
from pydantic import BaseModel, create_model, Field as PydanticField, field_validator
from typing_extensions import (
    Any,
    Dict,
    Optional,
    Type,
    TypeVar,
    Tuple,
    Union,
    Annotated,
    List,
    get_origin,
    get_args,
    TYPE_CHECKING,
)
import json
from datetime import datetime, date
from uuid import UUID

from nexios.orm.backends.fieldinfo import FieldInfo
# from nexios.orm.connection import AsyncCursor, Cursor
from nexios.orm.backends.types import DatabaseDialect
from nexios.orm.field import Field, FieldType
from nexios.orm.relationship import Relationship

if TYPE_CHECKING:
    from nexios.orm.query import Query

# class ModelMeta(type):
#     _registry: Dict[str, Type["Model"]] = {}

#     def __new__(
#         cls, name: str, bases: Tuple[Type, ...], namespace: Dict[str, Any], **kwargs
#     ):
#         if name == "Model":
#             return super().__new__(cls, name, bases, namespace, **kwargs)

#         fields: Dict[str, Field] = {}

#         type_hints: Dict[str, Any] = namespace.get("__annotations__", {})

#         for field_name, field_type in type_hints.items():
#             if field_name.startswith("_"):
#                 continue

#             if isinstance(namespace.get(field_name), Field):
#                 continue

#             default_value = namespace.get(field_name, None)
#             field = cls._create_field_from_type_hints(field_type, default_value)

#             if field:
#                 fields[field_name] = field
#                 if field_name in namespace:
#                     del namespace[field_name]

#         for key, value in namespace.items():
#             if isinstance(value, Field):
#                 fields[key] = value

#         table_name = namespace.get("__tablename__", name.lower())

#         new_class = super().__new__(cls, name, bases, namespace)

#         setattr(new_class, "_fields", fields)
#         setattr(new_class, "_tablename", table_name)

#         cls._registry[table_name] = new_class  # type: ignore

#         relationships = {}
#         for field_name, field_type in type_hints.items():
#             if get_origin(field_type) is Relationship:
#                 relationships[field_name] = field_type

#         setattr(new_class, "_relationships", relationships)

#         return new_class
    
#     @property
#     def fields(cls) -> Dict[str, Field]:
#         return getattr(cls, "_fields", {})

#     @property
#     def tablename(cls) -> str:
#         return getattr(cls, "_tablename", cls.__name__.lower())

#     @classmethod
#     def _create_field_from_type_hints(
#         cls, field_type: Type, default: Any
#     ) -> Optional[Field]:
#         origin = get_origin(field_type)
#         metadata = {}

#         if origin is Annotated:
#             args = get_args(field_type)
#             actual_type = args[0]
#             for meta in args[1:]:
#                 if isinstance(meta, dict):
#                     metadata.update(meta)
#         else:
#             actual_type = field_type

#         is_optional = cls._is_optional_type(actual_type)

#         if is_optional:
#             actual_type = cls._extract_actual_type(actual_type)

#         nullable = is_optional or default is None

#         return cls._type_to_field(actual_type, nullable, default, metadata)

#     @staticmethod
#     def _is_optional_type(field_type: Type) -> bool:
#         origin = get_origin(field_type)
#         if origin is Union:
#             args = get_args(field_type)
#             return type(None) in args
#         return False

#     @staticmethod
#     def _extract_actual_type(field_type: Type):
#         origin = get_origin(field_type)

#         if origin is Union:
#             args = [arg for arg in get_args(field_type) if arg is not type(None)]
#             return args[0] if args else field_type
#         elif origin is Annotated:
#             return get_args(field_type)[0]
#         else:
#             return field_type

#     @staticmethod
#     def _type_to_field(
#         python_type: Type, nullable: bool, default: Any, metadata: Dict[str, Any]
#     ) -> Field:
#         type_mapping = {
#             int: FieldType.INTEGER,
#             str: FieldType.VARCHAR,
#             bool: FieldType.BOOLEAN,
#             float: FieldType.FLOAT,
#             datetime: FieldType.DATETIME,
#             Decimal: FieldType.DECIMAL,
#             bytes: FieldType.BINARY,
#             UUID: FieldType.VARCHAR,
#             dict: FieldType.JSON,
#             list: FieldType.JSON,
#         }

#         field_type = type_mapping.get(python_type, FieldType.TEXT)

#         # Handle special types
#         if python_type in (dict, list):
#             metadata.setdefault("serializer", json.dumps)
#             metadata.setdefault("deserializer", json.loads)

#         # Apply metadata to field parameters
#         field_kwargs = {
#             "field_type": field_type,
#             "python_type": python_type,
#             "nullable": nullable,
#             "default": default,
#         }
#         field_kwargs.update(metadata)

#         return Field(**field_kwargs)


# class Model(metaclass=ModelMeta):
#     _fields: Dict[str, Field]
#     _tablename: str

#     def __init__(self, **kwargs) -> None:
#         for field_name, field in self._fields.items():
#             value = kwargs.get(field_name)

#             # Handle auto-generated values
#             if value is None and field.auto_now_add:
#                 value = datetime.now()

#             # Handle default values
#             if value is None and field.default is not None:
#                 value = field.get_default_value()

#             try:
#                 setattr(self, field_name, value)
#             except (ValueError, TypeError) as e:
#                 raise ValueError(
#                     f"Invalid value for field '{field_name}': {value}. Error: {e}"
#                 ) from e

#         # Set auto_now field after initialization
#         for field_name, field in self._fields.items():
#             if field.auto_now and field.auto_now_add:
#                 setattr(self, field_name, datetime.now())

#     def __repr__(self) -> str:
#         fields_repr = []
#         for field_name in self._fields:
#             value = getattr(self, field_name, None)
#             fields_repr.append(f"{field_name}={repr(value)}")
#         return f"<{self.__class__.__name__} " + ", ".join(fields_repr) + ">"

#     @classmethod
#     def query(cls) -> "Query[Model]":
#         return Query(cls)

#     @classmethod
#     async def create_table(cls, cursor: Cursor) -> None:

#         def _table_name() -> str:
#             if cls._tablename.strip() == "":
#                 return (
#                     cls.__class__.__name__.lower()
#                     if cls.__class__.__name__.endswith("s")
#                     else f"{cls.__class__.__name__}s"
#                 )
#             else:
#                 return cls._tablename

#         columns: List[str] = []
#         for field_name, field in cls._fields.items():
#             column_def = f"{field_name} {field.get_sql_definition()}"
#             columns.append(column_def)

#         tbname = _table_name()

#         sql = f"CREATE TABLE IF NOT EXISTS {tbname} ({', '.join(columns)})"

#         if isinstance(cursor, AsyncCursor):
#             await cursor.execute(sql)
#         else:
#             cursor.execute(sql)

#     async def save(self, cursor: Cursor) -> None:
#         """Save the model instance (insert or update)"""
#         fields_to_save = {}
#         primary_key_field = None
#         for field_name, field in self._fields.items():
#             value = getattr(self, field_name, None)
#             if value is not None:
#                 fields_to_save[field_name] = value
#             if field.primary_key:
#                 primary_key_field = field_name

#         if primary_key_field and getattr(self, primary_key_field, None):
#             # update existing record
#             await self._update(cursor, fields_to_save, primary_key_field)
#         else:
#             # Insert new record
#             await self._insert(cursor, fields_to_save)
    
#     async def update(self, cursor: Cursor, fields: Dict[str, Any]) -> None:
#         fields_to_update = {}
#         primary_key_field = None
#         for field_name, field in self._fields.items():
#             value = getattr(self, field_name, None)
#             if value is not None:
#                 fields_to_update [field_name] = value
#             if field.primary_key:
#                 primary_key_field = field_name
#         if primary_key_field and getattr(self, primary_key_field, None):
#             await self._update(cursor, fields_to_update, primary_key_field)

#     async def delete(self, cursor: Cursor) -> None:
#         """Delete the model instance"""
#         primary_key_field = None
#         primary_key_value = None

#         for field_name, field in self._fields.items():
#             if field.primary_key:
#                 primary_key_field = field_name
#                 primary_key_value = getattr(self, field_name, None)
#                 break

#         if not primary_key_field or primary_key_value is None:
#             raise ValueError("Cannot delete model without primary key field")

#         sql = f"DELETE FROM {self._tablename} WHERE {primary_key_field} = ?"

#         if isinstance(cursor, AsyncCursor):
#             await cursor.execute(sql, (primary_key_value,))
#         else:
#             cursor.execute(sql, (primary_key_value))

#     @classmethod
#     async def get(cls, cursor: Cursor, **filters) -> Optional["Model"]:
#         """ "Get a single model instance by filters"""
#         query = cls.query().filter(**filters)
#         if isinstance(cursor, AsyncCursor):
#             results = await query.first(cursor)
#         else:
#             results = query.first(cursor)
#         return results

#     @classmethod
#     async def all(cls, cursor: Cursor) -> List["Model"]:
#         """Get all model instances"""
#         results = []
#         query = cls.query()
#         if isinstance(cursor, AsyncCursor):
#             results.append(await query.all(cursor))
#         else:
#             results.append(query.all(cursor))

#         return results

#     def to_dict(self) -> Dict[str, Any]:
#         """Convert model instance to dictionary"""
#         result = {}
#         for field_name in self._fields.keys():
#             result[field_name] = getattr(self, field_name, None)
#         return result

#     @classmethod
#     def get_table_schema(cls) -> Dict[str, Field]:
#         return cls._fields

#     @classmethod
#     def get_tablename(cls) -> str:
#         return cls._tablename

#     async def _insert(self, cursor: Cursor, fields: Dict[str, Any]) -> None:
#         field_names = list(fields.keys())
#         placeholders = ", ".join(["?"] * len(field_names))
#         field_names_str = ", ".join(field_names)

#         sql = (
#             f"INSERT INTO {self._tablename} ({field_names_str}) VALUES ({placeholders})"
#         )
#         params = tuple(fields.values())

#         if isinstance(cursor, AsyncCursor):
#             await cursor.execute(sql, params)
#             # Attempt to fetch generated primary key if any
#             await self._fetch_generated_primary_key(cursor)
#         else:
#             cursor.execute(sql, params)
#             await self._fetch_generated_primary_key(cursor)

#     async def _update(
#         self, cursor: Cursor, fields: Dict[str, Any], primary_key_field: str
#     ) -> None:
#         set_clauses = []
#         params = []

#         for field_name, value in fields.items():
#             if field_name != primary_key_field:
#                 set_clauses.append(f"{field_name} = ?")
#                 params.append(value)

#         params.append(getattr(self, primary_key_field))
#         set_clause_str = ", ".join(set_clauses)

#         sql = f"UPDATE {self._tablename} SET {set_clause_str} WHERE {primary_key_field} = ?"

#         if isinstance(cursor, AsyncCursor):
#             await cursor.execute(sql, tuple(params))
#         else:
#             cursor.execute(sql, tuple(params))

#     async def _fetch_generated_primary_key(self, cursor: Cursor) -> None:
#         """Try to fetch an auto-generated primary key after insert, if supported"""
#         pk_field = None
#         for name, field in self._fields.items():
#             if field.primary_key:
#                 pk_field = name
#                 break

#         if not pk_field:
#             return

#         if hasattr(cursor, "lastrowid"):
#             pk_value = getattr(cursor, "lastrowid", None)
#             if pk_value is not None:
#                 setattr(self, pk_field, pk_value)
#                 return

#         if isinstance(cursor, AsyncCursor):
#             try:
#                 result = await cursor.fetchone()
#                 if result:
#                     setattr(self, pk_field, result[0])
#             except Exception:
#                 pass


class ModelMeta(type):
    _registry: Dict[str, Type["Model"]] = {}

    def __new__(
        cls, name: str, bases: Tuple[Type, ...], namespace: Dict[str, Any], **kwargs
    ):
        if name == "Model":
            return super().__new__(cls, name, bases, namespace, **kwargs)

        # Collect fields and their types
        fields: Dict[str, FieldInfo] = {}
        type_hints = namespace.get("__annotations__", {})
        
        # Process each field
        for field_name, field_type in type_hints.items():
            if field_name.startswith("_"):
                continue
                
            field_value = namespace.get(field_name)
            
            # Handle FieldInfo instances
            if isinstance(field_value, FieldInfo):
                field_info = field_value
                # Set python_type from type hint if not already set
                if field_info.python_type is None:
                    field_info.python_type = cls._extract_actual_type(field_type)
                fields[field_name] = field_info
                
            # Handle Relationship
            elif get_origin(field_type) is Relationship:
                # Relationships are handled separately
                continue
                
            # Create FieldInfo from type hints
            else:
                field_info = cls._create_field_from_type_hints(field_type, field_value)
                if field_info:
                    fields[field_name] = field_info

        # Remove field values from namespace to avoid conflicts
        for field_name in fields:
            if field_name in namespace:
                del namespace[field_name]

        # Create the actual class
        new_class = super().__new__(cls, name, bases, namespace)
        
        # Set metadata
        setattr(new_class, "_fields", fields)
        setattr(new_class, "_tablename", namespace.get("__tablename__", name.lower()))
        
        # Create Pydantic model with proper validation
        pydantic_fields = {}
        for field_name, field_info in fields.items():
            field_type = field_info.python_type or str
            
            # Apply constraints based on field_info metadata
            final_field = PydanticField(
                # default=field_info.default,
                # default_factory=field_info.default_factory,
                alias=field_info.alias,
                title=field_info.title,
                description=field_info.description,
                # Pass validation constraints that Pydantic understands
                **{k: v for k, v in {
                    'min_length': getattr(field_info, 'min_length', None),
                    'max_length': getattr(field_info, 'max_length', None),
                    'regex': getattr(field_info, 'regex', None),
                    'gt': getattr(field_info, 'gt', None),
                    'ge': getattr(field_info, 'ge', None),
                    'lt': getattr(field_info, 'lt', None),
                    'le': getattr(field_info, 'le', None),
                    'multiple_of': getattr(field_info, 'multiple_of', None),
                    'min_items': getattr(field_info, 'min_items', None),
                    'max_items': getattr(field_info, 'max_items', None),
                }.items() if v is not None}
            )
            
            pydantic_fields[field_name] = (field_type, final_field)

        # Create Pydantic model as __pydantic_model__
        pydantic_model = create_model(
            f"{name}Model",
            __base__=BaseModel,
            **pydantic_fields
        )
        setattr(new_class, "__pydantic_model__", pydantic_model)
        tbname = getattr(cls, '_tablename', None)
        
        cls._registry[tbname] = new_class # type: ignore
        
        return new_class

    @classmethod
    def _create_field_from_type_hints(
        cls, field_type: Type, default: Any
    ) -> Optional[FieldInfo]:
        """Create FieldInfo from type hints"""
        origin = get_origin(field_type)
        metadata = {}
        python_type = field_type
        
        # Handle Annotated types
        if origin is Annotated:
            args = get_args(field_type)
            python_type = args[0]
            for meta in args[1:]:
                if isinstance(meta, FieldInfo):
                    return meta
                elif isinstance(meta, dict):
                    metadata.update(meta)
        
        # Handle Optional types
        is_optional = cls._is_optional_type(python_type)
        if is_optional:
            python_type = cls._extract_actual_type(python_type)
        
        # Map Python types to FieldType
        field_type_enum = cls._python_type_to_field_type(python_type)
        
        # Create FieldInfo
        field_info = FieldInfo(
            default=default if default is not None else ...,
            field_type=field_type_enum,
            python_type=python_type,
            nullable=is_optional or default is None,
            **metadata
        )
        
        return field_info

    @staticmethod
    def _is_optional_type(field_type: Type) -> bool:
        origin = get_origin(field_type)
        if origin is Union:
            return type(None) in get_args(field_type)
        return False

    @staticmethod
    def _extract_actual_type(field_type: Type) -> Type:
        origin = get_origin(field_type)
        if origin is Union:
            args = [arg for arg in get_args(field_type) if arg is not type(None)]
            return args[0] if args else field_type
        elif origin is Annotated:
            return get_args(field_type)[0]
        return field_type

    @staticmethod
    def _python_type_to_field_type(python_type: Type) -> FieldType:
        type_mapping = {
            int: FieldType.INTEGER,
            str: FieldType.VARCHAR,
            bool: FieldType.BOOLEAN,
            float: FieldType.FLOAT,
            datetime: FieldType.DATETIME,
            date: FieldType.DATE,
            Decimal: FieldType.DECIMAL,
            bytes: FieldType.BINARY,
            UUID: FieldType.UUID,
            dict: FieldType.JSON,
            list: FieldType.JSON,
        }
        return type_mapping.get(python_type, FieldType.VARCHAR)

class Model(metaclass=ModelMeta):
    _fields: Dict[str, FieldInfo]
    _tablename: str
    __pydantic_model__: Type[BaseModel]

    def __init__(self, **kwargs) -> None:
        # Validate and set fields using Pydantic
        pydantic_instance = self.__pydantic_model__(**kwargs)
        
        for field_name in self._fields:
            value = getattr(pydantic_instance, field_name)
            
            # Handle auto-generated values
            field_info = self._fields[field_name]
            if value is None:
                if field_info.auto_now_add:
                    value = datetime.now()
                elif field_info.default is not ...:
                    value = field_info.get_default_value()
            
            # Additional validation
            if value is not None:
                value = field_info.validate_value(value)
                
            setattr(self, field_name, value)
        
        # Set auto_now fields
        for field_name, field_info in self._fields.items():
            if field_info.auto_now:
                setattr(self, field_name, datetime.now())

    @classmethod
    def get_table_name(cls) -> str:
        return cls._tablename

    @classmethod
    def get_fields(cls) -> Dict[str, FieldInfo]:
        return cls._fields

    def dict(self) -> Dict[str, Any]:
        """Convert model to dictionary"""
        result = {}
        for field_name in self._fields:
            value = getattr(self, field_name, None)
            result[field_name] = value
        return result

    def validate(self) -> bool:
        """Validate all fields"""
        try:
            self.__pydantic_model__(**self.dict())
            return True
        except Exception:
            return False
    
    @classmethod
    def create_table(cls) -> str:

        def _table_name() -> str:
            if cls._tablename.strip() == "":
                return (
                    cls.__class__.__name__.lower()
                    if cls.__class__.__name__.endswith("s")
                    else f"{cls.__class__.__name__}s"
                )
            else:
                return cls._tablename
        
        columns: List[str] = []
        for field_name, field in cls._fields.items():
            column_def = f"{field_name} {field.get_sql_definition()}"
            columns.append(column_def)
        
        tbname = _table_name()

        sql = f"CREATE TABLE IF NOT EXISTS {tbname} ({', '.join(columns)})"

        return sql

    def save(self, dialect: DatabaseDialect) -> Tuple[str, tuple]:
        fields_to_save: Dict[str, Any] = {}

        for field_name, field in self._fields.items():
            value = getattr(self, field_name, None)
            if value is not None:
                fields_to_save[field_name] = value

        field_names = list(fields_to_save.keys())
        placeholder = "%s" if dialect == "postgres" else "?"
        placeholders = ", ".join([placeholder] * len(field_names))
        field_names_str = ", ".join(field_names)

        sql = (
            f"INSERT INTO {self._tablename} ({field_names_str}) VALUES ({placeholders})"
        )
        params = tuple(getattr(self, fname) for fname in field_names)

        return sql, params
    
    def update(self, dialect: str) -> Tuple[str, tuple]:
        set_clauses = []
        params = []

        fields_to_save: Dict[str, Any] = {}
        primary_key_field = None

        for field_name, field in self._fields.items():
            value = getattr(self, field_name, None)
            if value is not None:
                fields_to_save[field_name] = value
            if field.primary_key:
                primary_key_field = field_name
                
        
        if primary_key_field and getattr(self, primary_key_field, None):
            pass


