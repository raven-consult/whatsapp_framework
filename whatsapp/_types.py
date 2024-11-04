from abc import ABC, abstractmethod
import sqlite3


class BaseInterface(ABC):

    @abstractmethod
    def get_connection(self) -> sqlite3.Connection:
        pass
