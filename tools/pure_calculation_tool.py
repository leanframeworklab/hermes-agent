"""Bounded, side-effect-free arithmetic capability for Ling3 level-zero work."""

from __future__ import annotations

import ast
import operator
from typing import Any

from tools.registry import registry


_BINOPS = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.FloorDiv: operator.floordiv,
    ast.Mod: operator.mod,
    ast.Pow: operator.pow,
}
_UNARYOPS = {ast.UAdd: operator.pos, ast.USub: operator.neg}
_LIMITS = {"cpu_operations": 100, "memory_bytes": 131072, "output_chars": 4096, "wall_time_ms": 2000}


class PureCalculationError(ValueError):
    """Calculation is outside the certified pure subset or resource bounds."""


def _validate_limits(limits: Any) -> None:
    if limits != _LIMITS:
        raise PureCalculationError("pure calculation limits are not certified")


def _eval(node: ast.AST, count: list[int], depth: int = 0) -> Any:
    count[0] += 1
    if count[0] > _LIMITS["cpu_operations"] or depth > 20:
        raise PureCalculationError("pure calculation operation bound exceeded")
    if isinstance(node, ast.Expression):
        return _eval(node.body, count, depth + 1)
    if isinstance(node, ast.Constant) and isinstance(node.value, (int, float, complex)):
        if len(repr(node.value)) > 100:
            raise PureCalculationError("numeric constant bound exceeded")
        return node.value
    if isinstance(node, ast.UnaryOp) and type(node.op) in _UNARYOPS:
        return _UNARYOPS[type(node.op)](_eval(node.operand, count, depth + 1))
    if isinstance(node, ast.BinOp) and type(node.op) in _BINOPS:
        left = _eval(node.left, count, depth + 1)
        right = _eval(node.right, count, depth + 1)
        if isinstance(node.op, ast.Pow) and abs(right) > 100:
            raise PureCalculationError("exponent bound exceeded")
        value = _BINOPS[type(node.op)](left, right)
        if len(repr(value)) > _LIMITS["output_chars"]:
            raise PureCalculationError("pure calculation output bound exceeded")
        return value
    raise PureCalculationError("expression contains non-pure syntax")


def pure_calculation(code: str, limits: dict[str, int]) -> dict[str, Any]:
    _validate_limits(limits)
    if not isinstance(code, str) or len(code) > 4096:
        raise PureCalculationError("calculation input bound exceeded")
    try:
        tree = ast.parse(code, mode="eval")
        value = _eval(tree, [0])
    except (SyntaxError, ZeroDivisionError, OverflowError, ValueError, TypeError) as exc:
        if isinstance(exc, PureCalculationError):
            raise
        raise PureCalculationError(str(exc)) from exc
    return {"value": value, "operations": "bounded", "side_effect_level": 0}


registry.register(
    name="pure_calculation",
    toolset="safe_local",
    schema={
        "name": "pure_calculation",
        "description": "Evaluate one bounded arithmetic expression without filesystem, network, process, or environment access.",
        "parameters": {
            "type": "object",
            "properties": {
                "code": {"type": "string"},
                "sandbox_profile": {"type": "string", "const": "pure_calculation_v1"},
                "limits": {"type": "object"},
            },
            "required": ["code", "sandbox_profile", "limits"],
        },
    },
    handler=lambda args, **_: pure_calculation(args.get("code", ""), args.get("limits", {})),
    emoji="∑",
    max_result_size_chars=4096,
)
