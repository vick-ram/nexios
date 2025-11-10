from typing_extensions import Type, Optional, Any, TYPE_CHECKING

if TYPE_CHECKING:
    from nexios.orm.model import Model

class Relationship:
    """Handle model relationships"""
    
    def __init__(
        self,
        related_model: Type["Model"],
        backref: Optional[str] = None,
        foreign_key: Optional[str] = None,
        lazy: bool = True,
        userlist: bool = True,
        **kwargs: Any,
    ) -> None:
        self.related_model = related_model
        self.backref = backref
        self.foreign_key = foreign_key
        self.lazy = lazy
        self.userlist = userlist
        self.kwargs = kwargs
