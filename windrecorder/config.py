import json
import os
import shutil

config_name = "config_user.json"
config_name_default = "src\\config_default.json"
config_name_video_compress_preset = "src\\video_compress_preset.json"
config_dir = "config"
default_config_path = os.path.join(config_dir, config_name_default)
user_config_path = os.path.join(config_dir, config_name)
video_compress_preset_config_path = os.path.join(config_dir, config_name_video_compress_preset)


class Config:
    def __init__(
        self,
        db_path,
        vdb_img_path,
        record_videos_dir,
        record_seconds,
        record_framerate,
        record_bitrate,
        record_screen_enable_half_res_while_hidpi,
        lang,
        ocr_lang,
        ocr_engine,
        max_page_result,
        target_screen_res,
        exclude_words,
        wordcloud_user_stop_words,
        vid_store_day,
        vid_compress_day,
        OCR_index_strategy,
        wordcloud_result_dir,
        screentime_not_change_to_pause_record,
        show_oneday_wordcloud,
        timeline_result_dir,
        user_name,
        use_similar_ch_char_to_search,
        ocr_image_crop_URBL,
        lightbox_result_dir,
        release_ver,
        video_compress_rate,
        oneday_timeline_pic_num,
        enable_ocr_chineseocr_lite_onnx,
        compress_encoder,
        compress_accelerator,
        compress_quality,
        lock_file_dir,
        maintain_lock_subdir,
        record_lock_name,
        tray_lock_name,
        img_emb_lock_name,
        last_idle_maintain_file_path,
        iframe_dir,
        log_dir,
        win_title_dir,
        start_recording_on_startup,
        userdata_dir,
        flag_mark_note_filename,
        thumbnail_generation_size_width,
        thumbnail_generation_jpg_quality,
        show_oneday_left_side_stat,
        webui_access_password_md5,
        enable_img_embed_search,
        img_embed_search_recall_result_per_db,
        img_embed_module_install,
        record_skip_wintitle,
        **other_field,
    ) -> None:
        self.db_path = db_path
        self.vdb_img_path = vdb_img_path
        self.record_videos_dir = record_videos_dir
        self.record_seconds = record_seconds
        self.record_framerate = record_framerate
        self.record_bitrate = record_bitrate
        self.record_screen_enable_half_res_while_hidpi = record_screen_enable_half_res_while_hidpi
        self.ffmpeg_path = ".venv\\ffmpeg.exe" if release_ver else "ffmpeg"
        self.lang = lang
        self.ocr_lang = ocr_lang
        self.ocr_engine = ocr_engine
        self.max_page_result = max_page_result
        self.target_screen_res = target_screen_res
        self.exclude_words = exclude_words
        self.wordcloud_user_stop_words = wordcloud_user_stop_words
        self.vid_store_day = vid_store_day
        self.vid_compress_day = vid_compress_day
        self.OCR_index_strategy = OCR_index_strategy  # 0=不自动索引，1=每录制完一个切片进行索引
        self.wordcloud_result_dir = wordcloud_result_dir
        self.timeline_result_dir = timeline_result_dir
        self.lightbox_result_dir = lightbox_result_dir
        self.screentime_not_change_to_pause_record = screentime_not_change_to_pause_record
        self.show_oneday_wordcloud = show_oneday_wordcloud
        self.user_name = user_name
        self.use_similar_ch_char_to_search = use_similar_ch_char_to_search
        self.ocr_image_crop_URBL = ocr_image_crop_URBL
        self.release_ver = release_ver
        self.video_compress_rate = video_compress_rate
        self.oneday_timeline_pic_num = oneday_timeline_pic_num
        self.enable_ocr_chineseocr_lite_onnx = enable_ocr_chineseocr_lite_onnx
        self.maintain_lock_path = os.path.join(lock_file_dir, maintain_lock_subdir)
        self.record_lock_path = os.path.join(lock_file_dir, record_lock_name)
        self.tray_lock_path = os.path.join(lock_file_dir, tray_lock_name)
        self.img_emb_lock_path = os.path.join(lock_file_dir, img_emb_lock_name)
        self.last_idle_maintain_file_path = last_idle_maintain_file_path
        self.iframe_dir = iframe_dir
        self.compress_encoder = compress_encoder
        self.compress_accelerator = compress_accelerator
        self.compress_quality = compress_quality
        self.compress_preset = get_video_compress_preset_json()
        self.log_dir = log_dir
        self.win_title_dir = win_title_dir
        self.start_recording_on_startup = start_recording_on_startup
        self.lock_file_dir = lock_file_dir
        self.userdata_dir = userdata_dir
        self.flag_mark_note_filename = flag_mark_note_filename
        self.flag_mark_note_filepath = os.path.join(self.userdata_dir, self.flag_mark_note_filename)
        self.thumbnail_generation_size_width = thumbnail_generation_size_width
        self.thumbnail_generation_jpg_quality = thumbnail_generation_jpg_quality
        self.show_oneday_left_side_stat = show_oneday_left_side_stat
        self.webui_access_password_md5 = webui_access_password_md5
        self.enable_img_embed_search = enable_img_embed_search
        self.img_embed_search_recall_result_per_db = img_embed_search_recall_result_per_db
        self.img_embed_module_install = img_embed_module_install
        self.record_skip_wintitle = record_skip_wintitle

    def set_and_save_config(self, attr: str, value):
        if not hasattr(self, attr):
            print("{} not exist in config!".format(attr))
            return
            # raise AttributeError("{} not exist in config!".format(attr))
        setattr(self, attr, value)
        self.save_config()

    def save_config(self):
        # 读取 config.json 获取旧设置
        config_json = get_config_json()
        # 把 python 对象转为 dict
        now_config_json = vars(self)
        # 更新设置
        config_json.update(now_config_json)
        # 去除不必要的字段
        self.filter_unwanted_field(config_json)
        # 写入 config.json 文件
        with open(user_config_path, "w", encoding="utf-8") as f:
            json.dump(config_json, f, indent=2, ensure_ascii=False)

    def filter_unwanted_field(self, config_json):
        return config_json


# 从default config中更新user config（升级用）
def update_config_files_from_default_to_user():
    with open(default_config_path, "r", encoding="utf-8") as f:
        default_data = json.load(f)

    with open(user_config_path, "r", encoding="utf-8") as f:
        user_data = json.load(f)

    # 将 default 中有的、user 中没有的属性从 default 写入 user中
    for key, value in default_data.items():
        if key not in user_data:
            user_data[key] = value
    # 将 default 中没有的、user 中有的属性从 user 中删除
    keys_to_remove = [key for key in user_data.keys() if key not in default_data]
    for key in keys_to_remove:
        del user_data[key]
    # 将更新后的 default 数据写入 user.json 文件
    with open(user_config_path, "w", encoding="utf-8") as f:
        json.dump(user_data, f, indent=2, ensure_ascii=False)


def initialize_config():
    if not os.path.exists(user_config_path):
        print("-User config not found, will be created.")
        shutil.copyfile(default_config_path, user_config_path)


def get_config_json():
    initialize_config()
    update_config_files_from_default_to_user()
    with open(user_config_path, "r", encoding="utf-8") as f:
        config_json = json.load(f)
    return config_json


def get_video_compress_preset_json():
    with open(video_compress_preset_config_path, "r", encoding="utf-8") as f:
        config_json = json.load(f)
    return config_json


config = Config(**get_config_json())
