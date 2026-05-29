import streamlit as st
import pandas as pd
import os
import glob
from src.agent import Agent
from dotenv import load_dotenv

load_dotenv()

st.set_page_config(page_title="数据分析Agent", layout="wide")
st.title("自主数据分析 Agent")

# ── Sidebar: file upload + API key ─────────────────────────────────────

with st.sidebar:
    st.header("数据上传")
    uploaded = st.file_uploader("上传 CSV", type=["csv"])
    api_key = st.text_input(
        "DeepSeek API Key",
        value=os.getenv("DEEPSEEK_API_KEY", ""),
        type="password",
    )

    if uploaded:
        os.makedirs("data", exist_ok=True)
        os.makedirs("outputs", exist_ok=True)
        path = f"data/{uploaded.name}"
        with open(path, "wb") as f:
            f.write(uploaded.read())
        st.success(f"已保存：{uploaded.name}")

        df = pd.read_csv(path)
        st.dataframe(df.head(10), use_container_width=True)

# ── Main: chat input → ReAct log → charts ──────────────────────────────

question = st.chat_input("用自然语言描述你想做的分析...")

if question and api_key:
    agent = Agent(api_key=api_key)

    with st.chat_message("user"):
        st.write(question)

    with st.chat_message("assistant"):
        logs = agent.run(question)

        for entry in logs:
            if entry["type"] == "action":
                with st.expander(f"🔧 {entry['tool']}", expanded=True):
                    st.caption(f"参数：{entry['args']}")
                    st.info(entry.get("thought", ""))
            elif entry["type"] == "observation":
                st.code(entry["content"][:500], language="text")
            elif entry["type"] == "answer":
                st.success(entry["content"])
            elif entry["type"] == "error":
                st.error(entry["content"])

        # Show generated charts (current session only)
        if "session_plots" not in st.session_state:
            st.session_state.session_plots = set()
        os.makedirs("outputs", exist_ok=True)
        current_plots = set(glob.glob("outputs/*.png"))
        new_plots = current_plots - st.session_state.session_plots
        st.session_state.session_plots = current_plots
        if new_plots:
            st.subheader("生成的图表")
            for p in sorted(new_plots, reverse=True):
                st.image(p)
