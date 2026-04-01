from __future__ import annotations

import types
from typing import (
    TYPE_CHECKING,
    Union,
    Optional,
    List,
    Type,
    Tuple,
    Dict,
    Any,
    ClassVar,
    ForwardRef,
    get_origin,
    get_args,
    dataclass_transform,
)
from pydantic import BaseModel as PydanticBaseModel
from pydantic_core import PydanticUndefined as Undefined
from pydantic._internal._model_construction import ModelMetaclass as ModelMetaclass
from nexios.orm.fields import Field, FieldInfo
from nexios.orm.relationships import RelationshipInfo, RelationshipType
from nexios.orm.descriptors import RelationshipDescriptor
from nexios.orm.misc.refs import ResolveForwardRefs
from nexios.orm.utils import (
    NexiosModelConfig,
    get_tablename_for_class,
    get_model_fields,
    set_config_value,
    to_snake_case,
    IS_PYDANTIC_V2,
)


@dataclass_transform(kw_only_default=True, field_specifiers=(Field, FieldInfo))
class NexiosModelMetaclass(ModelMetaclass):
    __relationships__: Dict[str, RelationshipInfo] = {}
    model_config: NexiosModelConfig
    model_fields: Dict[str, FieldInfo] = {}
    __config__: Type[NexiosModelConfig]
    __registry__: Dict[str, Type["NexiosModel"]] = {}

    def __new__(
        mcs,
        name: str,
        bases: Tuple[Type[Any], ...],
        namespace: Dict[str, Any],
        **kwargs: Any,
    ):
        namespace["__relationships__"] = {}

        relationships: Dict[str, RelationshipInfo] = {}
        relationship_items = {}
        pydantic_dict = {}
        original_annotations = namespace.get("__annotations__", {})
        pydantic_annotations = {}
        relationship_annotations = {}

        for k, v in namespace.items():
            if isinstance(v, RelationshipInfo):
                relationship_items[k] = v
                relationship_annotations[k] = original_annotations.get(k)
            else:
                pydantic_dict[k] = v
                if k in original_annotations:
                    pydantic_annotations[k] = original_annotations.get(k)
        dict_used = {
            **pydantic_dict,
            "__annotations__": pydantic_annotations,
        }
        allowed_config_keys = {"read_from_attributes", "from_attributes", "table"}

        config_kwargs = {
            key: kwargs[key] for key in kwargs.keys() & allowed_config_keys
        }
        for k in list(kwargs.keys()):
            if k in allowed_config_keys:
                config_kwargs[k] = kwargs.pop(k)

        # Create the class
        cls = super().__new__(mcs, name, bases, dict_used, **config_kwargs)

        # Register the class
        mcs.__registry__[cls.__name__] = cls

        # Process relationships
        for attr_name, rel_info in relationship_items.items():
            mcs._process_relationship(
                cls, attr_name, rel_info, original_annotations, relationships
            )

        cls.__relationships__ = relationships

        # Add ColumnDescriptor
        mcs._add_column_descriptors(cls)

        cls.__annotations__ = {
            **relationship_annotations,
            **pydantic_annotations,
            **cls.__annotations__,
        }

        cls.resolve_forward_references()
        return cls

    @classmethod
    def _add_column_descriptors(mcs, cls: Type["NexiosModel"]):
        """Replace model fields with ColumnDescriptors"""
        from nexios.orm.descriptors import ColumnDescriptor

        # Get all field names from Pydantic's model_fields
        # These are the actual database columns (not relationships)
        for field_name, field_info in cls.model_fields.items():
            # Skip relationship fields (they're handled separately)
            if field_name in cls.__relationships__:
                continue

            # Create and set the ColumnDescriptor
            descriptor = ColumnDescriptor(field_name, cls)
            setattr(cls, field_name, descriptor)

    @classmethod
    def _process_relationship(
        mcs,
        cls: Type[NexiosModel],
        attr_name: str,
        rel_info: RelationshipInfo,
        original_annotations: Dict[str, Any],
        relationships: Dict[str, RelationshipInfo],
    ):
        annotation = original_annotations.get(attr_name)
        # Parse relationship
        parsed_info = mcs._parse_relationship_annotation(annotation, rel_info)
        # Determine related model
        related_model_name = mcs._determine_related_model(parsed_info, rel_info)
        if not related_model_name:
            raise ValueError(
                f"Could not determine related model for relationship '{attr_name}' "
                f"in class '{cls.__name__}'"
            )
        # Determine relationship type
        relationship_type = mcs._determine_relationship_type(
            parsed_info, rel_info, attr_name
        )

        # Determine foreign key
        foreign_key = mcs._determine_foreign_key(
            rel_info, relationship_type, cls.__name__, related_model_name
        )

        print(
            f"Foreign key for relationship '{attr_name}' in '{cls.__name__}': {foreign_key}"
        )

        # Resolve through model if provided
        through = mcs._resolve_through_model(rel_info)

        association_table = None
        if rel_info.through:
            if isinstance(rel_info.through, str):
                association_table = rel_info.through
            elif (
                hasattr(rel_info.through, "__tablename__")
                and rel_info.through.__tablename__
            ):
                association_table = rel_info.through.__tablename__
            else:
                association_table = getattr(rel_info.through, "__name__", None)

        # reate final relationship info
        final_info = RelationshipInfo(
            field_name=attr_name,
            related_model_name=related_model_name,
            relationship_type=relationship_type,
            foreign_key=foreign_key,
            related_field_name=rel_info.related_field_name,
            through=through,
            ondelete=rel_info.ondelete,
            onupdate=rel_info.onupdate,
            nullable=rel_info.nullable,
            unique=rel_info.unique,
            back_populates=rel_info.back_populates,
            lazy=rel_info.lazy,
            deferrable=rel_info.deferrable,
            initially_deferred=rel_info.initially_deferred,
            association_table=association_table,
            local_column=rel_info.local_column,
            foreign_column=rel_info.foreign_column,
            metadata=rel_info.metadata,
        )
        relationships[attr_name] = final_info
        setattr(cls, attr_name, RelationshipDescriptor(cls, attr_name, final_info))

    @classmethod
    def _parse_relationship_annotation(
        mcs, annotation: Any, rel_info: RelationshipInfo
    ) -> Dict[str, Any]:
        result = {
            "related_model": None,
            "relationship_type": None,
            "is_optional": False,
            "is_list": False,
        }

        if annotation is None:
            return result

        def normalize_annotation(ann: str) -> str:
            return ann.replace("typing.", "").replace("typing_extensions.", "")

        # String annotations
        if isinstance(annotation, str):
            annotation = annotation.replace(" ", "")

            # Optional[T]
            normalized_annotation = normalize_annotation(annotation)
            if normalized_annotation.startswith(("Optional[", "Union[")):
                result["is_optional"] = True
                inner = normalized_annotation[normalized_annotation.find("[") + 1 : -1]
                nested = mcs._parse_relationship_annotation(inner, rel_info)
                result.update(nested)
                result["is_optional"] = True
                return result

            # List[T]
            if normalized_annotation.startswith(("List[", "list[")):
                result["is_list"] = True
                inner = normalized_annotation[
                    normalized_annotation.find("[") + 1 : -1
                ].strip("\"'")
                result["related_model"] = inner
                result["relationship_type"] = RelationshipType.ONE_TO_MANY
                return result

            # Bare types
            result["related_model"] = annotation.strip("\"'")
            return result

        # typing objects
        origin = get_origin(annotation)
        args = get_args(annotation)

        # Optional[T]
        if origin is Union:
            result["is_optional"] = True
            for arg in args:
                if arg is type(None):
                    continue
                nested = mcs._parse_relationship_annotation(arg, rel_info)
                result.update(nested)
                result["is_optional"] = True
                return result

        # List[T]
        if origin in (list, List):
            result["is_list"] = True
            if args:
                arg = args[0]
                if isinstance(arg, str):
                    result["related_model"] = arg
                elif isinstance(arg, ForwardRef):
                    result["related_model"] = arg.__forward_arg__
                elif isinstance(arg, type):
                    result["related_model"] = arg.__name__
            result["relationship_type"] = RelationshipType.ONE_TO_MANY
            return result

        # ForwardRef
        if isinstance(annotation, ForwardRef):
            result["related_model"] = annotation.__forward_arg__
            return result

        # type directly
        if isinstance(annotation, type):
            result["related_model"] = annotation.__name__
            return result

        return result

    @classmethod
    def _determine_related_model(
        mcs, parsed_info: Dict[str, Any], rel_info: RelationshipInfo
    ) -> Optional[str]:
        if rel_info.related_model:
            if isinstance(rel_info.related_model, str):
                return rel_info.related_model
            return rel_info.related_model.__name__

        if parsed_info.get("related_model"):
            return parsed_info["related_model"]

        return rel_info.related_model_name

    @classmethod
    def _determine_relationship_type(
        mcs, parsed_info: Dict[str, Any], rel_info: RelationshipInfo, attr_name: str
    ) -> RelationshipType:
        rel_type: RelationshipType = RelationshipType.MANY_TO_ONE

        if rel_info.relationship_type:
            return rel_info.relationship_type

        if parsed_info.get("relationship_type"):
            rel_type = parsed_info["relationship_type"]

        if parsed_info.get("is_list"):
            rel_type = RelationshipType.ONE_TO_MANY

        if rel_info.unique:
            rel_type = RelationshipType.ONE_TO_ONE

        if not parsed_info.get("is_list") and rel_type == RelationshipType.MANY_TO_ONE:
            rel_type = RelationshipType.ONE_TO_ONE

        return rel_type

    @classmethod
    def _determine_foreign_key(
        mcs,
        rel_info: RelationshipInfo,
        relationship_type: RelationshipType,
        current_model_name: str,
        related_model_name: str,
    ) -> Optional[str]:

        if rel_info.foreign_key:
            return rel_info.foreign_key

        current_cls = None
        try:
            current_cls = mcs.__registry__.get(current_model_name)
        except AttributeError:
            current_cls = None

        related_cls = mcs.__registry__.get(related_model_name)

        def fk_matches_target(fk_val: Any, target_name: str) -> bool:
            if not fk_val:
                return False
            if isinstance(fk_val, str):
                fk_s = fk_val.strip()
                if "." in fk_s:
                    left, _ = fk_s.rsplit(".", 1)
                    left_l = left.lower()

                    model_cls_from_registry = mcs.__registry__.get(target_name)
                    tablename_from_registry = ""
                    if model_cls_from_registry:
                        tablename_from_registry = (
                            get_tablename_for_class(model_cls_from_registry) or ""
                        )

                    candidates = {
                        target_name.lower(),
                        to_snake_case(target_name),
                        tablename_from_registry.lower(),
                    }
                    return left_l in candidates
                else:
                    if fk_s == f"{to_snake_case(target_name)}_id" or fk_s == "id":
                        return True
            return False

        # For one-to-one, check both sides
        if relationship_type == RelationshipType.ONE_TO_ONE:
            # First check if current model has FK to related
            if current_cls is not None:
                for field_name, field_info in get_model_fields(current_cls).items():
                    fk = getattr(field_info, "foreign_key", Undefined)
                    if fk is not Undefined and fk:
                        if fk_matches_target(fk, related_model_name):
                            return field_name

            # Then check if related model has FK to current
            if related_cls is not None:
                for field_name, field_info in get_model_fields(related_cls).items():
                    fk = getattr(field_info, "foreign_key", Undefined)
                    if fk is not Undefined and fk:
                        if fk_matches_target(fk, current_model_name):
                            # Return the FK field name on the related model
                            return field_name

            # Fallback to convention - assume FK on current model
            return f"{to_snake_case(related_model_name)}_id"

        # Rest of your existing logic for other relationship types...
        current = to_snake_case(current_model_name)
        related = to_snake_case(related_model_name)

        print(
            f"Determining FK for relationship in '{current_model_name}' to '{related_model_name}' with relationship type '{relationship_type}'"
        )

        fk = f"{related}_id"

        match (relationship_type):
            case RelationshipType.MANY_TO_ONE:
                return (
                    fk
                    if current_cls is not None and fk in get_model_fields(current_cls)
                    else None
                )
            case RelationshipType.ONE_TO_ONE:
                return (
                    fk
                    if current_cls is not None and fk in get_model_fields(current_cls)
                    else None
                )
            case RelationshipType.ONE_TO_MANY:
                return None
            case RelationshipType.MANY_TO_MANY:
                return None
            case _:
                return None

    # @classmethod
    # def _determine_foreign_key(
    #         mcs,
    #         rel_info: RelationshipInfo,
    #         relationship_type: RelationshipType,
    #         current_model_name: str,
    #         related_model_name: str
    # ) -> Optional[str]:

    #     if rel_info.foreign_key:
    #         return rel_info.foreign_key

    #     current_cls = None
    #     try:
    #         current_cls = mcs.__registry__.get(current_model_name)  # User
    #     except AttributeError:
    #         current_cls = None

    #     related_cls = mcs.__registry__.get(related_model_name)  # Profile

    #     def fk_matches_target(fk_val: Any, target_name: str, target_cls: Optional[Type] = None) -> bool:
    #         if not fk_val:
    #             return False
    #         if isinstance(fk_val, str):
    #             fk_s = fk_val.strip()
    #             if "." in fk_s:
    #                 left, _ = fk_s.rsplit(".", 1)
    #                 left_l = left.lower()
    #                 candidates = {
    #                     target_name.lower(),
    #                     _to_snake_case(target_name),
    #                 }
    #                 if target_cls:
    #                     tablename = (get_tablename_for_class(target_cls) or "").lower()
    #                     candidates.add(tablename)
    #                 return left_l in candidates
    #             else:
    #                 if fk_s == f"{_to_snake_case(target_name)}_id" or fk_s == "id":
    #                     return True
    #         return False

    #     # For one-to-one relationships
    #     if relationship_type == RelationshipType.ONE_TO_ONE:
    #         # Check if related model (Profile) has a foreign key to current model (User)
    #         if related_cls is not None:
    #             for field_name, field_info in get_model_fields(related_cls).items():
    #                 fk = getattr(field_info, "foreign_key", Undefined)
    #                 if fk is not Undefined and fk:
    #                     if fk_matches_target(fk, current_model_name, current_cls):
    #                         # Return the field name on the related model that holds the FK
    #                         return field_name

    #         # Check if current model (User) has a foreign key to related model (Profile)
    #         if current_cls is not None:
    #             for field_name, field_info in get_model_fields(current_cls).items():
    #                 fk = getattr(field_info, "foreign_key", Undefined)
    #                 if fk is not Undefined and fk:
    #                     if fk_matches_target(fk, related_model_name, related_cls):
    #                         return field_name

    #         # Fallback: assume foreign key is on related model with naming convention
    #         return f"{_to_snake_case(current_model_name)}_id"

    #     # For MANY_TO_ONE relationships
    #     if relationship_type == RelationshipType.MANY_TO_ONE:
    #         fk = f"{_to_snake_case(related_model_name)}_id"
    #         if current_cls is not None and fk in get_model_fields(current_cls):
    #             return fk
    #         return None

    #     # For ONE_TO_MANY, foreign key is on the related model
    #     if relationship_type == RelationshipType.ONE_TO_MANY:
    #         # Return the field name on the related model that points to current model
    #         fk = f"{_to_snake_case(current_model_name)}_id"
    #         return fk

    #     return None

    @classmethod
    def _resolve_through_model(mcs, rel_info: RelationshipInfo) -> Optional[str]:
        if rel_info.through is None:
            return None

        if isinstance(rel_info.through, str):
            return rel_info.through

        if hasattr(rel_info.through, "__name__"):
            return rel_info.through.__name__

        return str(rel_info.through)


class NexiosModel(
    PydanticBaseModel, ResolveForwardRefs, metaclass=NexiosModelMetaclass
):
    __tablename__: ClassVar[Optional[str]] = None
    __relationships__: ClassVar[Dict[str, RelationshipInfo]] = {}
    __primary_key__: ClassVar[Union[Tuple[str, ...], List[str], str, None]] = None

    if IS_PYDANTIC_V2:
        model_config = NexiosModelConfig(from_attributes=True)
    else:

        class Config:
            orm_mode = True

    def __init_subclass__(cls, table: Optional[bool] = None, **kwargs):
        super().__init_subclass__(**kwargs)

        cls.__registry__[cls.__name__] = cls

        if table is not None:
            set_config_value(model=cls, parameter="table", value=table)

        tablename = get_tablename_for_class(cls)
        cls.__tablename__ = tablename

    def __setattr__(self, name: str, value: Any) -> types.NoneType:
        if name not in self.__relationships__:
            super().__setattr__(name, value)

    @classmethod
    def _resolve_relationships(cls):
        for rel_name, rel_info in cls.__relationships__.items():
            if not rel_info.is_resolved:
                if rel_info.back_populates:
                    related_model = rel_info.related_model
                    if related_model and hasattr(related_model, "__relationships__"):
                        related_rel = related_model.__relationships__.get(
                            rel_info.back_populates
                        )

                        if related_rel:
                            related_rel.back_populates = rel_name
                            related_rel.is_resolved = True
                            rel_info.is_resolved = True
                rel_info.is_resolved = True

    @classmethod
    def get_fields(cls) -> Dict[str, FieldInfo]:
        return cls.model_fields

    @classmethod
    def get_relationships(cls) -> Dict[str, RelationshipInfo]:
        return cls.__relationships__

    @classmethod
    def get_primary_key(cls) -> Any:
        from nexios.orm.query.expressions import ColumnExpression

        pk = getattr(cls, "__primary_key__", None)
        if pk:
            if isinstance(pk, (tuple, list)):
                return tuple(pk) if len(pk) > 1 else pk[0]  # type: ignore
            return pk

        for field_name, field_info in get_model_fields(cls).items():
            if getattr(field_info, "primary_key", Undefined):
                field_ = getattr(cls, field_name)
                if isinstance(field_, ColumnExpression):
                    return field_.field_name
                else:
                    return field_
        return None
