import datetime
import html
import os
from pathlib import Path

import pandas as pd
import streamlit as st

from windrecorder import file_utils, flag_mark_note, record_wintitle, utils
from windrecorder.config import config
from windrecorder.const import ST_BACKGROUNDCOLOR
from windrecorder.db_manager import db_manager
from windrecorder.llm import component_day_or_month_tags
from windrecorder.logger import get_logger
from windrecorder.utils import get_text as _t

# do not import from windrecorder.ui

logger = get_logger(__name__)


# 检测并渲染onboarding提示
def web_onboarding():
    # 状态懒加载
    if "is_onboarding" not in st.session_state:
        st.session_state["is_onboarding"] = db_manager.check_is_onboarding()

    if st.session_state.is_onboarding:
        # 数据库不存在，展示 Onboarding 提示
        st.success(_t("text_welcome_to_windrecorder"), icon="😺")
        intro_markdown = Path(f"{config.config_src_dir}\\onboarding_{config.lang}.md").read_text(encoding="utf-8")
        st.markdown(intro_markdown)
        st.divider()


# 规范化的打表渲染组件
def video_dataframe(df, heightIn=800):
    # ~~is_videofile_exist~~ videofile 渲染为可选框
    # ocr_text 更大的展示空间
    # thumbnail 渲染为图像
    st.dataframe(
        df,
        column_config={
            "videofile": st.column_config.CheckboxColumn(
                "videofile",
                default=False,
            ),
            "ocr_text": st.column_config.TextColumn("ocr_text", width="medium"),
            "win_title": st.column_config.TextColumn("title", width="medium"),
            "thumbnail": st.column_config.ImageColumn(
                "thumbnail",
            ),
        },
        height=heightIn,
    )


def record_search_history(search_content, search_type, search_datetime=None):
    """记录搜索历史"""
    skip_words = [""]
    if search_content in skip_words:
        return
    try:
        if config.enable_search_history_record:
            if search_datetime is None:
                search_datetime = datetime.datetime.now()

            CSV_TEMPLATE_HISTORY = pd.DataFrame(columns=["search_content", "search_type", "search_datetime"])
            if not os.path.exists(config.search_history_note_filepath):
                file_utils.ensure_dir(config.userdata_dir)
                file_utils.save_dataframe_to_path(CSV_TEMPLATE_HISTORY, file_path=config.search_history_note_filepath)

            df = file_utils.read_dataframe_from_path(file_path=config.search_history_note_filepath)

            new_data = {
                "search_content": search_content,
                "search_type": search_type,
                "search_datetime": datetime.datetime.strftime(search_datetime, "%Y-%m-%d %H:%M:%S"),
            }
            df.loc[len(df)] = new_data
            file_utils.save_dataframe_to_path(df, file_path=config.search_history_note_filepath)
    except Exception as e:
        logger.error(e)


# 一日之时工具栏
def oneday_side_toolbar():
    lefttab_wintitle, lefttab_flagnote = st.tabs([_t("oneday_ls_title_wintitle"), _t("oneday_ls_title_flag_note")])
    with lefttab_wintitle:
        if config.enable_ai_extract_tag and datetime.date.today() != st.session_state.day_date_input:
            component_day_or_month_tags(st.session_state.day_date_input)
        record_wintitle.component_wintitle_stat(st.session_state.day_date_input)
    with lefttab_flagnote:
        flag_mark_note.component_flag_mark()


# 读取嵌入模型缓存
def load_emb_model_cache():
    if config.img_embed_module_install:
        try:
            from windrecorder import img_embed_manager

            try:
                if "emb_model_text" not in st.session_state or "emb_model_image" not in st.session_state:
                    with st.spinner(_t("gs_text_loading_embed_model")):
                        (
                            st.session_state["emb_model_text"],
                            st.session_state["emb_model_image"],
                            st.session_state["emb_processor_text"],
                            st.session_state["emb_processor_image"],
                        ) = img_embed_manager.get_model_and_processor()
            except ModuleNotFoundError:
                config.set_and_save_config("img_embed_module_install", False)
        except ModuleNotFoundError:
            config.set_and_save_config("img_embed_module_install", False)


# 显示 deep linking
def render_deep_linking(url):
    if isinstance(url, str):
        if "http" in url.lower():
            st.markdown(f"[{url}]({url})")
        else:
            st.markdown(f"{url}")


# 以 html 方式显示图片
def html_picture(imagepath, caption=None):
    if f"html_pic_b64_cache_{os.path.basename(imagepath)}" not in st.session_state:  # caching base 64 result
        st.session_state[f"html_pic_b64_cache_{os.path.basename(imagepath)}"] = utils.image_to_base64(imagepath)

    pic_b64 = st.session_state[f"html_pic_b64_cache_{os.path.basename(imagepath)}"]
    st.markdown(
        f"<img style='max-width: 100%;max-height: 100%;margin: 0 0px 0px 0px' src='data:image/png;base64, {pic_b64}'/>",
        unsafe_allow_html=True,
    )
    if caption:
        st.caption("<p align='center'>" + caption + "</p>", unsafe_allow_html=True)


# custom css
def inject_custom_css():
    if not os.path.exists(config.custom_background_filepath):
        st.toast(_t("bg_text_not_existed").format(custom_background_filepath=config.custom_background_filepath), icon="⚠️")
        config.set_and_save_config("custom_background_filepath", "")
        return

    b64 = "data:image/png;base64, " + utils.image_to_base64(config.custom_background_filepath)

    custom_img_bg = f"background-image: url('{b64}') !important;"
    custom_img_bg_opacity = f"background-color: rgba({ST_BACKGROUNDCOLOR[0]}, {ST_BACKGROUNDCOLOR[1]}, {ST_BACKGROUNDCOLOR[2]}, {config.custom_background_opacity}) !important;"

    custom_css_text = (
        """
body {
"""
        + custom_img_bg
        + """
        background-color: rgb(0,0,0,0) !important;
        background-position: top;
        background-repeat: no-repeat;
        background-size: cover;
    }
.stApp {
"""
        + custom_img_bg_opacity
        + """
}
[class^="st-emotion-cache-"] {
    background: rgba(0,0,0,0) !important;
}

.chart-wrapper, .glideDataEditor, .st-ag, .st-cd, .st-d1, .st-bg, .st-co, .st-bp, .st-ct, .st-br, .st-bs, .st-bt, .st-bu, .st-c1, .st-cy, .st-ec, .st-ed, .rti--container {
    mix-blend-mode: darken;
}

.step-down, .step-up {
    mix-blend-mode: multiply;
}


"""
    )

    st.markdown(f"<style>{custom_css_text}</style>", unsafe_allow_html=True)
    if "css_injected" not in st.session_state:
        st.session_state["css_injected"] = True


def ocr_res_position_visualization(ocr_text_full: str, ocr_text_query: str):
    """在全部文本中高亮搜索内容，渲染为 html 卡片显示"""
    ocr_text_full = ocr_text_full.replace("\n", " ")

    def find_all_occurrences(original_text, pattern):
        lower_text = original_text.lower()
        lower_pattern = pattern.lower()
        start = 0
        occurrences = []
        len_pattern = len(lower_pattern)
        if len_pattern == 0:
            return occurrences
        while True:
            pos = lower_text.find(lower_pattern, start)
            if pos == -1:
                break
            end = pos + len_pattern - 1
            occurrences.append((pos, end))
            start = pos + 1  # 移动到当前匹配之后继续查找
        return occurrences

    def merge_intervals(intervals):
        if not intervals:
            return []
        sorted_intervals = sorted(intervals, key=lambda x: x[0])
        merged = [sorted_intervals[0]]
        for current in sorted_intervals[1:]:
            last = merged[-1]
            if current[0] <= last[1] + 1:
                merged[-1] = (last[0], max(last[1], current[1]))
            else:
                merged.append(current)
        return merged

    # 处理查询词：分割、替换连字符、保留原始大小写
    search_terms = [term.replace("-", " ") for term in ocr_text_query.split() if term.strip()]
    search_terms.extend([term.replace("-", "") for term in ocr_text_query.split() if term.strip()])

    # 查找所有匹配区间
    intervals = []
    for term in search_terms:
        if not term:
            continue
        # 这里使用原始文本进行实际匹配，但比较时忽略大小写
        for start, end in find_all_occurrences(ocr_text_full, term):
            intervals.append((start, end))

    # 合并重叠区间
    merged = merge_intervals(intervals)

    # 构建文本片段
    parts = []
    start_pos = 0
    for start, end in merged:
        if start_pos < start:
            parts.append(ocr_text_full[start_pos:start])
        parts.append(("highlight", ocr_text_full[start : end + 1]))
        start_pos = end + 1

    if start_pos < len(ocr_text_full):
        parts.append(ocr_text_full[start_pos:])

    # Build HTML content
    html_content = []
    for part in parts:
        if isinstance(part, tuple):
            escaped = html.escape(part[1])
            html_content.append(
                f'<span style="background-color: #8262C9; color: white; font-weight: bold; padding: 1px 4px 1px 4px;">{escaped}</span>'
            )
        else:
            escaped = html.escape(part).replace("\n", "<br/>")
            html_content.append(escaped)

    res = f"""
<div style="width: 100%; border-radius: 6px; font-size: 10px; color:rgba(0,0,0,.4); background: #F6F2EF; padding: 5px 10px 5px 10px; box-sizing: border-box; mix-blend-mode: multiply;">
{''.join(html_content)}
</div>
""".strip()

    st.markdown(res, unsafe_allow_html=True)
