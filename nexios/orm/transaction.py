from __future__ import annotations

import logging
import threading
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Callable, Self, TypeVar, Any, Optional, List, Union, Dict

from nexios.orm.connection import SyncDatabaseConnection, SyncCursor, SyncQueryResult
from nexios.orm.misc.exceptions import  TransactionException

_T = TypeVar("_T")

logger = logging.getLogger(__name__)


class IsolationLevel(Enum):
    READ_UNCOMMITTED = "READ UNCOMMITTED"
    READ_COMMITTED = "READ COMMITTED"
    REPEATABLE_READ = "REPEATABLE READ"
    SERIALIZABLE = "SERIALIZABLE"

    # SQLite specific
    DEFERRED = "DEFERRED"
    IMMEDIATE = "IMMEDIATE"
    EXCLUSIVE = "EXCLUSIVE"

    @classmethod
    def from_string(cls, level: str) -> Self:
        """Convert string to IsolationLevel."""
        level_upper = level.upper().replace('-', '_').replace(' ', '_')
        for member in cls:
            if member.value.upper().replace(' ', '_') == level_upper:
                return member
        raise ValueError(f"Unknown isolation level: {level}")


class TransactionState(Enum):
    """Transaction states"""

    IDLE = "idle"
    STARTING = "starting"
    ACTIVE = "active"
    SAVEPOINT = " savepoint_active"
    COMMITTING = "committing"
    ROLLING_BACK = "rolling_back"
    COMMITTED = "committed"
    ROLLED_BACK = "rolled_back"
    FAILED = "failed"
    READ_ONLY = "read_only"
    CLOSED = "closed"

class OperationType(Enum):
    """Types of operations that can be performed."""
    BEGIN = "begin"
    COMMIT = "commit"
    ROLLBACK = "rollback"
    SAVEPOINT = "savepoint"
    RELEASE_SAVEPOINT = "release_savepoint"
    ROLLBACK_TO_SAVEPOINT = "rollback_to_savepoint"
    EXECUTE = "execute"
    CLOSE = "close"

@dataclass
class Savepoint:
    name: str
    created_at: float = field(default_factory=time.time)
    is_released: bool = False


class Transaction:
    def __init__(
        self,
        connection: SyncDatabaseConnection,
        isolation_level: IsolationLevel = IsolationLevel.READ_COMMITTED,
        readonly: bool = False,
        autocommit: bool = False,
        timeout: Optional[float] = None,
        max_retries: int = 0,
        retry_delay: float = 0.1,
    ):
        self.connection = connection
        self.isolation_level = (isolation_level if isinstance(isolation_level, IsolationLevel) else IsolationLevel.from_string(isolation_level))
        self.readonly = readonly
        self.autocommit = autocommit
        self.timeout = timeout
        self.max_retries = max_retries
        self.retry_delay = retry_delay

        self.state = TransactionState.IDLE
        self._cursor: Optional[SyncCursor] = None
        self._savepoints: List[Savepoint] = []
        self._nested_level= 0
        self._start_time: Optional[float] = None
        self._last_operation: Optional[OperationType] = None
        self._lock = threading.RLock()

        self.stats = {
            'queries_executes': 0,
            'transactions_committed':0,
            'transactions_rolled_back': 0,
            'savepoints_created': 0,
            'retries_attempted': 0,
            'total_execution_time': 0.0
        }

        logger.debug(f"Transaction created: isolation={isolation_level}, "
                    f"readonly={readonly}, autocommit={autocommit}")

    def __enter__(self):
        self.begin()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        try:
            if exc_type is not None:
                logger.warning(f"Transaction exiting with exception: {exc_type.__name__}: {exc_val}")
                self.rollback()
            elif self.state == TransactionState.ACTIVE:
                self.commit()
            elif self.state in [TransactionState.SAVEPOINT, TransactionState.STARTING]:
                self.rollback()
        finally:
            self.close()

    def __check_state(self, operation: OperationType, allowed_states: List[TransactionState]):
        if self.state not in allowed_states:
            allowed_str = ", ".join(s.value for s in allowed_states)
            raise TransactionException(
                f"Cannot {operation} while in state {self.state.value}."
                f"Allowed states: {allowed_str}"
            )
        self._last_operation = operation
    
    def __execute_with_retry(self, operation: Callable, *args, **kwargs) -> SyncQueryResult:
        last_error = None

        for attempt in range(self.max_retries + 1):
            try:
                if attempt > 0:
                    self.stats['retries_attempted'] += 1
                    logger.debug(f"Retry attempt {attempt} for operation")
                    time.sleep(self.retry_delay * attempt)
                return operation(*args, **kwargs)
            except Exception as e:
                last_error = e
                logger.debug(f"Attempt {attempt + 1} failed: {e}")

                if attempt >= self.max_retries:
                    break

                error_msg = str(e).lower()
                retryable_errors = [
                    'deadlock',
                    'timeout',
                    'lock',
                    'busy',
                    'try again',
                    'retry',
                    'connection',
                    'temporary',
                    'would block'
                ]
                if not any(retry_err in error_msg for retry_err in retryable_errors):
                    break

        raise TransactionException(f"Operation failed after {self.max_retries + 1} attempts: {last_error}")
    
    def _release_savepoint(self, name: str) -> None:
        """Release a savepoint."""
        self.execute(f"RELEASE SAVEPOINT {name}")

    def _rollback_to_savepoint(self, name: str):
        self.execute(f"ROLLBACK TO SAVEPOINT {name}")
    
    def _savepoint(self, name: str):
        self.execute(f"SAVEPOINT {name}")

    def _set_isolation_level(self, isolation_level: IsolationLevel) -> None:
        """Set isolation level for next transaction."""
        self._isolation_level = isolation_level
    
    def _get_isolation_level(self) -> Optional[IsolationLevel]:
        """Get current isolation level."""
        return self._isolation_level

    def begin(self, isolation_level: Optional[IsolationLevel] = None, readonly: Optional[bool] = None):
        with self._lock:
            self.__check_state(OperationType.BEGIN, [TransactionState.IDLE, TransactionState.CLOSED])

            iso_level = (
                IsolationLevel.from_string(isolation_level) 
                if isinstance(isolation_level, str) else isolation_level
            ) or self.isolation_level
            is_readonly = readonly if readonly is not None else self.readonly

            self.state = TransactionState.STARTING
            self._start_time = time.time()
            self._nested_level = 0
            self._savepoints.clear()

            logger.debug(f"Beginning transaction: isolation={iso_level}, readonly={is_readonly}")

            try:
                self.execute("BEGIN")
                self.state = TransactionState.ACTIVE
                logger.info("Transaction started successfully")
            except Exception as e:
                self.state = TransactionState.FAILED
                logger.error(f"Failed to begin transaction: {e}")
                raise TransactionException(f"Failed to begin transaction: {e}")

    def commit(self):
        with self._lock:
            self.__check_state(OperationType.COMMIT, [TransactionState.ACTIVE, TransactionState.SAVEPOINT])

            if self._nested_level > 0:
                raise TransactionException(
                    f"Cannot commit with {self._nested_level} nested transactions. "
                    f"Release savepoints first."
                )
            self.state = TransactionState.COMMITTING
            logger.debug("Committing transaction")

            try:
                self.connection.commit()
                self.state = TransactionState.COMMITTED
                self.stats['transaction_committed'] += 1

                if self._start_time:
                    duration = time.time() - self._start_time
                    self.stats['total_execution_time'] += duration
                    logger.info(f"Transaction committed in {duration:.3f}s")
            except Exception as e:
                self.state = TransactionState.FAILED
                logger.error(f"Failed to commit transaction: {e}")
                raise TransactionException(f"Cannot commit transaction: {e}")

    def rollback(self, to_savepoint: Optional[str] = None):
        with self._lock:
            if to_savepoint:
                self.__check_state(OperationType.ROLLBACK_TO_SAVEPOINT, [TransactionState.ACTIVE, TransactionState.SAVEPOINT])
                
                savepoint_idx = -1
                for i, sp in enumerate(self._savepoints):
                    if sp.name == to_savepoint and not sp.is_released:
                        savepoint_idx = i
                        break
                
                if savepoint_idx == -1:
                    raise TransactionException(f"Savepoint '{to_savepoint}' not found or already released")
                logger.debug(f"Rolling back to savepoint: {to_savepoint}")

                try:
                    self._rollback_to_savepoint(to_savepoint) # type: ignore
                    self._savepoints = self._savepoints[:savepoint_idx + 1]
                    if self._nested_level == 0:
                        self.state = TransactionState.ACTIVE
                    else:
                        self.state = TransactionState.SAVEPOINT
                    
                    logger.info(f"Rolled back to savepoint: {to_savepoint}")
                except Exception as e:
                    self.state = TransactionState.FAILED
                    logger.error(f"Failed to rollback to savepoint: {e}")
                    raise TransactionException(f"Failed to rollback to savepoint '{to_savepoint}': {e}")
            else:
                self.__check_state(OperationType.ROLLBACK, [
                    TransactionState.ACTIVE,
                    TransactionState.SAVEPOINT,
                    TransactionState.STARTING,
                    TransactionState.FAILED
                ])
                self.state = TransactionState.ROLLING_BACK
                logger.debug("Rolling back transaction")

                try:
                    self.connection.rollback()
                    self.state = TransactionState.ROLLED_BACK
                    self.stats['transactions_rolled_back'] += 1
                    self._savepoints.clear()
                    self._nested_level = 0
                    
                    if self._start_time:
                        duration = time.time() - self._start_time
                        self.stats['total_execution_time'] += duration
                        logger.info(f"Transaction rolled back in {duration:.3f}s")
                    
                except Exception as e:
                    self.state = TransactionState.FAILED
                    logger.error(f"Failed to rollback transaction: {e}")
                    raise TransactionException(f"Failed to rollback transaction: {e}")

    def savepoint(self, name: str):
        with self._lock:
            self.__check_state(OperationType.SAVEPOINT, [
                TransactionState.ACTIVE,
                TransactionState.SAVEPOINT
            ])

            for sp in self._savepoints:
                if sp.name == name and not sp.is_released:
                    raise TransactionException(f"Savepoint '{name}' already exists")
            
            logger.debug(f"Creating savepoint: {name}")

            try:
                self._savepoint(name)
                self._savepoints.append(Savepoint(name))
                self._nested_level += 1
                self.state = TransactionState.SAVEPOINT
                self.stats['savepoints_created'] += 1
                logger.info(f"Savepoint created: {name} (level: {self._nested_level})")
            except Exception as e:
                logger.error(f"Failed to create savepoint: {e}")
                raise TransactionException(f"Failed to create savepoint '{name}': {e}")
    
    def release_savepoint(self, name: str) -> None:
        """Release a savepoint."""
        with self._lock:
            self.__check_state(OperationType.RELEASE_SAVEPOINT, [
                TransactionState.ACTIVE,
                TransactionState.SAVEPOINT
            ])
            
            # Find the savepoint
            savepoint = None
            for sp in self._savepoints:
                if sp.name == name and not sp.is_released:
                    savepoint = sp
                    break
            
            if not savepoint:
                raise TransactionException(f"Savepoint '{name}' not found or already released")
            
            logger.debug(f"Releasing savepoint: {name}")
            
            try:
                self._release_savepoint(name)
                savepoint.is_released = True
                self._nested_level -= 1
                
                # Update state based on remaining savepoints
                if self._nested_level == 0:
                    self.state = TransactionState.ACTIVE
                
                logger.info(f"Savepoint released: {name}")
                
            except Exception as e:
                logger.error(f"Failed to release savepoint: {e}")
                raise TransactionException(f"Failed to release savepoint '{name}': {e}")

    def execute(
        self,
        query: str,
        params: Union[tuple, List[tuple], Dict[str, Any], None] = None,
        many: bool = False,
        autocommit: bool = False
    ) -> SyncQueryResult:
        with self._lock:
            self.__check_state(OperationType.EXECUTE, [
                TransactionState.ACTIVE,
                TransactionState.SAVEPOINT,
                TransactionState.READ_ONLY,
                TransactionState.IDLE # Allow queries outside transactions
            ])

            if self.readonly or self.state == TransactionState.READ_ONLY:
                upper_query = query.strip().upper()
                forbidden_keywords = ['INSERT', 'UPDATE', 'DELETE', 'DROP', 
                                    'CREATE', 'ALTER', 'TRUNCATE']
                
                if any(keyword in upper_query for keyword in forbidden_keywords):
                    raise TransactionException(
                        f"Write operation not allowed in read-only transaction: {query[:50]}..."
                    )
            
            if self.autocommit and self.state == TransactionState.IDLE:
                logger.debug("Auto-beginning transaction for autocommit mode")
                self.begin()
            
            logger.debug(f"Executing query: {query[:100]}...")

            try:
                start_time = time.time()

                if many and isinstance(params, list):
                    result = self.__execute_with_retry(
                        self.cursor.executemany, query, params
                    )
                else:
                    result = self.__execute_with_retry(
                        self.cursor.execute, query, params
                    )
                
                duration = time.time() - start_time
                self.stats['queries_executes'] += 1
                self.stats['total_execution_time'] += duration

                if self.timeout and self._start_time:
                    total_duration = time.time() - self._start_time
                    if total_duration > self.timeout:
                        raise TransactionException(f"Transaction timeout after {total_duration:.2f}s")
                
                logger.debug(f"Query executed in {duration:.3f}s")
                return result
                
            except Exception as e:
                logger.error(f"Query execution failed: {query[:50]}... - Error: {e}")
                self.state = TransactionState.FAILED
                raise

    def fetchall(self):
        return self.cursor.fetchall()

    def fetchone(self):
        return self.cursor.fetchone()

    def fetchmany(self, size: int = 1):
        return self.cursor.fetchmany(size)

    def close(self):
        with self._lock:
            if self.state == TransactionState.CLOSED:
                return
            
            logger.debug(f"Closing transaction (state: {self.state.value})")

            if self.is_active:
                try:
                    self.rollback()
                except Exception as e:
                    logger.warning(f"Error during rollback on close: {e}")
            
            self.state = TransactionState.CLOSED
            self._savepoints.clear()
            self._nested_level = 0

    @property
    def cursor(self):
        if self._cursor is None:
            self._cursor = self.connection.cursor()
        return self._cursor

    @property
    def is_active(self):
        return self.state in [
            TransactionState.ACTIVE,
            TransactionState.SAVEPOINT,
            TransactionState.STARTING,
        ]
    
    @property
    def is_readonly(self) -> bool:
        """Check if transaction is read-only."""
        return self.readonly or self.state == TransactionState.READ_ONLY
    
    @property
    def nested_level(self) -> int:
        """Get current nested transaction level."""
        return self._nested_level
    
    @property
    def duration(self) -> Optional[float]:
        """Get transaction duration if active."""
        if self._start_time and self.is_active:
            return time.time() - self._start_time
        return None
    
    @property
    def savepoints(self) -> List[str]:
        """Get list of active savepoint names."""
        return [sp.name for sp in self._savepoints if not sp.is_released]
    
    def get_stats(self) -> Dict[str, Any]:
        """Get transaction statistics."""
        stats = self.stats.copy()
        stats.update({
            'state': self.state.value,
            'nested_level': self._nested_level,
            'is_readonly': self.is_readonly,
            'duration': self.duration,
            'savepoints': self.savepoints,
            'last_operation': self._last_operation.value if self._last_operation else None
        })
        return stats
