from decimal import Decimal
import sys
from pydantic import (
    BaseModel,
    PrivateAttr,
    create_model,
    Field as PydanticField,
    field_validator,
)
from typing_extensions import (
    Any,
    Dict,
    Optional,
    Type,
    Tuple,
    Union,
    Annotated,
    List,
    get_origin,
    get_args,
    get_type_hints,
    ForwardRef
)
from datetime import datetime, date
from uuid import UUID

from nexios.orm.backends.config import DatabaseDialect
from nexios.orm.backends.fieldinfo import FieldInfo
from nexios.orm.backends.sessions import Session, AsyncSession
from nexios.orm.field import FieldType, ForeignConstraint
from nexios.orm.query import ColumnExpression, select
from nexios.orm.relationship import RelationshipInfo


class ModelMeta(type):
    _registry: Dict[str, Type["Model"]] = {}

    def __new__(
        cls, name: str, bases: Tuple[Type, ...], namespace: Dict[str, Any], **kwargs
    ):
        if name == "Model":
            return super().__new__(cls, name, bases, namespace, **kwargs)

        # Collect fields, relationships, and foreign keys
        fields: Dict[str, FieldInfo] = {}
        relationships: Dict[str, RelationshipInfo] = {}
        foreign_keys: Dict[str, str] = {}

        # type_hints = namespace.get("__annotations__", {})
        type_hints = get_type_hints(
            namespace, globalns=namespace.get("__globals__", {})
        )

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

                # Check if this is a foreign key field
                if field_info.foreign_key:
                    related_model = cls._extract_related_model_from_fk(
                        field_info.foreign_key
                    )
                    if related_model:
                        foreign_keys[field_name] = related_model

                fields[field_name] = field_info

            # Handle Relationship
            elif isinstance(field_value, RelationshipInfo):
                relationships[field_name] = field_value
                continue

            # Create FieldInfo from type hints
            else:
                field_info = cls._create_field_from_type_hints(field_type, field_value)
                if field_info:
                    fields[field_name] = field_info

        # Remove field values from namespace to avoid conflicts
        for field_name in list(fields.keys()) + list(relationships.keys()):
            if field_name in namespace:
                del namespace[field_name]

        # Create the actual class
        new_class = super().__new__(cls, name, bases, namespace)

        # Set metadata
        setattr(new_class, "_fields", fields)
        setattr(new_class, "_relationships", relationships)
        setattr(new_class, "_foreign_keys", foreign_keys)
        setattr(new_class, "_tablename", namespace.get("__tablename__", name.lower()))

        # Create Pydantic model with proper validation
        pydantic_fields = {}
        for field_name, field_info in fields.items():
            field_type = field_info.python_type or str

            # Apply constraints based on field_info metadata
            final_field = PydanticField(
                default=field_info.default,
                # default_factory=field_info.default_factory,
                alias=field_info.alias,
                title=field_info.title,
                description=field_info.description,
                # Pass validation constraints that Pydantic understands
                **{
                    k: v
                    for k, v in {
                        "min_length": getattr(field_info, "min_length", None),
                        "max_length": getattr(field_info, "max_length", None),
                        "regex": getattr(field_info, "regex", None),
                        "gt": getattr(field_info, "gt", None),
                        "ge": getattr(field_info, "ge", None),
                        "lt": getattr(field_info, "lt", None),
                        "le": getattr(field_info, "le", None),
                        "multiple_of": getattr(field_info, "multiple_of", None),
                        "min_items": getattr(field_info, "min_items", None),
                        "max_items": getattr(field_info, "max_items", None),
                    }.items()
                    if v is not None
                },
            )

            pydantic_fields[field_name] = (field_type, final_field)

        # Create Pydantic model as __pydantic_model__
        pydantic_model = create_model(
            f"{name}Model", __base__=BaseModel, **pydantic_fields
        )
        setattr(new_class, "__pydantic_model__", pydantic_model)
        tbname = getattr(cls, "_tablename", None)

        # Register the class
        cls._registry[tbname] = new_class  # type: ignore

        # Set up back-populates relationship
        cls._setup_back_populates(new_class, relationships, foreign_keys) # type: ignore

        return new_class

    @classmethod
    def _extract_related_model_from_fk(cls, foreign_key: ForeignConstraint):
        """Extract related model name from foreign key consraint"""
        table_name = foreign_key.table
        for model_name, model_class in cls._registry.items():
            if model_class.get_table_name() == table_name:
                return model_name
        return None

    @classmethod
    def _setup_back_populates(
        cls,
        model_class: Type["Model"],
        relationships: Dict[str, RelationshipInfo],
        foreign_keys: Dict[str, str],
    ):
        """Set up back-populates relationship between models"""
        for rel_name, rel_info in relationships.items():
            if rel_info.back_populates:
                type_hints = get_type_hints(
                    model_class, globalns=model_class.__dict__.get("__globals__", {})
                )
                rel_type = type_hints.get(rel_name)
                if rel_type:
                    related_model = cls._resolve_type(rel_type)
                    if related_model and hasattr(related_model, "_relationships"):
                        if rel_info.back_populates in related_model._relationships:
                            # Link the relationships
                            pass

    @classmethod
    def _resolve_type(cls, type_hint: Any) -> Optional[Type["Model"]]:
        """Resole forward references and get the actual model class"""
        try:
            if isinstance(type_hint, ForwardRef):
                globals = sys.modules[__name__].__dict__
                try:
                    actual_type = type_hint._evaluate(globals, globals, recursive_guard=frozenset())
                except (NameError, AttributeError):
                    # If evaluation fails, try to find the class in the registry
                    class_name = type_hint.__forward_arg__
                    for model_cls in cls._registry.values():
                        if model_cls.__name__ == class_name:
                            return model_cls
                    return None
            else:
                actual_type = type_hint

            # Handle List[Model] and Optional[Model]
            origin = get_origin(actual_type)
            if origin in (list, List):
                args = get_args(actual_type)
                if args:
                    actual_type = args[0]
            elif origin in Union: # type: ignore
                args = [arg for arg in get_args(actual_type) if arg is not type(None)]
                if args:
                    actual_type = args[0]
            if isinstance(actual_type, type) and issubclass(actual_type, Model):
                return actual_type
        except Exception:
            pass
        return None

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
            **metadata,
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
    _relationships: Dict[str, RelationshipInfo]
    _foreign_keys: Dict[str, str]
    _tablename: str
    __pydantic_model__: Type[BaseModel]
    _session: Optional[Union["Session", "AsyncSession"]] = None

    _relationship_cache: Dict[str, Any] = PrivateAttr(default_factory=dict)
    _relationship_loaded: Dict[str, bool] = PrivateAttr(default_factory=dict)

    def __init__(self, **kwargs) -> None:
        field_kwargs = {}
        rel_kwargs = {}

        for key, value in kwargs.items():
            if key in self._relationships:
                rel_kwargs[key] = value
            else:
                field_kwargs[key] = value

        # Validate and set fields using Pydantic
        pydantic_instance = self.__pydantic_model__(**field_kwargs)

        for field_name in self._fields:
            value = getattr(pydantic_instance, field_name)
            field_info = self._fields[field_name]

            # Handle auto-generated values
            if value is None:
                if field_info.auto_now_add:
                    value = datetime.now()
                elif field_info.default is not ...:
                    value = field_info.get_default_value()

            # Additional validation
            if value is not None:
                value = field_info.validate_value(value)

            setattr(self, field_name, value)

        # Set relationship attributes
        for rel_name, value in rel_kwargs.items():
            setattr(self, rel_name, value)

        # Set auto_now fields
        for field_name, field_info in self._fields.items():
            if field_info.auto_now:
                setattr(self, field_name, datetime.now())

        # Set provided relationship data
        for rel_name, value in rel_kwargs.items():
            self._relationship_cache[rel_name] = value
            self._relationship_loaded[rel_name] = True

    def __getattribute__(self, name: str) -> Any:
        """Lazy load relationships when accessed"""
        # Get the class relationship
        relationships = object.__getattribute__(self, "_relationships")

        loaded = object.__getattribute__(self, "relationship_loaded")
        if name in relationships and not getattr(loaded, "get", lambda *_: False)(name, False):
            return self._get_relationship(name)

        return object.__getattribute__(self, name)

    def __setattr__(self, name: str, value: Any) -> None:
        if hasattr(self, "_relationships") and name in self._relationships:
            self._set_relationship(name, value)
        else:
            super().__setattr__(name, value)

    def _get_relationship(self, rel_name: str) -> Any:
        """Load related objects from database"""
        if self._relationship_loaded.get(rel_name, False):
            return self._relationship_cache.get(rel_name)

        if not self._session:
            raise ValueError("Cannot load relationship: model not bound to a session")

        rel_info = self._relationships[rel_name]
        related_objects = self._load_relationship(rel_name, rel_info)

        # Cache the result
        self._relationship_cache[rel_name] = related_objects
        self._relationship_loaded[rel_name] = True

        return related_objects

    def _set_relationship(self, rel_name: str, value: Any) -> None:
        """Set a relationship and handle back-populates"""
        rel_info = self._relationships[rel_name]

        # Set the relationship value
        self._relationship_cache[rel_name] = value
        self._relationship_loaded[rel_name] = True

        # Handle a back populates
        if rel_info.back_populates and value is not None:
            if isinstance(value, list):
                for item in value:
                    if hasattr(item, rel_info.back_populates):
                        setattr(value, rel_info.back_populates, self)
            else:
                if hasattr(value, rel_info.back_populates):
                    setattr(value, rel_info.back_populates, self)

    def _load_relationship(self, rel_name: str, rel_info: RelationshipInfo) -> Any:
        """Load a relationship from the database"""
        type_hints = get_type_hints(self.__class__)
        rel_type = type_hints.get(rel_name)

        if not rel_type:
            raise ValueError(f"Cannot determine type for relationship {rel_name}")

        origin = get_origin(rel_type)
        is_list = origin in (list, List)

        if is_list:
            return self._load_to_many_relationship(rel_name, rel_type)
        else:
            return self._load_to_one_relationship(rel_name, rel_type)

    def _load_to_many_relationship(
        self, rel_name: str, rel_type: Any
    ) -> List["Model"]:
        """Loaad one-to-many or many-to-many relationships"""
        related_model = ModelMeta._resolve_type(rel_type)
        if not related_model:
            raise ValueError(
                f"Cannot determine related model for relationship {rel_name}"
            )

        fk_field = None
        for field_name, field_info in related_model._fields.items():
            if (
                field_info.foreign_key
                and field_info.foreign_key.table.lower() == self._tablename.lower()
            ):
                fk_field = field_name
                break

        if not fk_field:
            # Try common naming convention
            fk_field = f"{self.__class__.__name__.lower()}_id"

        # Get this instance's primary key
        pk_field, pk_value = self._get_primary_key()
        if not pk_value:
            return []

        query = select(related_model).where(
            getattr(related_model, fk_field) == pk_value
        )

        if isinstance(self._session, Session):
            return self._session.exec(query)
        else:
            # Handle async
            pass

    def _load_to_one_relationship(
        self,
        rel_name: str,
        rel_type: Any,
    ) -> Optional["Model"]:
        """Load many-to-one or one-to-one relationships"""
        related_model = ModelMeta._resolve_type(rel_type)
        if not related_model:
            raise ValueError(f"Cannot resolve related model for {rel_name}")

        # Look for foreign key in this model that points to the related model
        fk_field = None
        for field_name, field_info in self._fields.items():
            if (
                field_info.foreign_key
                and field_info.foreign_key.table.lower()
                == related_model.get_table_name().lower()
            ):
                fk_field = field_name
                break

        if not fk_field:
            # Try common naming convention
            fk_field = f"{related_model.__name__.lower()}_id"

        # Get the foreign key value
        fk_value = getattr(self, fk_field, None)
        if not fk_value:
            return None

        # Get the related model's primary key
        related_pk = related_model._get_primary_key_field()

        # Build and execute query
        query = (
            select(related_model)
            .where(getattr(related_model, related_pk) == fk_value)
            .limit(1)
        )
        if isinstance(self._session, Session):
            results = self._session.exec(query)
            return results[0] if results else None
        else:
            # Handle async
            pass

    def _get_primary_key(self) -> Tuple[Optional[str], Any]:
        """Get the primary key value field name and value"""
        for field_name, field_info in self._fields.items():
            if field_info.primary_key:
                return field_name, getattr(self, field_name)
        return None, None

    @classmethod
    def _get_primary_key_field(cls) -> str:
        """Get the primary key field name for this model"""
        for field_name, field_info in cls._fields.items():
            if field_info.primary_key:
                return field_name

        # Fallback
        common_pks = ["id", f"{cls.__name__.lower()}_id"]
        for pk in common_pks:
            if pk in cls._fields:
                return pk

        raise ValueError(f"No primary key found for model {cls.__name__}")

    @classmethod
    def __getattr__(cls, name: str) -> ColumnExpression:
        """Allow User.name syntax"""
        if name in cls._fields:
            return ColumnExpression(cls, name)
        raise AttributeError(f"{cls.__name__} has no attribute {name}")

    @classmethod
    def __getitem__(cls, name: str) -> ColumnExpression:
        """Allow User['name'] syntax"""
        return getattr(cls, name)

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
        placeholder = "%s" if dialect == DatabaseDialect.POSTGRES else "?"
        placeholders = ", ".join([placeholder] * len(field_names))
        field_names_str = ", ".join(field_names)

        sql = (
            f"INSERT INTO {self._tablename} ({field_names_str}) VALUES ({placeholders})"
        )
        params = tuple(getattr(self, fname) for fname in field_names)

        return sql, params

