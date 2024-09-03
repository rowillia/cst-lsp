import textwrap
from abc import ABC, abstractmethod
from typing import ClassVar

import libcst as cst
from libcst.metadata import CodeRange
from lsprotocol.types import CodeActionKind


def code_ranges_interect(first: CodeRange, second: CodeRange):
    overlap_start_line = max(first.start.line, second.start.line)
    overlap_end_line = min(first.end.line, second.end.line)
    if overlap_start_line > overlap_end_line:
        return False
    if first.start.line == first.end.line and second.start.line == second.end.line:
        overlap_start_column = max(first.start.column, second.start.column)
        overlap_end_column = min(first.end.column, second.end.column)
        if overlap_start_column > overlap_end_column:
            return False
    return True


class BaseCstLspCodeAction(ABC):
    name: ClassVar[str]
    kind: ClassVar[CodeActionKind]

    def is_valid(self, source: str, module: cst.Module, code_range: CodeRange) -> bool:
        lines = source.splitlines()
        dedented = textwrap.dedent(
            "\n".join(lines[code_range.start.line - 1 : code_range.end.line])
        )
        try:
            cst.parse_module(dedented)
            return True
        except Exception:
            return False

    @abstractmethod
    def refactor(self, module: cst.Module, code_range: CodeRange) -> str | None:
        pass
