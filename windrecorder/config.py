import json
import os

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
    



def get_config_json():
    with open('config.json', 'r', encoding='utf-8') as f:
        config_json = json.load(f)
    return config_json

    

config = Config(**get_config_json())