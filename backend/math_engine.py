def solve(expression):
    try:
        return eval(expression, {"__builtins__": {}})
    except:
        return None
