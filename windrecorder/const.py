import os

# all const var should be stored here
CACHE_DIR = "cache"
CACHE_DIR_OCR_IMG_PREPROCESSOR = os.path.join(CACHE_DIR, "temp_ocr_img_preprocess")

FOOTER_STATE_CAHCE_FILEPATH = "cache\\footer_info_cache.json"
SCREENSHOT_CACHE_FILEPATH = "cache_screenshot"
SCREENSHOT_CACHE_FILEPATH_TMP_DB_NAME = "tmp_db.json"
SCREENSHOT_CACHE_FILEPATH_TMP_DB_ALL_FILES_NAME = "tmp_db_json_all_files.json"

OUTDATE_DAY_TO_DELETE_SCREENSHOTS_CACHE_CONVERTED_TO_VID = 2
OUTDATE_DAY_TO_DELETE_SCREENSHOTS_CACHE_CONVERTED_TO_VID_WITHOUT_IMGEMB = 2
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
    "deep_linking",
]

DEBUGMODE_TRIGGER = "DEBUGMODE.txt"

# add ocr test set config here
OCR_BENCHMARK_TEST_SET = {
    "zh-Hans-CN": {
        "image_path": "__assets__\\OCR_test_1080_zh-Hans-CN.png",
        "verify_text_path": "__assets__\\OCR_test_1080_words_zh-Hans-CN.txt",
    },
    "en-US": {
        "image_path": "__assets__\\OCR_test_1080_en-US.png",
        "verify_text_path": "__assets__\\OCR_test_1080_words_en-US.txt",
    },
    "ja-jp": {
        "image_path": "__assets__\\OCR_test_1080_ja-jp.png",
        "verify_text_path": "__assets__\\OCR_test_1080_words_ja-jp.txt",
    },
    "fallback": {
        "image_path": "__assets__\\OCR_test_1080_en-US.png",
        "verify_text_path": "__assets__\\OCR_test_1080_words_en-US.txt",
    },
}

OCR_SUPPORT_CONFIG = {
    "Windows.Media.Ocr.Cli": {"support_lang_option": []},
    "ChineseOCR_lite_onnx": {"support_lang_option": ["en-US, zh-Hans, zh-Hant"]},
    "PaddleOCR": {"support_lang_option": ["en-US, zh-Hans, zh-Hant"]},
}
