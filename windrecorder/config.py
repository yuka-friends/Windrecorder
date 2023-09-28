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
        vid_store_day,
        vid_compress_day,
        OCR_index_strategy,
        wordcloud_result_dir,
        screentime_not_change_to_pause_record,
        show_oneday_wordcloud,
        timeline_result_dir,
        user_name,
        use_similar_ch_char_to_search,
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
        self.vid_store_day = vid_store_day
        self.vid_compress_day = vid_compress_day
        self.OCR_index_strategy = OCR_index_strategy # 0=不自动索引，1=每录制完一个切片进行索引
        self.wordcloud_result_dir = wordcloud_result_dir
        self.screentime_not_change_to_pause_record = screentime_not_change_to_pause_record
        self.show_oneday_wordcloud = show_oneday_wordcloud
        self.timeline_result_dir = timeline_result_dir
        self.user_name = user_name
        self.use_similar_ch_char_to_search = use_similar_ch_char_to_search
    
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
        with open(config_path, 'w', encoding='utf-8') as f:
            json.dump(config_json, f, indent=2, ensure_ascii=False)
    
    def filter_unwanted_field(self, config_json):
        del config_json["db_filepath"]
        return config_json
    






config_name = 'config_user.json'
config_name_default = 'config_default.json'
config_dir = 'config'
config_path = os.path.join(config_dir,config_name)






# 从default config中更新user config（升级用）
def update_config_files_from_default_to_user(
        a_path = os.path.join(config_dir, config_name_default), 
        b_path =  os.path.join(config_dir, config_name)
        ):
    # 读取A.json文件
    with open(a_path, 'r', encoding='utf-8') as a_file:
        a_data = json.load(a_file)
    # 读取B.json文件
    with open(b_path, 'r', encoding='utf-8') as b_file:
        b_data = json.load(b_file)
    # 将A中有的、B中没有的属性从A写入B中
    for key, value in a_data.items():
        if key not in b_data:
            b_data[key] = value
    # 将A中没有的、B中有的属性从B中删除
    keys_to_remove = [key for key in b_data.keys() if key not in a_data]
    for key in keys_to_remove:
        del b_data[key]
    # 将更新后的B数据写入B.json文件
    with open(b_path, 'w', encoding='utf-8') as b_file:
        json.dump(b_data, b_file, indent=2, ensure_ascii=False)
    

def initialize_config():
    if not os.path.exists(config_path):
        print(f"-未找到用户配置文件，将进行创建。")
        default_config_path = os.path.join(config_dir,config_name_default)
        shutil.copyfile(default_config_path,config_path)


def get_config_json():
    update_config_files_from_default_to_user()
    initialize_config()
    with open(config_path, 'r', encoding='utf-8') as f:
        config_json = json.load(f)
    return config_json



    


config = Config(**get_config_json())