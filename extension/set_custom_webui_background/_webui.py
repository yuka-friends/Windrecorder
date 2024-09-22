# Set workspace to Windrecorder dir
import os
from io import BytesIO

import streamlit as st
from PIL import Image

from windrecorder.config import config
from windrecorder.const import ST_BACKGROUNDCOLOR
from windrecorder.file_utils import ensure_dir
from windrecorder.utils import get_text as _t

st.set_page_config(page_title="Create custom webui background - Windrecord - webui", page_icon="🦝", layout="wide")
overlay_image = Image.open(os.path.join("extension", "set_custom_webui_background", "_preview_overlay.png"))


def init_st_state():
    if "file_lazy" not in st.session_state:
        st.session_state["file_lazy"] = None
    if "opacity_lazy" not in st.session_state:
        st.session_state["opacity_lazy"] = None
    if "preview_img" not in st.session_state:
        st.session_state["preview_img"] = None


def generate_preview_image(uploaded_file, opacity):
    if not uploaded_file:
        return None

    image_data = BytesIO(uploaded_file.getvalue())
    image_bg = Image.open(image_data)

    image_canvas = Image.new("RGBA", overlay_image.size, (0, 0, 0, 0))

    opacity_layer = Image.new(
        "RGBA", overlay_image.size, (ST_BACKGROUNDCOLOR[0], ST_BACKGROUNDCOLOR[1], ST_BACKGROUNDCOLOR[2], int(opacity * 255))
    )
    overlay_width = overlay_image.width

    base_ratio = image_bg.height / image_bg.width
    new_height = int(overlay_width * base_ratio)
    resized_base_image = image_bg.resize((overlay_width, new_height))
    image_canvas.paste(resized_base_image, (0, 0))
    image_canvas.paste(opacity_layer, (0, 0), opacity_layer)
    image_canvas.paste(overlay_image, (0, 0), overlay_image)

    return image_canvas


def set_background(uploaded_file, opacity):
    if not uploaded_file:
        st.toast("no image selected", icon="⚠️")
        return

    save_path = os.path.join(config.userdata_dir, "custom", uploaded_file.name)
    ensure_dir(os.path.dirname(save_path))
    bytes_data = uploaded_file.getvalue()
    with open(save_path, "wb") as file:
        file.write(bytes_data)

    config.set_and_save_config("custom_background_filepath", save_path)
    config.set_and_save_config("custom_background_opacity", opacity)
    st.toast(_t("utils_toast_setting_saved") + f", {opacity}, " + save_path, icon="✅")


def clean_background():
    config.set_and_save_config("custom_background_filepath", "")
    config.set_and_save_config("custom_background_opacity", 0.9)
    st.session_state["preview_img"] = None

    st.toast("已关闭自定义背景图", icon="✅")


def main_webui():
    def update_preview():
        update_condition = False

        if file != st.session_state["file_lazy"]:
            update_condition = True
            st.session_state["file_lazy"] = file

        if opacity != st.session_state["opacity_lazy"]:
            update_condition = True
            st.session_state["opacity_lazy"] = opacity

        if update_condition:
            st.session_state["preview_img"] = generate_preview_image(file, opacity)

    st.markdown("### 🖼️ 自定义 webui 背景图片")
    col_1, col_2, col_3, col_4 = st.columns([1.5, 0.5, 3, 0.5])
    with col_1:
        file = st.file_uploader(
            _t("gs_text_upload_img"), type=["png", "jpg", "webp"], accept_multiple_files=False, on_change=update_preview
        )
        opacity = st.slider("不透明度", min_value=0.01, max_value=0.99, value=0.9, step=0.01, on_change=update_preview)

        if config.custom_background_filepath:
            if st.button("移除背景图片", use_container_width=True, type="secondary"):
                clean_background()

        if st.button("设置为背景图片", use_container_width=True, type="primary", disabled=True if file is None else False):
            set_background(file, opacity)

        st.empty()

        st.caption("---\nmade by [@antonoko](https://github.com/Antonoko), version 0.0.1")

    with col_2:
        st.empty()
    with col_3:
        update_preview()
        if st.session_state["preview_img"]:
            st.image(st.session_state["preview_img"], caption="预览效果")
        else:
            st.image(overlay_image, caption="预览效果")
        st.empty()
    with col_4:
        st.empty()


init_st_state()
main_webui()
