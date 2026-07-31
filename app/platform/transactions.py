"""Unit-of-work boundary to be implemented by database adapters later."""
from abc import ABC, abstractmethod

class UnitOfWork(ABC):
    @abstractmethod
    def commit(self) -> None: ...
    @abstractmethod
    def rollback(self) -> None: ...
    def __enter__(self): return self
    def __exit__(self, error_type, error, traceback):
        self.rollback() if error else self.commit()
