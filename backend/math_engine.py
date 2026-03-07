"""
Safe evaluation of numeric expressions. Only allows numbers and +, -, *, /, (, ).
No eval() of arbitrary code.
"""
import re
import operator

_OPS = {
    "+": operator.add,
    "-": operator.sub,
    "*": operator.mul,
    "/": operator.truediv,
}


def solve(expression):
    if not expression or not isinstance(expression, str):
        return None
    expr = expression.strip()
    if not expr:
        return None
    # Allow only digits, spaces, and + - * / ( )
    if not re.fullmatch(r"[\d\s+\-*/().]+", expr):
        return None
    try:
        return _eval_expr(_tokenize(expr))
    except (ValueError, ZeroDivisionError, IndexError):
        return None


def _tokenize(s):
    s = s.replace(" ", "")
    tokens = []
    i = 0
    while i < len(s):
        if s[i] in "()+-*/":
            tokens.append(s[i])
            i += 1
        elif s[i].isdigit() or s[i] == ".":
            start = i
            while i < len(s) and (s[i].isdigit() or s[i] == "."):
                i += 1
            tokens.append(s[start:i])
        else:
            i += 1
    return tokens


def _eval_expr(tokens):
    """Parse and evaluate expression (numbers and + - * / with precedence)."""
    tokens = list(tokens)
    idx = [0]

    def parse_factor():
        t = tokens[idx[0]]
        idx[0] += 1
        if t == "(":
            v = parse_expr()
            idx[0] += 1  # ")"
            return v
        if t == "-":
            return -parse_factor()
        if t == "+":
            return parse_factor()
        return float(t)

    def parse_term():
        left = parse_factor()
        while idx[0] < len(tokens) and tokens[idx[0]] in "*/":
            op = tokens[idx[0]]
            idx[0] += 1
            right = parse_factor()
            left = _OPS[op](left, right)
        return left

    def parse_expr():
        left = parse_term()
        while idx[0] < len(tokens) and tokens[idx[0]] in "+-":
            op = tokens[idx[0]]
            idx[0] += 1
            right = parse_term()
            left = _OPS[op](left, right)
        return left

    return parse_expr()
