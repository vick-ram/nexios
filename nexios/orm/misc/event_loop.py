from __future__ import annotations

import atexit
import concurrent.futures
from dataclasses import dataclass
from enum import Enum
import os
import platform
import asyncio
import sys
import threading
from typing import Any, Coroutine, List, Optional, TypeVar, Union

import concurrent
import warnings

T = TypeVar("T")

PYTHON_VERSION = sys.version_info
PYTHON_311_PLUS = PYTHON_VERSION.major > 3 or (
    PYTHON_VERSION.major == 3 and PYTHON_VERSION.minor >= 11
)
IS_WINDOWS = platform.system() == "Windows"

USING_UVLOOP = False
if not IS_WINDOWS:
    try:
        import uvloop

        if not IS_WINDOWS:
            loop = uvloop.new_event_loop()
            asyncio.set_event_loop(loop)
            USING_UVLOOP = True
    except ImportError:
        pass


class LoopBackend(Enum):
    ASYNCIO = "asyncio"
    UVLOOP = "uvloop"

    @classmethod
    def get_available(cls) -> LoopBackend:
        if USING_UVLOOP and not IS_WINDOWS:
            return cls.UVLOOP
        return cls.ASYNCIO


@dataclass
class ExecutionResult:
    success: bool
    result: Any = None
    exception: Optional[Exception] = None

    @property
    def value(self):
        if not self.success and self.exception:
            raise self.exception
        return self.result


class NexiosEventLoop:
    _instance: Optional[NexiosEventLoop] = None
    _lock = threading.Lock()

    def __new__(cls):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super().__new__(cls)
                cls._instance._initialized = False
            return cls._instance

    def __init__(
        self,
        backend: Optional[LoopBackend] = None,
        max_workers: Optional[int] = None,
        enable_thread_pool: bool = False,
    ) -> None:
        if getattr(self, "_initialized", False):
            return

        self.backend = backend or LoopBackend.get_available()
        self._loop: Optional[asyncio.AbstractEventLoop] = None
        self._thread: Optional[threading.Thread] = None
        self._ready_event = threading.Event()
        self._shutdown_event = threading.Event()
        self._initialized = True
        self._thread_pool: Optional[concurrent.futures.ThreadPoolExecutor] = None

        if enable_thread_pool:
            self._thread_pool = concurrent.futures.ThreadPoolExecutor(
                max_workers=max_workers or (os.cpu_count() or 4) * 5,
                thread_name_prefix="NexiosEventLoop_Pool",
            )
        self._start_background_loop()
        atexit.register(self.stop)

    def _start_background_loop(self):
        def run_loop():
            try:
                if self.backend == LoopBackend.UVLOOP and USING_UVLOOP:
                    import uvloop

                    self._loop = uvloop.new_event_loop()
                else:
                    self._loop = asyncio.new_event_loop()

                asyncio.set_event_loop(self._loop)

                if self._loop and self._thread_pool:
                    self._loop.set_default_executor(self._thread_pool)

                self._ready_event.set()

                # while not self._shutdown_event.is_set():
                #     if self._loop is not None:
                #         self._loop.run_until_complete(asyncio.sleep(0.1))
                self._loop.run_forever()
            except Exception as e:
                warnings.warn(f"Event loop crushed: {e}")
            finally:
                if self._loop and not self._loop.is_closed():
                    pending = asyncio.all_tasks(self._loop)
                    for task in pending:
                        task.cancel()

                    if pending:
                        self._loop.run_until_complete(
                            asyncio.gather(*pending, return_exceptions=True)
                        )

                    self._loop.close()

        self._thread = threading.Thread(
            target=run_loop, daemon=True, name=f"NexiosEventLoop-{self.backend.value}"
        )
        self._thread.start()

        if not self._ready_event.wait(timeout=10.0):
            raise RuntimeError("Failed to start event loop with timeout")

    def run(self, coro: Coroutine[Any, Any, T], timeout: Optional[float] = None) -> T:
        if PYTHON_311_PLUS and self._loop is None:
            with asyncio.Runner() as runner:
                return runner.run(coro)

        if self._loop is None or self._loop.is_closed():
            raise RuntimeError("Event loop is not running")

        future = asyncio.run_coroutine_threadsafe(coro, self._loop)

        try:
            return future.result(timeout=timeout)
        except concurrent.futures.TimeoutError:
            future.cancel()
            raise TimeoutError(f"Operation timeouted out after {timeout} seconds")
        except KeyboardInterrupt:
            future.cancel()
            raise
        except Exception as e:
            raise e

    def run_multiple(
        self,
        coros: List[Coroutine[Any, Any, T]],
        timeout: Optional[float] = None,
        return_exceptions: bool = False,
    ) -> List[Union[T, BaseException]]:
        
        if not coros:
            return []
        
        if PYTHON_311_PLUS and self._loop is None:
            with asyncio.Runner() as runner:
                async def gather_wrapper():
                    tasks = [asyncio.create_task(coro) for coro in coros]
                    return await asyncio.gather(*tasks, return_exceptions=return_exceptions)
            
            return runner.run(gather_wrapper())

        async def gather_coros():
            tasks = [self._create_task(coro) for coro in coros]
            return await asyncio.gather(*tasks, return_exceptions=return_exceptions)
        assert self._loop is not None
        future = asyncio.run_coroutine_threadsafe(gather_coros(), self._loop)

        try:
            return future.result(timeout=timeout)
        except concurrent.futures.TimeoutError:
            future.cancel()
            raise TimeoutError(f"Operation timeouted out after {timeout} seconds")

    def run_batch(
        self,
        coros: List[Coroutine[Any, Any, T]],
        batch_size: int = 10,
        timeout_per_batch: Optional[float] = None,
    ) -> List[ExecutionResult]:
        results: List[ExecutionResult] = []
        for i in range(0, len(coros), batch_size):
            batch = coros[i : i + batch_size]
            batch_results = self.run_multiple(
                batch, timeout=timeout_per_batch, return_exceptions=True
            )
            for j, result in enumerate(batch_results):
                if isinstance(result, Exception):
                    results.append(ExecutionResult(success=False, exception=result))
                else:
                    results.append(ExecutionResult(success=True, result=result))
        return results
    
    def stop(self, timeout: float = 5.0):
        if not self._initialized:
            return
        
        self._shutdown_event.set()

        if self._thread_pool:
            self._thread_pool.shutdown(wait=False, cancel_futures=True)
        
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=timeout)
        
            if self._thread.is_alive():
                warnings.warn("NexiosEventLoop runner thread did not terminate gracefully")

        self._initialized = False
        NexiosEventLoop._instance = None
    
    def _create_task(self, coro: Coroutine[Any, Any, T]) -> asyncio.Task[T]:
        if self._loop and not self._loop.is_closed():
            return self._loop.create_task(coro)
        else:
            return asyncio.create_task(coro)
    
    def __del__(self):
        self.stop()
