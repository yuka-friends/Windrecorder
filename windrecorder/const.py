import os

# all const var should be stored here
CACHE_DIR = "cache"
CACHE_DIR_OCR_IMG_PREPROCESSOR = os.path.join(CACHE_DIR, "temp_ocr_img_preprocess")

FOOTER_STATE_CAHCE_FILEPATH = "cache\\footer_info_cache.json"
SCREENSHOT_CACHE_FILEPATH = "cache_screenshot"
SCREENSHOT_CACHE_FILEPATH_TMP_DB_NAME = "tmp_db.json"
SCREENSHOT_CACHE_FILEPATH_TMP_DB_ALL_FILES_NAME = "tmp_db_json_all_files.json"


ERROR_VIDEO_RETRY_TIMES = 3

DATETIME_FORMAT = "%Y-%m-%d_%H-%M-%S"
DATE_FORMAT = "%Y-%m"
DATETIME_FORMAT_PATTERN = r"(\d{4}-\d{2}-\d{2}_\d{2}-\d{2}-\d{2})"

DATAFRAME_COLUMN_NAMES = [
    "videofile_name",
    "picturefile_name",
    "videofile_time",
    "ocr_text",
    "is_videofile_exist",
    "is_picturefile_exist",
    "thumbnail",
    "win_title",
]
