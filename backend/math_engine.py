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

_EXPR_IN_TEXT = re.compile(
    r"(?:what is|calculate|compute|evaluate|solve)\s+([\d\s+\-*/().]+?)(?:\?|\.|\s+then|\s*$)",
    re.IGNORECASE,
)


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
        value = _eval_expr(_tokenize(expr))
        if value is None:
            return None
        if float(value).is_integer():
            return int(value)
        return round(float(value), 6)
    except (ValueError, ZeroDivisionError, IndexError):
        return None


def extract_expression(text):
    """Return the first safe arithmetic sub-expression found in a question."""
    if not text:
        return None
    for match in _EXPR_IN_TEXT.finditer(text):
        cleaned = (match.group(1) or "").strip().strip("?.,")
        if cleaned and solve(cleaned) is not None:
            return cleaned
    return None


def build_mixed_math_reply(level, user_text, math_result):
    """Deterministic answer for calculate-then-explain prompts (demo-safe on Light tier)."""
    expr = extract_expression(user_text) or str(math_result)
    result = math_result

    if level == "basic":
        return (
            f"The answer is {result}. "
            "Do multiplication and division before addition and subtraction."
        )

    if level == "lower_secondary":
        return (
            f"{expr} = {result}. "
            "Order of operations means brackets first, then multiplication and division, "
            "then addition and subtraction."
        )

    if level == "upper_secondary":
        return (
            f"Evaluating {expr}: division and multiplication are done before addition, "
            f"so the result is {result}. "
            "Order of operations (PEMDAS/BODMAS) keeps everyone calculating the same way: "
            "parentheses, then × and ÷, then + and −."
        )

    steps = (
        f"1. Parse the expression {expr} and identify operator precedence.\n"
        "2. Evaluate division and multiplication before addition.\n"
        f"3. Combine the intermediate values to obtain {result}.\n"
        "4. Order of operations (PEMDAS/BODMAS) prevents ambiguity by fixing precedence rules."
    )
    return (
        f"The result of {expr} is {result}. "
        "Technical evaluation applies operator precedence: parentheses, then multiplication/division, "
        "then addition/subtraction.\n"
        f"{steps}"
    )


def solve_in_text(text):
    """Return a numeric result when a safe expression appears inside a question."""
    if not text or not isinstance(text, str):
        return None

    direct = solve(text.strip())
    if direct is not None:
        return direct

    candidates = []
    for match in _EXPR_IN_TEXT.finditer(text):
        cleaned = (match.group(1) or "").strip().strip("?.,")
        if cleaned:
            candidates.append(cleaned)

    if not candidates:
        return None

    candidates.sort(key=len, reverse=True)
    for candidate in candidates:
        result = solve(candidate)
        if result is not None:
            return result
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
