"""Tool definitions and execution for the data analysis Agent."""

import subprocess
import os

import pandas as pd
from pathlib import Path

from src.sandbox import validate_code

# ── Tool definitions (OpenAI Function Calling schema) ──────────────────────

TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "execute_python",
            "description": "执行 Python 代码并返回输出。用于数据分析、数值计算、图表生成。",
            "parameters": {
                "type": "object",
                "properties": {
                    "code": {
                        "type": "string",
                        "description": "要执行的 Python 代码",
                    }
                },
                "required": ["code"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "read_file",
            "description": "读取CSV文件并返回数据摘要（行数、列名、数据类型、前5行、缺失值统计）",
            "parameters": {
                "type": "object",
                "properties": {
                    "filepath": {"type": "string", "description": "CSV文件的路径"}
                },
                "required": ["filepath"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "list_files",
            "description": "列出当前工作目录下的所有文件",
            "parameters": {"type": "object", "properties": {}},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "generate_plot",
            "description": "使用matplotlib生成图表并保存为PNG。返回图片路径。",
            "parameters": {
                "type": "object",
                "properties": {
                    "code": {
                        "type": "string",
                        "description": "使用matplotlib/seaborn生成图表的Python代码。必须包含plt.savefig('outputs/xxx.png')",
                    }
                },
                "required": ["code"],
            },
        },
    },
]

# ── Tool dispatcher ────────────────────────────────────────────────────────

def run_tool(tool_name: str, arguments: dict) -> str:
    """Dispatch a tool call by name."""
    if tool_name == "execute_python":
        return _execute_python(arguments["code"])
    if tool_name == "read_file":
        return _read_file(arguments["filepath"])
    if tool_name == "list_files":
        return _list_files()
    if tool_name == "generate_plot":
        return _execute_python(arguments["code"], timeout=30)
    return f"未知工具：{tool_name}"

# ── Tool implementations ───────────────────────────────────────────────────

def _execute_python(code: str, timeout: int = 10) -> str:
    """Execute Python code in a temporary sandbox directory."""
    safe, reason = validate_code(code)
    if not safe:
        return f"[BLOCKED] {reason}"

    os.makedirs("data", exist_ok=True)
    os.makedirs("outputs", exist_ok=True)

    try:
        result = subprocess.run(
            ["python", "-c", code],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=timeout,
        )
        output = (result.stdout or "").strip()
        if result.stderr:
            output += "\n[stderr]\n" + (result.stderr or "").strip()
        return output or "(无输出)"
    except subprocess.TimeoutExpired:
        return "[ERROR] 代码执行超时（>10秒）"


def _read_file(filepath: str) -> str:
    """Read a CSV file and return a data summary."""
    try:
        df = pd.read_csv(filepath)
        info = [
            f"文件：{filepath}",
            f"行数：{len(df)}，列数：{len(df.columns)}",
            f"列名：{list(df.columns)}",
            f"数据类型：\n{df.dtypes.to_string()}",
            f"\n前5行：\n{df.head().to_string()}",
            f"\n缺失值：\n{df.isnull().sum().to_string()}",
        ]
        return "\n".join(info)
    except Exception as e:
        return f"[ERROR] 读取文件失败：{e}"


def _list_files() -> str:
    """List files in data/ and outputs/ directories."""
    files = []
    for d in ("data", "outputs"):
        p = Path(d)
        if p.exists():
            files.extend(str(f) for f in p.glob("*"))
    return "\n".join(files) or "(无文件)"
