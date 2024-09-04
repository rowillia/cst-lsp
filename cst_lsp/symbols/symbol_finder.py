from abc import ABC, abstractmethod
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
import functools
import subprocess
import json
import re

IMPORT_PATTERN = re.compile(r"import\s+(\w+)(?:\s+as\s+(\w+))?")


@dataclass(frozen=True)
class SuggestedImport:
    module: str
    symbol: str | None
    alias: str | None


@dataclass(frozen=True)
class SymbolFinder(ABC):
    python_path: Path
    root: Path

    @abstractmethod
    def find_symbol(self, symbol: str) -> list[SuggestedImport]:
        pass

    @functools.lru_cache(maxsize=None)
    def paths(self) -> list[Path]:
        result = subprocess.run(
            [str(self.python_path), "-c", r'import sys; print("\n".join(sys.path))'],
            capture_output=True,
            text=True,
            check=True,
        )
        return [Path(x) for x in result.stdout.splitlines() if x.strip()]

    @classmethod
    def create(cls, python_path: Path, root: Path) -> "SymbolFinder | None":
        try:
            subprocess.run(["rg", "--version"], check=True, capture_output=True)
            return RipGrepSymbolFinder(python_path, root)
        except (subprocess.CalledProcessError, FileNotFoundError):
            return None


class RipGrepSymbolFinder(SymbolFinder):
    """
    A symbol finder that uses ripgrep to search for symbols in Python files.

    This class extends the SymbolFinder abstract base class and implements
    methods to find symbols using the ripgrep command-line tool. It can
    search for existing imports, symbols in __all__ declarations, and
    top-level class or function definitions.
    """

    def _ripgrep_generator(
        self, pattern: str, root: Path, glob: str = "*.py", max_hits: int = 25
    ):
        cmd = [
            "rg",
            "-m1",
            "-g",
            glob,
            "--no-ignore",
            "--multiline",
            pattern,
            str(root),
            "--json",
        ]
        if (root / "site-packages").is_dir():
            # Avoid crawling `site-packages` from it's parent since it won't
            # be valid to import from the parent anyway.
            cmd.extend(["-g", "!{**/site-packages/*}"])
        with subprocess.Popen(
            cmd, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE
        ) as process:
            if not process.stdout:
                return
            hits = 0
            for line in process.stdout:
                try:
                    data = json.loads(line)
                    if (
                        "data" in data
                        and "lines" in data["data"]
                        and "path" in data["data"]
                    ):
                        line: str = data["data"]["lines"]["text"].strip()
                        path: str = data["data"]["path"]["text"].strip()
                        yield path, line
                        hits += 1
                    if hits >= max_hits:
                        return
                except json.JSONDecodeError:
                    continue

    @functools.lru_cache(maxsize=None)
    def find_existing_imports(self, symbol: str) -> list[SuggestedImport]:
        """
        Find existing imports of the given symbol in the project.

        This method searches for import statements that import the specified symbol,
        either directly or as an alias. It handles both 'import' and 'from ... import' statements.

        Args:
            symbol (str): The symbol to search for in import statements.

        Returns:
            list[SuggestedImport]: A list of SuggestedImport objects, where each object contains:
                - The module from which the symbol is imported
                - The original name of the symbol (if using 'from ... import')
                - The alias of the symbol (if an alias is used)
            The list is sorted by frequency of occurrence, with the most common imports first.
        """
        pattern = rf"import\s+(?:\(\s*(?:\w+,\s*)*)?(?:(?:\w+\s+as\s+))?{symbol}(?:,|\s+|\)|$)"
        imports = []
        for _, line in self._ripgrep_generator(pattern, self.root):
            if line.startswith("from"):
                if match := re.search(
                    rf"from\s+(\w+)\s+import.*[,\s]+(\w+)\s+as\s+({symbol})", line
                ):
                    imports.append(
                        SuggestedImport(match.group(1), match.group(2), match.group(3))
                    )
                else:
                    imports.append(SuggestedImport(line.split()[1], symbol, None))
            elif match := re.search(IMPORT_PATTERN, line):
                module, alias = match.groups()
                imports.append(
                    SuggestedImport(module, None, alias if alias == symbol else None)
                )
        counter = Counter(imports)
        sorted_imports = sorted(counter.items(), key=lambda x: x[1], reverse=True)
        return [item[0] for item in sorted_imports]

    @functools.lru_cache(maxsize=None)
    def find_symbol_from_all(self, symbol: str) -> list[SuggestedImport]:
        """
        Search for the given symbol in __all__ declarations within __init__.py files.

        Modules add symbols to their `__all__` in their `__init__.py` to make importing
        those symbols easier.  It's also much faster to check these first before doing
        a full scan.

        Args:
            symbol (str): The symbol to search for in __all__ declarations.

        Returns:
            list[SuggestedImport]: A list of SuggestedImport objects containing:
                - The module path where the symbol was found in __all__
                - The symbol itself
                - None (as no alias is used in __all__ declarations)
        """
        return self._find_pattern_in_files(
            symbol,
            f"__all__\\s*=\\s*(?:\\(|\\[)(?s:.)*[\"']{symbol}[\"']",
            glob="__init__.py",
            use_parent=True,
        )

    @functools.lru_cache(maxsize=None)
    def find_top_level_symbol(self, symbol: str) -> list[SuggestedImport]:
        """
        Search for top-level class or function definitions of the given symbol.

        This method looks for class or function definitions that match the provided symbol
        at the top level of Python files.

        Args:
            symbol (str): The symbol to search for in top-level definitions.

        Returns:
            list[SuggestedImport]: A list of SuggestedImport objects containing:
                - The module path where the symbol was found
                - The symbol itself
                - None (as no alias is used in top-level definitions)
        """
        return self._find_pattern_in_files(symbol, rf"(?:class|def)\s+{symbol}(?:\(|:)")

    def _find_pattern_in_files(
        self, symbol: str, pattern: str, glob: str = "*.py", use_parent: bool = False
    ) -> list[SuggestedImport]:
        matches = []
        for root in self.paths():
            if not root.is_dir():
                continue
            for path, _ in self._ripgrep_generator(pattern, root=root, glob=glob):
                relative_path = Path(path).relative_to(root)
                if use_parent:
                    relative_path = relative_path.parent
                module_path = str(relative_path.with_suffix("")).replace("/", ".")
                if all(part.isidentifier() for part in module_path.split(".")):
                    matches.append(SuggestedImport(module_path, symbol, None))
        return matches

    def find_symbol(self, symbol: str) -> list[SuggestedImport]:
        return (
            self.find_existing_imports(symbol)
            or self.find_symbol_from_all(symbol)
            or self.find_top_level_symbol(symbol)
        )
