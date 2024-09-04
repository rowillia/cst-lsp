import difflib

from pathlib import Path
import sys
import libcst
from libcst.metadata import CodePosition, CodeRange
from lsprotocol import types as lsp
from pygls.server import LanguageServer

from cst_lsp.code_actions.base import BaseCstLspCodeAction
from cst_lsp.code_actions.extract_method import ExtractMethod
from cst_lsp.code_actions.import_symbol import ImportAll, ImportSymbol
from cst_lsp.symbols.symbol_finder import SymbolFinder


def string_diff_to_text_edits(original: str, modified: str) -> list[lsp.TextEdit]:
    """
    Convert the difference between two strings into a list of LSP TextEdit objects.

    Args:
    text1 (str): The original text.
    text2 (str): The modified text.

    Returns:
    List[lsp.TextEdit]: A list of TextEdit objects representing the changes.
    """
    original_lines = original.splitlines()
    modified_lines = modified.splitlines()

    matcher = difflib.SequenceMatcher(None, original_lines, modified_lines)

    text_edits = {}

    for op, i1, i2, j1, j2 in matcher.get_opcodes():
        if op == "replace":
            # Handle replacements
            new_text = "\n".join(modified_lines[j1:j2])
            text_edits[i1] = lsp.TextEdit(
                range=lsp.Range(
                    start=lsp.Position(i1, 0),
                    end=lsp.Position(i2 - 1, len(original_lines[i2 - 1])),
                ),
                new_text=new_text,
            )
        elif op == "insert":
            # Handle insertions
            insert_at_line = i1
            new_text = "\n".join(modified_lines[j1:j2]) + "\n"
            if insert_at_line in text_edits:
                # Append to existing edit if there's one for this line
                text_edits[insert_at_line].new_text += new_text
            else:
                text_edits[insert_at_line] = lsp.TextEdit(
                    range=lsp.Range(
                        start=lsp.Position(insert_at_line, 0),
                        end=lsp.Position(insert_at_line, 0),
                    ),
                    new_text=new_text,
                )
        elif op == "delete":
            # Handle deletions
            text_edits[i1] = lsp.TextEdit(
                range=lsp.Range(
                    start=lsp.Position(i1, 0),
                    end=lsp.Position(i2, len(original_lines[i2 - 1])),
                ),
                new_text="",
            )

    # Convert the dictionary to a list of TextEdits
    result = list(text_edits.values())
    return result


class CstLspServer(LanguageServer):
    def __init__(self):
        super().__init__("cst-lsp-server", "v0.1")
        self.transformations: list[BaseCstLspCodeAction] = []

    async def initialize(self, params: lsp.InitializeParams):
        self.transformations = [ExtractMethod()]
        if params.root_uri:
            root_path = Path(params.root_uri.replace("file://", ""))
            # TODO: Make `python_path` configurable.
            symbol_finder = SymbolFinder.create(Path(sys.executable), Path(root_path))
            if symbol_finder:
                self.transformations.append(ImportSymbol(symbol_finder))
                self.transformations.append(ImportAll(symbol_finder))

    async def code_action_handler(
        self, params: lsp.CodeActionParams
    ) -> list[lsp.CodeAction] | None:
        document = self.workspace.get_document(params.text_document.uri)
        start, end = params.range.start, params.range.end

        code_actions = []
        module = libcst.parse_module(document.source)
        code_range = CodeRange(
            CodePosition(start.line + 1, start.character),
            CodePosition(end.line + 1, end.character),
        )
        for transformation in self.transformations:
            if not transformation.is_valid(document.source, module, code_range):
                continue
            try:
                result = transformation.refactor(module, code_range)
                if not result or result == document.source:
                    continue
                edits = string_diff_to_text_edits(document.source, result)
            except Exception:
                continue

            code_actions.append(
                lsp.CodeAction(
                    title=f"{transformation.name}",
                    kind=lsp.CodeActionKind.RefactorExtract,
                    edit=lsp.WorkspaceEdit(changes={params.text_document.uri: edits}),
                )
            )

        return code_actions if code_actions else None


server = CstLspServer()


@server.feature(lsp.TEXT_DOCUMENT_CODE_ACTION)
async def code_action(params: lsp.CodeActionParams) -> list[lsp.CodeAction] | None:
    return await server.code_action_handler(params)


@server.feature(lsp.INITIALIZE)
async def initialize(params: lsp.InitializeParams):
    return await server.initialize(params)


def main():
    server.start_io()


if __name__ == "__main__":
    main()
