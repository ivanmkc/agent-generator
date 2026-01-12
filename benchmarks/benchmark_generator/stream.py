# Copyright 2025 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""
Functional asynchronous stream processing utilities.

This module provides the `AsyncStream` class, which allows for fluent chaining
of asynchronous operations like map, filter, and parallel execution.
"""

import asyncio
from typing import (
    TypeVar,
    Generic,
    AsyncIterator,
    Callable,
    Awaitable,
    List,
    Union,
    Set,
    Any
)

T = TypeVar("T")
U = TypeVar("U")


class AsyncStream(Generic[T]):
    """
    A wrapper around an AsyncIterator that provides functional operators.
    
    This class allows building lazy processing pipelines where operations are
    only executed when the stream is consumed.
    """

    def __init__(self, async_iterator: AsyncIterator[T]):
        """
        Initialize the AsyncStream.

        Args:
            async_iterator: The source async iterator to wrap.
        """
        self._iterator = async_iterator

    def __aiter__(self) -> AsyncIterator[T]:
        return self._iterator

    @classmethod
    def from_iterable(cls, iterable: Union[List[T], AsyncIterator[T]]) -> "AsyncStream[T]":
        """
        Create a stream from a list or existing async iterator.

        Args:
            iterable: A list or async iterator.

        Returns:
            An AsyncStream wrapping the input.
        """
        if isinstance(iterable, list):
            async def _gen():
                for item in iterable:
                    yield item
            return cls(_gen())
        return cls(iterable)

    def map(self, func: Callable[[T], Union[U, Awaitable[U]]]) -> "AsyncStream[U]":
        """
        Transform each item in the stream using a function.

        Args:
            func: A synchronous or asynchronous function to apply to each item.

        Returns:
            A new AsyncStream yielding the transformed items.
        """
        async def _gen() -> AsyncIterator[U]:
            async for item in self._iterator:
                if asyncio.iscoroutinefunction(func):
                    # We know it returns Awaitable[U], but type checker needs help
                    yield await func(item) # type: ignore
                else:
                    yield func(item) # type: ignore
        return AsyncStream(_gen())

    def filter(self, predicate: Callable[[T], Union[bool, Awaitable[bool]]]) -> "AsyncStream[T]":
        """
        Filter items in the stream based on a predicate.

        Args:
            predicate: A function returning True to keep the item, False to drop it.

        Returns:
            A new AsyncStream yielding only items matching the predicate.
        """
        async def _gen() -> AsyncIterator[T]:
            async for item in self._iterator:
                if asyncio.iscoroutinefunction(predicate):
                    if await predicate(item): # type: ignore
                        yield item
                elif predicate(item):
                    yield item
        return AsyncStream(_gen())

    def par_map(self, func: Callable[[T], Awaitable[U]], concurrency: int = 5) -> "AsyncStream[U]":
        """
        Apply an async function to items in parallel.
        
        Note: The order of results is NOT guaranteed to match the input order.
        Results are yielded as soon as they complete to maximize throughput.

        Args:
            func: An asynchronous function to apply to each item.
            concurrency: Maximum number of concurrent tasks.

        Returns:
            A new AsyncStream yielding transformed items.
        """
        async def _gen() -> AsyncIterator[U]:
            pending: Set[asyncio.Task] = set()
            
            # Wrap the function to ensure we catch exceptions or handle them if needed
            # For now, we propagate exceptions which will kill the stream
            
            async for item in self._iterator:
                # If we've reached the concurrency limit, wait for at least one to finish
                if len(pending) >= concurrency:
                    done, pending = await asyncio.wait(pending, return_when=asyncio.FIRST_COMPLETED)
                    for task in done:
                        yield await task
                
                # Schedule new task
                task = asyncio.create_task(func(item))
                pending.add(task)
            
            # Drain remaining tasks
            if pending:
                # Wait for all remaining tasks
                for task in asyncio.as_completed(pending):
                    yield await task

        return AsyncStream(_gen())

    async def collect(self) -> List[T]:
        """
        Consume the entire stream and return a list of results.

        Returns:
            A list containing all items in the stream.
        """
        return [item async for item in self._iterator]

    async def for_each(self, func: Callable[[T], Awaitable[None]]) -> None:
        """
        Consume the stream and apply an async function to each item.
        Useful for side effects (like saving to a file).

        Args:
            func: An async function to execute for each item.
        """
        async for item in self._iterator:
            await func(item)
