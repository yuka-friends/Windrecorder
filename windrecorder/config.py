import json
import os
import shutil

class Config:
    def __init__(
        self,
        db_path, 
        db_filename,
        record_videos_dir,
        record_seconds,
        lang,
        ocr_engine,
        max_page_result,
        target_screen_res,
        exclude_words,
        config_vid_store_day,
        OCR_index_strategy,
        wordcloud_result_dir,
        screentime_not_change_to_pause_record,
        show_oneday_wordcloud,
        timeline_result_dir,
        user_name,
        **other_field
    ) -> None:
        self.db_path = db_path
        self.db_filename = db_filename
        self.db_filepath = os.path.join(self.db_path, self.db_filename)
        self.record_videos_dir = record_videos_dir
        self.record_seconds = record_seconds
        self.lang = lang
        self.ocr_engine = ocr_engine
        self.max_page_result = max_page_result
        self.target_screen_res = target_screen_res
        self.exclude_words = exclude_words
        self.config_vid_store_day = config_vid_store_day
        self.OCR_index_strategy = OCR_index_strategy # 0=不自动索引，1=每录制完一个切片进行索引
        self.wordcloud_result_dir = wordcloud_result_dir
        self.screentime_not_change_to_pause_record = screentime_not_change_to_pause_record
        self.show_oneday_wordcloud = show_oneday_wordcloud
        self.timeline_result_dir = timeline_result_dir
        self.user_name = user_name
    
    def set_and_save_config(self, attr: str, value):
        if not hasattr(self, attr):
            raise AttributeError("{} not exist in config!".format(attr))
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
        with open('config.json', 'w', encoding='utf-8') as f:
            json.dump(config_json, f, indent=2, ensure_ascii=False)
    
    def filter_unwanted_field(self, config_json):
        del config_json["db_filepath"]
        return config_json
    


def initialize_config():
    if not os.path.exists(config_path):
        print(f"-未找到用户配置文件，将进行创建。")
        default_config_path = os.path.join(config_dir,config_name_default)
        shutil.copyfile(default_config_path,config_path)




def get_config_json():
    initialize_config()
    with open(config_path, 'r', encoding='utf-8') as f:
        config_json = json.load(f)
    return config_json

    
config_name = 'config_user.json'
config_name_default = 'config_default.json'
config_dir = 'config'
config_path = os.path.join(config_dir,config_name)

config = Config(**get_config_json())