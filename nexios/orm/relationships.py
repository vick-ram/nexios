from __future__ import annotations

from enum import Enum
from typing import TYPE_CHECKING, Any, Optional, Type, Union, overload, Literal, Dict
from dataclasses import dataclass, field
from pydantic._internal._repr import Representation
if TYPE_CHECKING:
    from nexios.orm.model import NexiosModel
    from nexios.orm.utils import OnDeleteOrUpdate, LazyOp


class RelationshipType(Enum):
    ONE_TO_ONE = "one_to_one"
    ONE_TO_MANY = "one_to_many"
    MANY_TO_ONE = "many_to_one"
    MANY_TO_MANY = "many_to_many"

@dataclass
class RelationshipInfo(Representation):
    """Information about a relationship between models."""

    field_name: str
    related_model_name: str  # Store as string to avoid circular imports
    relationship_type: RelationshipType
    foreign_key: Optional[str] = None
    related_field_name: Optional[str] = None
    through: Optional[str] = None  # Store as string
    ondelete: Optional[OnDeleteOrUpdate] = None
    onupdate: Optional[OnDeleteOrUpdate] = None
    nullable: bool = False
    unique: bool = False
    back_populates: Optional[str] = None
    lazy: LazyOp = "select"

    # Database constraints
    deferrable: Optional[bool] = None
    initially_deferred: Optional[bool] = None

    # For many-to-many relationships
    association_table: Optional[str] = None
    local_column: Optional[str] = None
    foreign_column: Optional[str] = None

    # For tracking
    is_resolved: bool = False
    metadata: Dict[str, Any] = field(default_factory=dict)

    # Cache for resolved models
    _related_model: Optional[Type["NexiosModel"]] = None
    _through_model: Optional[Type["NexiosModel"]] = None

    @property
    def through_model(self) -> Optional[Type["NexiosModel"]]:
        if self._through_model is None and self.through:
            from nexios.orm.model import NexiosModel
            try:
                if (
                        hasattr(NexiosModel, "__registry__")
                        and self.through in NexiosModel.__registry__
                ):
                    self._through_model = NexiosModel.__registry__[self.through]
            except (AttributeError, KeyError):
                pass
        return self._through_model

    @property
    def related_model(self) -> Optional[Type["NexiosModel"]]:
        if self._related_model is None and self.related_model_name:
            from nexios.orm.model import NexiosModel
            try:
                if (
                        hasattr(NexiosModel, "__registry__")
                        and self.related_model_name in NexiosModel.__registry__
                ):
                    self._related_model = NexiosModel.__registry__[
                        self.related_model_name
                    ]
            except (AttributeError, KeyError):
                pass
        return self._related_model


# For one-to-one, one-to-many and many-to-one
@overload
def Relationship(
        related_model: Union[Type[NexiosModel], str, None] = None,
        relationship_type: Literal[
            RelationshipType.MANY_TO_ONE,
            RelationshipType.ONE_TO_MANY,
            RelationshipType.ONE_TO_ONE,
        ] = RelationshipType.MANY_TO_ONE,
        *,
        foreign_key: Optional[str] = None,
        related_field_name: Optional[str] = None,
        **kwargs: Any,
) -> Any: ...


# For many-to-many with through model
@overload
def Relationship(
        related_model: Union[Type[NexiosModel], str, None] = None,
        relationship_type: Literal[
            RelationshipType.MANY_TO_MANY
        ] = RelationshipType.MANY_TO_MANY,
        *,
        through: Union[Type["NexiosModel"], str, None] = None,
        local_column: Optional[str] = None,
        foreign_column: Optional[str] = None,
        **kwargs: Any,
) -> Any: ...


def Relationship(
        related_model: Union[Type[NexiosModel], str, None] = None,
        relationship_type: Optional[RelationshipType] = None,
        *,
        foreign_key: Optional[str] = None,
        related_field_name: Optional[str] = None,
        through: Optional[Union[Type["NexiosModel"], str]] = None,
        ondelete: Optional[OnDeleteOrUpdate] = None,
        onupdate: Optional[OnDeleteOrUpdate] = None,
        nullable: bool = False,
        unique: bool = False,
        back_populates: Optional[str] = None,
        lazy: LazyOp = "select",
        deferrable: Optional[bool] = None,
        initially_deferred: Optional[bool] = None,
        local_column: Optional[str] = None,
        foreign_column: Optional[str] = None,
        **kwargs: Any,
) -> Any:
    rel_model_str = None
    if related_model:
        rel_model_str = (
            related_model if isinstance(related_model, str) else related_model.__name__
        )
    through_model_str = None
    if through:
        through_model_str = (
            through
            if isinstance(through, str)
            else through.__name__
            if through
            else None
        )

    return RelationshipInfo(
        field_name="",
        related_model_name=rel_model_str or "",
        relationship_type=relationship_type or RelationshipType.MANY_TO_ONE,
        foreign_key=foreign_key,
        related_field_name=related_field_name,
        through=through_model_str,
        ondelete=ondelete,
        onupdate=onupdate,
        nullable=nullable,
        unique=unique,
        back_populates=back_populates,
        lazy=lazy,
        deferrable=deferrable,
        initially_deferred=initially_deferred,
        local_column=local_column,
        foreign_column=foreign_column,
        metadata=kwargs,
    )
