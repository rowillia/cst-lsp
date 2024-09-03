import sys
from pathlib import Path
import pytest
from cst_lsp.symbols.symbol_finder import RipGrepSymbolFinder, SuggestedImport


@pytest.fixture
def symbol_finder():
    return RipGrepSymbolFinder(python_path=Path(sys.executable), root=Path.cwd())


def test_find_existing_imports(symbol_finder: RipGrepSymbolFinder):
    print(symbol_finder.root)
    result = symbol_finder.find_existing_imports("pytest")
    assert len(result) > 0
    assert any("pytest" == item.module for item in result)


def test_find_symbol_from_all(symbol_finder: RipGrepSymbolFinder):
    result = symbol_finder.find_symbol_from_all("AugAssign")
    assert len(result) > 0
    assert any("libcst" == item.module for item in result)


def test_find_top_level_symbol(symbol_finder: RipGrepSymbolFinder):
    result = symbol_finder.find_top_level_symbol("BaseMetadataProvider")
    assert len(result) > 0
    assert any("libcst.metadata.base_provider" == item.module for item in result)


def test_find_symbol(symbol_finder: RipGrepSymbolFinder):
    result = symbol_finder.find_symbol("cst")
    assert len(result) > 0
    assert any(SuggestedImport("libcst", None, "cst") == item for item in result)
