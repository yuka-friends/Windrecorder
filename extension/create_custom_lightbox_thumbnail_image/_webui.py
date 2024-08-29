# Set workspace to Windrecorder dir
import os
import sys

current_dir = os.path.dirname(os.path.abspath(__file__))
parent_parent_dir = os.path.dirname(os.path.dirname(current_dir))
sys.path.append(parent_parent_dir)
os.chdir("..")
os.chdir("..")

import streamlit as st  # NOQA: E402

st.set_page_config(page_title="Create custom lightbox - Windrecord - webui", page_icon="🦝", layout="wide")


def main_webui():
    st.markdown("#### 自定义光箱生成器")
    col_L, col_R = st.columns([1, 3])
    with col_L:
        st.empty()
        col_L_params, col_R_params = st.columns([1, 1])
        with col_L_params:
            st.number_input("横向缩略图数量", min_value=5, max_value=1000, value=30, step=1)
        with col_R_params:
            st.number_input("纵向缩略图数量", min_value=5, max_value=1000, value=50, step=1)
        st.markdown("包含缩略图总数为：`1500`")
        st.button("创建图片", use_container_width=True, type="primary")
    with col_R:
        st.empty()


main_webui()
