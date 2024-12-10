# CST-LSP

Supports refactoring with `libcst` via a LSP Server.

## Installation

```bash
# Install from source with development dependencies
uv pip install -e ".[dev]"
```

## Features

- Code refactoring via Language Server Protocol (LSP)
- Built on `libcst` for reliable Python code transformations
- Supports method extraction and symbol management

## Development

To run linting and type checking:
```bash
uv run ruff check .
uv run pyright .
```
