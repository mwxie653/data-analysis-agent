"""AST-based safety validation for user-submitted Python code."""

import ast

FORBIDDEN_IMPORTS = {
    "os", "subprocess", "socket", "shutil", "sys",
    "ctypes", "multiprocessing", "signal",
}

FORBIDDEN_CALLS = {
    "eval", "exec", "compile", "__import__",
    "open",
}


def validate_code(code: str) -> tuple[bool, str]:
    """Static analysis of Python code. Returns (is_safe, reason)."""
    try:
        tree = ast.parse(code)
    except SyntaxError as e:
        return False, f"语法错误：{e}"

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name.split(".")[0] in FORBIDDEN_IMPORTS:
                    return False, f"禁止导入模块：{alias.name}"
        if isinstance(node, ast.ImportFrom):
            if node.module and node.module.split(".")[0] in FORBIDDEN_IMPORTS:
                return False, f"禁止导入模块：{node.module}"

        if isinstance(node, ast.Call):
            if isinstance(node.func, ast.Name):
                if node.func.id in FORBIDDEN_CALLS:
                    return False, f"禁止调用：{node.func.id}()"

    return True, "OK"
