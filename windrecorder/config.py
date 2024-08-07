import json
import os
import shutil

from send2trash import send2trash

from windrecorder.logger import get_logger

logger = get_logger(__name__)

CONFIG_NAME_USER = "config_user.json"
CONFIG_NAME_DEFAULT = "config_default.json"
CONFIG_NAME_VIDEO_COMPRESS_PRESET = "video_compress_preset.json"
CONFIG_NAME_RECORD_PRESET = "record_preset.json"

DIR_CONFIG_SRC = "windrecorder\\config_src"
DIR_USERDATA = "userdata"
FILEPATH_CONFIG_DEFAULT = os.path.join(DIR_CONFIG_SRC, CONFIG_NAME_DEFAULT)
FILEPATH_CONFIG_USER = os.path.join(DIR_USERDATA, CONFIG_NAME_USER)
FILEPATH_CONFIG_VIDEO_COMPRESS_PRESET = os.path.join(DIR_CONFIG_SRC, CONFIG_NAME_VIDEO_COMPRESS_PRESET)
FILEPATH_CONFIG_RECORD_PRESET = os.path.join(DIR_CONFIG_SRC, CONFIG_NAME_RECORD_PRESET)


class Config:
    def __init__(
        self,
        config_src_dir,
        db_path,
        vdb_img_path,
        record_videos_dir,
        record_seconds,
        record_framerate,
        record_bitrate,
        lang,
        ocr_lang,
        third_party_engine_ocr_lang,
        ocr_engine,
        ocr_short_size,
        max_page_result,
        target_screen_res,
        exclude_words,
        wordcloud_user_stop_words,
        vid_store_day,
        vid_compress_day,
        OCR_index_strategy,
        wordcloud_result_dir,
        screentime_not_change_to_pause_record,
        timeline_result_dir,
        user_name,
        use_similar_ch_char_to_search,
        ocr_image_crop_URBL,
        lightbox_result_dir,
        wintitle_result_dir,
        date_state_dir,
        release_ver,
        video_compress_rate,
        oneday_timeline_pic_num,
        compress_encoder,
        compress_accelerator,
        compress_quality,
        day_begin_minutes,
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
        search_history_note_filename,
        thumbnail_generation_size_width,
        thumbnail_generation_jpg_quality,
        webui_access_password_md5,
        enable_img_embed_search,
        img_embed_search_recall_result_per_db,
        img_embed_module_install,
        enable_search_history_record,
        batch_size_embed_video_in_idle,
        batch_size_remove_video_in_idle,
        batch_size_compress_video_in_idle,
        enable_3_columns_in_oneday,
        enable_synonyms_recommend,
        multi_display_record_strategy,
        record_single_display_index,
        record_encoder,
        record_crf,
        index_reduce_same_content_at_different_time,
        record_screenshot_method_capture_foreground_window_only,
        screenshot_interval_second,
        record_mode,
        screenshot_compare_similarity,
        ocr_compare_similarity,
        ocr_compare_similarity_in_table,
        convert_screenshots_to_vid_while_only_when_idle_or_plugged_in,
        foreground_window_video_background_color,
        is_record_system_sound,
        record_audio_device_name,
        record_foreground_window_process_name,
        record_deep_linking,
        support_ocr_lst,
        TesseractOCR_filepath,
        **other_field,
    ) -> None:
        # If need to process input parameters, they should assign another variable name to prevent recursive writing into the config.
        self.config_src_dir = config_src_dir
        self.userdata_dir = userdata_dir
        self.db_path_ud = os.path.join(userdata_dir, db_path)
        self.vdb_img_path_ud = os.path.join(userdata_dir, vdb_img_path)
        self.record_videos_dir_ud = os.path.join(userdata_dir, record_videos_dir)
        self.record_seconds = record_seconds
        self.record_framerate = record_framerate
        self.record_bitrate = record_bitrate
        self.ffmpeg_path = ".venv\\ffmpeg.exe" if release_ver else "ffmpeg"
        self.ffprobe_path = ".venv\\ffprobe.exe" if release_ver else "ffprobe"
        self.lang = lang
        self.ocr_lang = ocr_lang  # this param only affect Windows.Media.Ocr.Cli
        self.third_party_engine_ocr_lang = third_party_engine_ocr_lang  # this param only affect third-party ocr engine
        self.ocr_engine = ocr_engine
        self.ocr_short_size = ocr_short_size
        self.max_page_result = max_page_result
        self.target_screen_res = target_screen_res
        self.exclude_words = exclude_words
        self.wordcloud_user_stop_words = wordcloud_user_stop_words
        self.vid_store_day = vid_store_day
        self.vid_compress_day = vid_compress_day
        self.OCR_index_strategy = OCR_index_strategy  # 0=不自动索引，1=每录制完一个切片进行索引
        self.wordcloud_result_dir_ud = os.path.join(userdata_dir, wordcloud_result_dir)
        self.timeline_result_dir_ud = os.path.join(userdata_dir, timeline_result_dir)
        self.lightbox_result_dir_ud = os.path.join(userdata_dir, lightbox_result_dir)
        self.wintitle_result_dir_ud = os.path.join(userdata_dir, wintitle_result_dir)
        self.date_state_dir_ud = os.path.join(userdata_dir, date_state_dir)
        self.screentime_not_change_to_pause_record = screentime_not_change_to_pause_record
        self.user_name = user_name
        self.use_similar_ch_char_to_search = use_similar_ch_char_to_search
        self.ocr_image_crop_URBL = ocr_image_crop_URBL
        self.release_ver = release_ver
        self.video_compress_rate = video_compress_rate
        self.oneday_timeline_pic_num = oneday_timeline_pic_num
        self.maintain_lock_path = os.path.join(lock_file_dir, maintain_lock_subdir)
        self.record_lock_path = os.path.join(lock_file_dir, record_lock_name)
        self.tray_lock_path = os.path.join(lock_file_dir, tray_lock_name)
        self.img_emb_lock_path = os.path.join(lock_file_dir, img_emb_lock_name)
        self.last_idle_maintain_file_path = last_idle_maintain_file_path
        self.iframe_dir = iframe_dir
        self.compress_encoder = compress_encoder
        self.compress_accelerator = compress_accelerator
        self.compress_quality = compress_quality
        self.log_dir = log_dir
        self.win_title_dir = win_title_dir
        self.start_recording_on_startup = start_recording_on_startup
        self.lock_file_dir = lock_file_dir
        self.flag_mark_note_filename = flag_mark_note_filename
        self.flag_mark_note_filepath = os.path.join(self.userdata_dir, self.flag_mark_note_filename)
        self.search_history_note_filename = search_history_note_filename
        self.search_history_note_filepath = os.path.join(self.userdata_dir, self.search_history_note_filename)
        self.thumbnail_generation_size_width = thumbnail_generation_size_width
        self.thumbnail_generation_jpg_quality = thumbnail_generation_jpg_quality
        self.webui_access_password_md5 = webui_access_password_md5
        self.enable_img_embed_search = enable_img_embed_search
        self.img_embed_search_recall_result_per_db = img_embed_search_recall_result_per_db
        self.img_embed_module_install = img_embed_module_install
        self.day_begin_minutes = day_begin_minutes
        self.enable_search_history_record = enable_search_history_record
        self.batch_size_embed_video_in_idle = batch_size_embed_video_in_idle
        self.batch_size_remove_video_in_idle = batch_size_remove_video_in_idle
        self.batch_size_compress_video_in_idle = batch_size_compress_video_in_idle
        self.enable_3_columns_in_oneday = enable_3_columns_in_oneday
        self.enable_synonyms_recommend = enable_synonyms_recommend
        self.multi_display_record_strategy = multi_display_record_strategy  # all:record all   single:record single display
        self.record_single_display_index = record_single_display_index  # start from 1, map to mms display list
        self.record_encoder = record_encoder
        self.record_crf = record_crf
        self.index_reduce_same_content_at_different_time = index_reduce_same_content_at_different_time
        self.screenshot_interval_second = screenshot_interval_second
        self.record_mode = record_mode  # ffmpeg, screenshot_array
        self.record_screenshot_method_capture_foreground_window_only = record_screenshot_method_capture_foreground_window_only
        self.screenshot_compare_similarity = screenshot_compare_similarity
        self.ocr_compare_similarity = ocr_compare_similarity
        self.ocr_compare_similarity_in_table = ocr_compare_similarity_in_table
        self.convert_screenshots_to_vid_while_only_when_idle_or_plugged_in = (
            convert_screenshots_to_vid_while_only_when_idle_or_plugged_in
        )
        self.foreground_window_video_background_color = foreground_window_video_background_color
        self.is_record_system_sound = is_record_system_sound
        self.record_audio_device_name = record_audio_device_name
        self.record_foreground_window_process_name = record_foreground_window_process_name
        self.record_deep_linking = record_deep_linking
        self.support_ocr_lst = support_ocr_lst
        self.TesseractOCR_filepath = TesseractOCR_filepath

    def set_and_save_config(self, attr: str, value):
        if not hasattr(self, attr):
            logger.warning("{} not exist in config!".format(attr))
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
        with open(FILEPATH_CONFIG_USER, "w", encoding="utf-8") as f:
            json.dump(config_json, f, indent=2, ensure_ascii=False)

    def filter_unwanted_field(self, config_json):
        return config_json


# 从default config中更新user config（升级用）
def update_config_files_from_default_to_user():
    with open(FILEPATH_CONFIG_DEFAULT, "r", encoding="utf-8") as f:
        default_data = json.load(f)

    with open(FILEPATH_CONFIG_USER, "r", encoding="utf-8") as f:
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
    with open(FILEPATH_CONFIG_USER, "w", encoding="utf-8") as f:
        json.dump(user_data, f, indent=2, ensure_ascii=False)


def initialize_config():
    # 0.0.9 upgrade change, migrate previous user config
    if not os.path.exists(DIR_USERDATA):
        os.makedirs(DIR_USERDATA)

    if os.path.exists("config\\config_user.json"):
        shutil.copyfile("config\\config_user.json", FILEPATH_CONFIG_USER)
        send2trash("config\\config_user.json")

    if not os.path.exists(FILEPATH_CONFIG_USER):
        logger.info("-User config not found, will be created.")
        shutil.copyfile(FILEPATH_CONFIG_DEFAULT, FILEPATH_CONFIG_USER)


def get_config_json():
    initialize_config()
    update_config_files_from_default_to_user()
    with open(FILEPATH_CONFIG_USER, "r", encoding="utf-8") as f:
        config_json = json.load(f)
    return config_json


def get_video_compress_preset_json():
    with open(FILEPATH_CONFIG_VIDEO_COMPRESS_PRESET, "r", encoding="utf-8") as f:
        config_json = json.load(f)
    return config_json


def get_record_preset_json():
    with open(FILEPATH_CONFIG_RECORD_PRESET, "r", encoding="utf-8") as f:
        config_json = json.load(f)
    return config_json


config = Config(**get_config_json())
CONFIG_VIDEO_COMPRESS_PRESET = get_video_compress_preset_json()
CONFIG_RECORD_PRESET = get_record_preset_json()

# main 函数，输出 config 内容
if __name__ == "__main__":
    print(vars(config))
    print(config)
