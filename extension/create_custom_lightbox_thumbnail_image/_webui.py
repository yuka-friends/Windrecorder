# Set workspace to Windrecorder dir
import datetime
import os

import streamlit as st

from windrecorder.const import CACHE_DIR
from windrecorder.db_manager import db_manager
from windrecorder.state import generate_lightbox_from_datetime_range
from windrecorder.ui.components import html_picture
from windrecorder.ui.search import ui_component_date_range_selector
from windrecorder.utils import get_text as _t

st.set_page_config(page_title="Create custom lightbox - Windrecord - webui", page_icon="🦝", layout="wide")

last_img_saved_path = "extension\\create_custom_lightbox_thumbnail_image\\_lightbox_placeholder.jpg"


def init_st_state():
    # 初始化时间搜索范围组件（懒加载）
    if "search_latest_record_time_int" not in st.session_state:
        st.session_state["search_latest_record_time_int"] = db_manager.db_latest_record_time()
    if "search_earlist_record_time_int" not in st.session_state:
        st.session_state["search_earlist_record_time_int"] = db_manager.db_first_earliest_record_time()
    if "search_date_range_in" not in st.session_state:
        st.session_state.search_date_range_in = datetime.datetime.today() - datetime.timedelta(seconds=86400)
    if "search_date_range_out" not in st.session_state:
        st.session_state.search_date_range_out = datetime.datetime.today()


def generate_lightbox_data_range(
    img_saved_path, width_thumbnail_num, height_thumbnail_num, lightbox_width, image_lst_mode, is_add_watermark=True
):
    with st.spinner(_t("lb_text_generating")):
        if generate_lightbox_from_datetime_range(
            dt_month_start=st.session_state.search_date_range_in,
            dt_month_end=st.session_state.search_date_range_out,
            image_lst_mode=image_lst_mode,
            img_saved_name=os.path.basename(img_saved_path),
            img_saved_folder=os.path.dirname(img_saved_path),
            pic_width_num=width_thumbnail_num,
            pic_height_num=height_thumbnail_num,
            lightbox_width=lightbox_width,
            enable_month_lightbox_watermark=is_add_watermark,
        ):
            return img_saved_path
        else:
            return None


def ui_custom_data_range():
    st.markdown("---\n### 📆")

    data_range_type_lst = [_t("lb_text_month_range"), _t("lb_text_exact_date")]
    data_range_type = st.radio(_t("lb_text_data_selector"), data_range_type_lst, label_visibility="collapsed")
    if data_range_type == data_range_type_lst[0]:
        ui_component_date_range_selector(data_type="month_range")
    elif data_range_type == data_range_type_lst[1]:
        ui_component_date_range_selector(data_type="exact_date")

    st.markdown("---\n### 🎞️")

    thumbnail_mode_lst = [_t("lb_text_distributeavg"), _t("lb_text_timeavg")]
    thumbnail_mode_select = st.radio(_t("lb_text_thumbnail_mode_select"), thumbnail_mode_lst)
    thumbnail_mode = "distributeavg"
    if thumbnail_mode_select == thumbnail_mode_lst[0]:
        thumbnail_mode = "distributeavg"
    elif thumbnail_mode_select == thumbnail_mode_lst[1]:
        thumbnail_mode = "timeavg"

    st.markdown("---\n### 🖼️")

    col_L_params, col_R_params = st.columns([1, 1])
    with col_L_params:
        width_thumbnail_num = int(
            st.number_input(_t("lb_text_width_thumbnail_num"), min_value=5, max_value=1000, value=25, step=1)
        )
    with col_R_params:
        height_thumbnail_num = int(
            st.number_input(_t("lb_text_height_thumbnail_num"), min_value=5, max_value=1000, value=35, step=1)
        )

    if thumbnail_mode_select == thumbnail_mode_lst[0]:
        st.info(
            _t("lb_tip_distributeavg").format(
                num=width_thumbnail_num * height_thumbnail_num,
            )
        )
    elif thumbnail_mode_select == thumbnail_mode_lst[1]:
        st.info(
            _t("lb_tip_timeavg").format(
                num=width_thumbnail_num * height_thumbnail_num,
            )
        )

    custom_lightbox_width = int(
        st.number_input(_t("lb_text_custom_lightbox_width"), min_value=1775, max_value=10000, value=1800, step=1)
    )
    is_add_watermark = st.checkbox(_t("lb_checkbox_add_watermark"), value=True)

    if st.button(_t("lb_btn_create_img"), use_container_width=True, type="primary"):
        global last_img_saved_path
        last_img_saved_path = os.path.join(
            CACHE_DIR,
            st.session_state.search_date_range_in.strftime("%Y%m%d")
            + "-"
            + st.session_state.search_date_range_out.strftime("%Y%m%d")
            + "_"
            + datetime.datetime.now().strftime("%Y%m%d%H%M%S")
            + ".png",
        )
        generate_lightbox_data_range(
            img_saved_path=last_img_saved_path,
            width_thumbnail_num=width_thumbnail_num,
            height_thumbnail_num=height_thumbnail_num,
            image_lst_mode=thumbnail_mode,
            lightbox_width=custom_lightbox_width,
            is_add_watermark=is_add_watermark,
        )
    st.caption(
        _t("lb_text_create_img_instruction").format(
            cache_dir=CACHE_DIR,
        )
    )


def main_webui():
    st.markdown(_t("lb_text_title"))
    col_1, col_2, col_3, col_4 = st.columns([1.5, 0.5, 3, 0.5])
    with col_1:
        st.empty()
        ui_custom_data_range()

        st.caption("---\nmade by [@antonoko](https://github.com/Antonoko), version 0.0.1")

    with col_2:
        st.empty()
    with col_3:
        if os.path.exists(last_img_saved_path):
            html_picture(last_img_saved_path, caption=last_img_saved_path)
        st.empty()
    with col_4:
        st.empty()


init_st_state()
main_webui()
