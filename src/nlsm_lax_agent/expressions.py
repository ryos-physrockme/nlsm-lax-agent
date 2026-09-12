"""Bounded, non-evaluating reader for exact rational expressions."""

import ast
import io
import re
import tokenize
from dataclasses import dataclass

import sympy as s


class InputError(ValueError):
    def __init__(self, code: str, message: str, path: str = ""):
        super().__init__(message)
        self.code, self.path = code, path

    def as_dict(self):
        return {"code": self.code, "path": self.path, "message": str(self)}


@dataclass
class RationalExpression:
    value: s.Expr
    nonzero: list[s.Expr]


def read_expression(text: str, names: tuple[str, ...] = ("z", "I")) -> RationalExpression:
    if not isinstance(text, str) or not text.strip() or len(text) > 2048:
        raise InputError("INVALID_EXPRESSION", "Expected an expression of 1–2048 characters.")
    symbols = {name: s.I if name == "I" else s.Symbol(name) for name in names}
    nonzero = []
    try:
        for token in tokenize.generate_tokens(io.StringIO(text.strip()).readline):
            if token.type == tokenize.NUMBER and (not re.fullmatch(r"[0-9]+", token.string) or len(token.string) > 32):
                raise InputError("UNSUPPORTED_EXPRESSION", "Use decimal integers and exact fractions.")
            if token.type == tokenize.NAME and token.string not in symbols:
                raise InputError("UNDECLARED_SYMBOL", f"Undeclared symbol: {token.string}")
            if token.type not in {tokenize.NUMBER, tokenize.NAME, tokenize.OP,
                                  tokenize.NEWLINE, tokenize.NL, tokenize.ENDMARKER}:
                raise InputError("UNSUPPORTED_EXPRESSION", "Unsupported token.")
        tree = ast.parse(text.strip(), mode="eval")
    except (SyntaxError, tokenize.TokenError, IndentationError) as exc:
        raise InputError("INVALID_EXPRESSION", "Invalid expression syntax.") from exc
    if sum(1 for _ in ast.walk(tree)) > 256:
        raise InputError("UNSUPPORTED_EXPRESSION", "Expression has too many operations.")

    def require_nonzero(value):
        numerator = s.fraction(s.cancel(value))[0]
        if numerator == 0:
            raise InputError("ZERO_DENOMINATOR", "Division by an identically zero expression.")
        nonzero.append(numerator)

    def walk(node):
        if isinstance(node, ast.Constant) and type(node.value) is int:
            return s.Integer(node.value)
        if isinstance(node, ast.Name):
            return symbols[node.id]
        if isinstance(node, ast.UnaryOp) and isinstance(node.op, (ast.UAdd, ast.USub)):
            return (-1 if isinstance(node.op, ast.USub) else 1) * walk(node.operand)
        if isinstance(node, ast.BinOp):
            a = walk(node.left)
            if isinstance(node.op, ast.Pow):
                exp_node = node.right
                sign = 1
                if isinstance(exp_node, ast.UnaryOp) and isinstance(exp_node.op, (ast.USub, ast.UAdd)):
                    sign = -1 if isinstance(exp_node.op, ast.USub) else 1
                    exp_node = exp_node.operand
                if not isinstance(exp_node, ast.Constant) or type(exp_node.value) is not int:
                    raise InputError("UNSUPPORTED_EXPRESSION", "Exponent must be an integer literal.")
                exponent = sign * exp_node.value
                if abs(exponent) > 16:
                    raise InputError("UNSUPPORTED_EXPRESSION", "Absolute exponent exceeds 16.")
                if exponent < 0:
                    require_nonzero(a)
                return a ** exponent
            b = walk(node.right)
            if isinstance(node.op, ast.Add):
                return a + b
            if isinstance(node.op, ast.Sub):
                return a - b
            if isinstance(node.op, ast.Mult):
                return a * b
            if isinstance(node.op, ast.Div):
                require_nonzero(b)
                return a / b
        raise InputError("UNSUPPORTED_EXPRESSION", "Only exact rational arithmetic is supported.")

    return RationalExpression(s.cancel(walk(tree.body)), nonzero)


def polynomial(expr: s.Expr, symbol: s.Symbol) -> s.Poly:
    try:
        return s.Poly(expr, symbol, extension=s.I)
    except (s.PolynomialError, s.CoercionFailed) as exc:
        raise InputError("INVALID_SPECTRAL_DOMAIN", "Expected a polynomial over the Gaussian rationals.") from exc


def spectral_domain(exclusions: list[str], expressions: list[RationalExpression]) -> list[str]:
    z = s.Symbol("z")
    polys, all_expr = [], list(expressions)
    for text in exclusions:
        parsed = read_expression(text)
        p = polynomial(parsed.value, z)
        if p.is_zero:
            raise InputError("INVALID_SPECTRAL_DOMAIN", "The spectral domain must be nonempty.")
        polys.append(p.sqf_part().monic())
        all_expr.append(parsed)
    product = polynomial(s.prod(p.as_expr() for p in polys), z).sqf_part()
    for expr in all_expr:
        for condition in expr.nonzero + [s.denom(expr.value)]:
            p = polynomial(condition, z).sqf_part()
            if not product.rem(p).is_zero:
                raise InputError("UNDECLARED_SINGULARITY", f"Exclude the zeros of {p.as_expr()}.")
    return sorted({str(p.as_expr()) for p in polys if p.degree() > 0})
