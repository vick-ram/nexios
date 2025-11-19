from typing import Dict
from typing_extensions import Optional, Any


class RelationshipInfo:
    def __init__(
        self,
        back_populates: Optional[str] = None,
        sa_relationship_kwargs: Optional[Dict[str, Any]] = None,
    ) -> None:
        self.back_populates = back_populates
        self.sa_relationship_kwargs = sa_relationship_kwargs or {}


def Relationship(
    *,
    back_populates: Optional[str] = None,
    **kwargs: Any,
) -> Any:
    return RelationshipInfo(
        back_populates=back_populates,
        sa_relationship_kwargs=kwargs,
    )
