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

LLM_FAIL_COPY = "System: Fail to get AI reply, please try again."
LLM_SYSTEM_PROMPT_DEFAULT = "You are a helpful assistant."
LLM_SYSTEM_PROMPT_EXTRACT_DAY_TAGS = """
You are a screen content analysis assistant. Please extract the specific activity content tags under the "content_page_name" column based on the provided user's screen time list csv table for the day.
### rules:
1. Please focus on the activity content itself, such as what content was browsed/read/watch/interact, rather than the program process name.
2. The content of the label should be meaningful, otherwise it is unnecessary.
3. Don't similar content tags, just keep one or merge them.
4. Avoid repeating content platforms multiple times, more **focus on actual and meaningful content** itself. (not like youtube, bilibili, acfun, quora, reddit, zhihu, weibo etc.)
5. Tags might not to be short; slightly longer phrases can be used if necessary.
6. Generated tags should not be too general and should closely match or quote or shorten the content.
7. The extracted weight could be related to the screen time in the "screen_time" column as much as possible: the longer the usage time, the higher the content weight.
8. The number of returned tags is controlled to under 15. It is better to have less than more, depends on the content.

Only output the extracted results, and the tags are separated by English commas.
Do not attach any other instructions. Please generate the return in the language of the provided content.
"""
LLM_TEMPERATURE_EXTRACT_DAY_TAGS = 0.3

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
    "Windows.Media.Ocr.Cli": {
        "support_lang_option": {},
        "support_multiple_languages": False,
        "cost_process_second_per_minute_video": 5,
    },
    "ChineseOCR_lite_onnx": {
        "support_lang_option": {"en-US, zh-Hans, zh-Hant": "en-US, zh-Hans, zh-Hant"},
        "support_multiple_languages": False,
        "cost_process_second_per_minute_video": 25,
    },
    "PaddleOCR": {
        "support_lang_option": {"en-US, zh-Hans, zh-Hant": "en-US, zh-Hans, zh-Hant"},
        "support_multiple_languages": False,
        "cost_process_second_per_minute_video": 25,
    },
    "WeChatOCR": {
        "support_lang_option": {"en-US, zh-Hans, zh-Hant": "en-US, zh-Hans, zh-Hant"},
        "support_multiple_languages": False,
        "cost_process_second_per_minute_video": 5,
    },
    "TesseractOCR": {
        "support_lang_option": {
            "afr": "Afrikaans",
            "amh": "Amharic",
            "ara": "Arabic",
            "asm": "Assamese",
            "aze": "Azerbaijani",
            "aze_cyrl": "Azerbaijani-Cyrilic",
            "bel": "Belarusian",
            "ben": "Bengali",
            "bod": "Tibetan",
            "bos": "Bosnian",
            "bre": "Breton",
            "bul": "Bulgarian",
            "cat": "Catalan;Valencian",
            "ceb": "Cebuano",
            "ces": "Czech",
            "chi_sim": "Chinese-Simplified",
            "chi_tra": "Chinese-Traditional",
            "chr": "Cherokee",
            "cos": "Corsican",
            "cym": "Welsh",
            "dan": "Danish",
            "dan_frak": "Danish-Fraktur(contrib)",
            "deu": "German",
            "deu_frak": "German-Fraktur(contrib)",
            "deu_latf": "German(FrakturLatin)",
            "dzo": "Dzongkha",
            "ell": "Greek,Modern(1453-)",
            "eng": "English",
            "enm": "English,Middle(1100-1500)",
            "epo": "Esperanto",
            "equ": "Math/equationdetectionmodule",
            "est": "Estonian",
            "eus": "Basque",
            "fao": "Faroese",
            "fas": "Persian",
            "fil": "Filipino(old-Tagalog)",
            "fin": "Finnish",
            "fra": "French",
            "frk": "German-Fraktur(nowdeu_latf)",
            "frm": "French,Middle(ca.1400-1600)",
            "fry": "WesternFrisian",
            "gla": "ScottishGaelic",
            "gle": "Irish",
            "glg": "Galician",
            "grc": "Greek,Ancient(to1453)(contrib)",
            "guj": "Gujarati",
            "hat": "Haitian;HaitianCreole",
            "heb": "Hebrew",
            "hin": "Hindi",
            "hrv": "Croatian",
            "hun": "Hungarian",
            "hye": "Armenian",
            "iku": "Inuktitut",
            "ind": "Indonesian",
            "isl": "Icelandic",
            "ita": "Italian",
            "ita_old": "Italian-Old",
            "jav": "Javanese",
            "jpn": "Japanese",
            "kan": "Kannada",
            "kat": "Georgian",
            "kat_old": "Georgian-Old",
            "kaz": "Kazakh",
            "khm": "CentralKhmer",
            "kir": "Kirghiz;Kyrgyz",
            "kmr": "Kurmanji(Kurdish-LatinScript)",
            "kor": "Korean",
            "kor_vert": "Korean(vertical)",
            "kur": "Kurdish(ArabicScript)",
            "lao": "Lao",
            "lat": "Latin",
            "lav": "Latvian",
            "lit": "Lithuanian",
            "ltz": "Luxembourgish",
            "mal": "Malayalam",
            "mar": "Marathi",
            "mkd": "Macedonian",
            "mlt": "Maltese",
            "mon": "Mongolian",
            "mri": "Maori",
            "msa": "Malay",
            "mya": "Burmese",
            "nep": "Nepali",
            "nld": "Dutch;Flemish",
            "nor": "Norwegian",
            "oci": "Occitan(post1500)",
            "ori": "Oriya",
            "osd": "Orientationandscriptdetectionmodule",
            "pan": "Panjabi;Punjabi",
            "pol": "Polish",
            "por": "Portuguese",
            "pus": "Pushto;Pashto",
            "que": "Quechua",
            "ron": "Romanian;Moldavian;Moldovan",
            "rus": "Russian",
            "san": "Sanskrit",
            "sin": "Sinhala;Sinhalese",
            "slk": "Slovak",
            "slk_frak": "Slovak-Fraktur(contrib)",
            "slv": "Slovenian",
            "snd": "Sindhi",
            "spa": "Spanish;Castilian",
            "spa_old": "Spanish;Castilian-Old",
            "sqi": "Albanian",
            "srp": "Serbian",
            "srp_latn": "Serbian-Latin",
            "sun": "Sundanese",
            "swa": "Swahili",
            "swe": "Swedish",
            "syr": "Syriac",
            "tam": "Tamil",
            "tat": "Tatar",
            "tel": "Telugu",
            "tgk": "Tajik",
            "tgl": "Tagalog(new-Filipino)",
            "tha": "Thai",
            "tir": "Tigrinya",
            "ton": "Tonga",
            "tur": "Turkish",
            "uig": "Uighur;Uyghur",
            "ukr": "Ukrainian",
            "urd": "Urdu",
            "uzb": "Uzbek",
            "uzb_cyrl": "Uzbek-Cyrilic",
            "vie": "Vietnamese",
            "yid": "Yiddish",
            "yor": "Yoruba",
        },
        "support_multiple_languages": True,
        "cost_process_second_per_minute_video": 10,
    },
}
