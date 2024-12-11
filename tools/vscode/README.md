# CST LSP VSCode Extension

VSCode extension for Python code transformations using libcst. This extension provides advanced code refactoring capabilities powered by the CST LSP language server.

## Features

- **Extract Method Refactoring**: Select code and extract it into a new method, automatically handling:
  - Variable scope analysis
  - Return value detection
  - Method parameter ordering
  - Class method context preservation

- **Symbol Management**:
  - Import missing symbols automatically
  - Import all undefined symbols in a file
  - Smart import suggestions based on available symbols

## Requirements

- Python 3.10 or higher
- CST LSP package (`pip install cst-lsp`)
- Visual Studio Code version 1.85.0 or higher

## Extension Settings

This extension contributes the following settings:

* `cstLsp.pythonPath`: Path to Python interpreter (default: "python")
* `cstLsp.trace.server`: Trace communication between VS Code and the language server
  - "off": Disable tracing
  - "messages": Log messages between client and server
  - "verbose": Detailed logging for debugging

## Usage

1. Install the CST LSP package:
   ```bash
   pip install cst-lsp
   ```

2. Open any Python file in VSCode

3. Use the command palette (Ctrl+Shift+P) to access:
   - "CST LSP: Extract Method"
   - "CST LSP: Import Symbol"

4. For method extraction:
   - Select the code you want to extract
   - Use the command palette or context menu
   - Enter the new method name when prompted

5. For symbol importing:
   - Place cursor on undefined symbol
   - Use the command palette or quick fix (Ctrl+.)
   - Select from available import suggestions

## Known Issues

- The extension requires the cst-lsp Python package to be installed in the active Python environment
- Method extraction may require manual adjustment for complex control flow

## Release Notes

### 0.0.1

Initial release of CST LSP VSCode Extension:
- Extract Method refactoring support
- Import Symbol management
- Basic LSP integration
