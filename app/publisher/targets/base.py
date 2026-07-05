from abc import ABC, abstractmethod
from pathlib import Path

class BasePublisherTarget(ABC):
    @abstractmethod
    def generate(self, bundle: dict, output_dir: Path) -> None:
        pass

    @abstractmethod
    def validate(self, output_dir: Path) -> dict:
        pass
