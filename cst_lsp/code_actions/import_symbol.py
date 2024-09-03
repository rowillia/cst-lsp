import libcst as cst
from libcst.metadata import CodeRange, PositionProvider, ScopeProvider, MetadataWrapper
from lsprotocol import types as lsp_types
from libcst.codemod.visitors import AddImportsVisitor

from cst_lsp.symbols.symbol_finder import SymbolFinder
from .base import BaseCstLspCodeAction, code_ranges_interect

from libcst.codemod import CodemodContext


class NameAtLocationVisitor(cst.CSTVisitor):
    METADATA_DEPENDENCIES = (PositionProvider,)

    def __init__(self, target_location: CodeRange):
        self.target_location = target_location
        self.name = None

    def visit_Name(self, node: cst.Name) -> None:
        position = self.get_metadata(PositionProvider, node)
        assert isinstance(position, CodeRange)
        if code_ranges_interect(position, self.target_location):
            self.name = node.value


def get_name_at_location(module: cst.Module, location: CodeRange) -> str | None:
    wrapper = MetadataWrapper(module)
    visitor = NameAtLocationVisitor(location)
    wrapper.visit(visitor)
    return visitor.name


class ImportSymbol(BaseCstLspCodeAction):
    name = "Import Symbol"
    kind = lsp_types.CodeActionKind.RefactorExtract

    def __init__(self, symbol_finder: SymbolFinder) -> None:
        super().__init__()
        self.symbol_finder = symbol_finder

    def is_valid(
        self,
        source: str,
        module: cst.Module,
        code_range: CodeRange,
    ) -> bool:
        """
        Check if the refactor is valid for the given code range.

        This method allows the refactor to fire if the name that's currently
        selected isn't defined in the current scope.
        """
        wrapper = MetadataWrapper(module)
        scopes = set(wrapper.resolve(ScopeProvider).values())
        ranges = wrapper.resolve(PositionProvider)
        for scope in scopes:
            if not scope:
                continue
            for access in scope.accesses:
                if len(access.referents) == 0:
                    node = access.node
                    location = ranges[node]
                    if code_ranges_interect(location, code_range):
                        return True
        return False

    def refactor(
        self,
        module: cst.Module,
        code_range: CodeRange,
    ) -> str | None:
        wrapper = cst.MetadataWrapper(module)
        context = CodemodContext()
        symbol = get_name_at_location(module, code_range)
        if symbol is None:
            return module.code
        matching_imports = self.symbol_finder.find_symbol(symbol)
        if not matching_imports:
            return None
        suggested_import = matching_imports[0]
        AddImportsVisitor.add_needed_import(
            context,
            suggested_import.module,
            suggested_import.symbol,
            suggested_import.alias,
        )
        result = wrapper.visit(AddImportsVisitor(context))
        return result.code
