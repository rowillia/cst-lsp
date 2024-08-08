import textwrap
from abc import ABC, abstractmethod
from typing import ClassVar

import libcst as cst
from lsprotocol.types import CodeActionKind, Position


class BaseCstLspCodeAction(ABC):
    name: ClassVar[str]
    kind: ClassVar[CodeActionKind]

    def is_valid(self, source: str, start: Position, end: Position) -> bool:
        lines = source.splitlines()
        dedented = textwrap.dedent("\n".join(lines[start.line : end.line + 1]))
        try:
            cst.parse_module(dedented)
            return True
        except Exception:
            return False

    @abstractmethod
    def refactor(
        self, module: cst.Module, start: Position, end: Position
    ) -> str | None:
        pass
