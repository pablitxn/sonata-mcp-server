"""
Using Protocol for structural subtyping
PEP 544 - Inspired by TypeScript interfaces
"""
from typing import Protocol, runtime_checkable, Dict, Any


@runtime_checkable
class BrowserPageProtocol(Protocol):
    """
    Protocol defining what a browser page should implement
    Duck typing with static type checking!
    """

    async def goto(self, url: str, wait_until: str = "load") -> None: ...

    async def click(self, selector: str) -> None: ...

    async def fill(self, selector: str, value: str) -> None: ...

    async def evaluate(self, script: str) -> Any: ...

    async def screenshot(self, path: str = None) -> bytes: ...

    async def content(self) -> str: ...


# Usage example:
def process_page(page: BrowserPageProtocol) -> None:
    """Any object that implements the protocol methods can be used"""
    # Type checker will verify the object has required methods
    pass
