"""Guard: codebase requires Python >= 3.14.

Two assertions:
1. sys.version_info — fail sớm nếu ai chạy bằng Python < 3.14.
2. Runtime PEP 604 unions (X | Y) — chứng minh codebase đang trên
   floor cho phép syntax này (3.9 không có).
"""
from __future__ import annotations

import sys


def test_python_floor_is_at_least_3_14():
    assert sys.version_info >= (3, 14), (
        f"agent-system requires Python >= 3.14, "
        f"running {sys.version_info.major}.{sys.version_info.minor}"
    )


def test_pep604_union_runtime_supported():
    # PEP 604 (X | Y) — 3.10+; trên 3.14 chắc chắn OK.
    x: int | str = 5
    assert isinstance(x, int)
    y: None | float = None
    assert y is None


def test_typing_modern_collections_available():
    # codebase giờ dùng list[X] / dict[X] (không còn typing.List/Dict)
    # — đảm bảo built-in generics hoạt động.
    a: list[int] = [1, 2, 3]
    b: dict[str, int] = {"x": 1}
    assert sum(a) == 6
    assert b["x"] == 1
