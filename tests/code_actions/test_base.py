from libcst.metadata import CodeRange, CodePosition

from cst_lsp.code_actions.base import code_ranges_interect


import pytest


@pytest.mark.parametrize(
    "range1, range2, expected",
    [
        # Test case 1: Ranges overlap
        (
            CodeRange(
                start=CodePosition(line=1, column=0), end=CodePosition(line=3, column=0)
            ),
            CodeRange(
                start=CodePosition(line=2, column=0), end=CodePosition(line=4, column=0)
            ),
            True,
        ),
        # Test case 2: Ranges touch at a point
        (
            CodeRange(
                start=CodePosition(line=1, column=0), end=CodePosition(line=2, column=0)
            ),
            CodeRange(
                start=CodePosition(line=2, column=0), end=CodePosition(line=3, column=0)
            ),
            True,
        ),
        # Test case 3: One range entirely within another
        (
            CodeRange(
                start=CodePosition(line=1, column=0), end=CodePosition(line=5, column=0)
            ),
            CodeRange(
                start=CodePosition(line=2, column=0), end=CodePosition(line=3, column=0)
            ),
            True,
        ),
        # Test case 4: Ranges do not intersect
        (
            CodeRange(
                start=CodePosition(line=1, column=0), end=CodePosition(line=2, column=0)
            ),
            CodeRange(
                start=CodePosition(line=3, column=0), end=CodePosition(line=4, column=0)
            ),
            False,
        ),
        # Test case 5: Ranges are the same
        (
            CodeRange(
                start=CodePosition(line=1, column=0), end=CodePosition(line=2, column=0)
            ),
            CodeRange(
                start=CodePosition(line=1, column=0), end=CodePosition(line=2, column=0)
            ),
            True,
        ),
        # Test case 6: Ranges overlap in columns
        (
            CodeRange(
                start=CodePosition(line=1, column=0),
                end=CodePosition(line=1, column=10),
            ),
            CodeRange(
                start=CodePosition(line=1, column=5),
                end=CodePosition(line=1, column=15),
            ),
            True,
        ),
        # Test case 7: Ranges touch at a column
        (
            CodeRange(
                start=CodePosition(line=1, column=0), end=CodePosition(line=1, column=5)
            ),
            CodeRange(
                start=CodePosition(line=1, column=5),
                end=CodePosition(line=1, column=10),
            ),
            True,
        ),
        # Test case 8: One range entirely within another in columns
        (
            CodeRange(
                start=CodePosition(line=1, column=0),
                end=CodePosition(line=1, column=20),
            ),
            CodeRange(
                start=CodePosition(line=1, column=5),
                end=CodePosition(line=1, column=15),
            ),
            True,
        ),
        # Test case 9: Ranges do not intersect in columns
        (
            CodeRange(
                start=CodePosition(line=1, column=0), end=CodePosition(line=1, column=5)
            ),
            CodeRange(
                start=CodePosition(line=1, column=10),
                end=CodePosition(line=1, column=15),
            ),
            False,
        ),
    ],
)
def test_code_ranges_intersect(range1, range2, expected):
    assert code_ranges_interect(range1, range2) == expected
