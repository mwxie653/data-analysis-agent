"""ReAct Agent loop — think, act, observe, repeat."""

import json

from src.llm import DeepSeekClient
from src.tools import TOOLS, run_tool

SYSTEM_PROMPT = """你是一个自主数据分析Agent。你可以使用以下工具：
- execute_python: 执行Python代码
- read_file: 读取CSV数据摘要
- list_files: 列出文件
- generate_plot: 生成图表

分析流程：
1. 先用 list_files 了解有哪些数据文件
2. 用 read_file 查看数据结构
3. 根据用户问题，用 execute_python 做分析计算
4. 需要可视化时用 generate_plot 生成图表
5. **如果代码报错**，仔细阅读错误信息，修正代码后重试
6. 完成所有分析后，给出自然语言的总结

规则：
- 每次只调用一个工具
- 代码报错时，分析错误原因再修正，不要放弃
- 不要猜测数据内容——先读文件再回答
- 最终结论要引用实际分析结果"""


class Agent:
    def __init__(self, api_key: str):
        self.llm = DeepSeekClient(api_key=api_key)
        self.max_turns = 10

    def run(self, user_question: str) -> list[dict]:
        """Execute the ReAct loop. Returns a log of every step."""
        messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_question},
        ]
        log = []
        consecutive_errors = 0

        for turn in range(self.max_turns):
            try:
                response = self.llm.client.chat.completions.create(
                    model="deepseek-chat",
                    messages=messages,
                    tools=TOOLS,
                    temperature=0.3,
                )
            except Exception as e:
                log.append({
                    "type": "error",
                    "content": f"API 调用失败：{e}",
                })
                return log
            msg = response.choices[0].message

            # LLM decided to answer directly — task complete
            if not msg.tool_calls:
                log.append({"type": "answer", "content": msg.content})
                return log

            for tc in msg.tool_calls:
                tool_name = tc.function.name
                try:
                    args = json.loads(tc.function.arguments)
                except json.JSONDecodeError:
                    log.append({
                        "type": "error",
                        "content": f"LLM 返回了无效的 JSON 参数：{tc.function.arguments[:200]}",
                    })
                    consecutive_errors += 1
                    if consecutive_errors >= 2:
                        return log
                    continue

                log.append({
                    "type": "action",
                    "tool": tool_name,
                    "args": args,
                    "thought": msg.content or f"调用 {tool_name}",
                })

                result = run_tool(tool_name, args)
                log.append({"type": "observation", "content": result})

                # Error recovery: track consecutive failures
                if "[ERROR]" in result or "Traceback" in result:
                    consecutive_errors += 1
                    if consecutive_errors >= 2:
                        log.append({
                            "type": "error",
                            "content": f"连续{consecutive_errors}次失败，Agent停止：{result}",
                        })
                        return log
                else:
                    consecutive_errors = 0

                # Append assistant + tool messages to conversation
                messages.append({
                    "role": "assistant",
                    "content": msg.content,
                    "tool_calls": [tc],
                })
                messages.append({
                    "role": "tool",
                    "content": result,
                    "tool_call_id": tc.id,
                })

        log.append({"type": "error", "content": "超过最大轮次"})
        return log
