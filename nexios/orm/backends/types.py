# nexios/orm/backends/types
from enum import Enum
# from typing_extensions import Literal

# DatabaseDialect = Literal['sqlite', 'postgres', 'mysql']

class MigrationStatus(Enum):
    PENDING = 'pending'
    RUNNING = 'running'
    COMPLETED = 'completed'
    FAILED = 'failed'
