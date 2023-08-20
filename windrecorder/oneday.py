import pandas as pd

import windrecorder.utils as utils
import windrecorder.files as files
from windrecorder.dbManager import dbManager
from windrecorder.config import config


# 一天之时功能模块
class OneDay:
    def __init__(self):
        pass

    def checkout(self, dt_in):
        # 获取输入的时间
        # dt_in 的输入格式：datetime.datetime
        # now = datetime.datetime.now()
        search_content = ""
        search_date_range_in = dt_in.replace(hour=0, minute=0, second=0, microsecond=0)
        search_date_range_out = dt_in.replace(hour=23, minute=59, second=59, microsecond=0)
        page_index = 0
        # 获取当日所有的索引信息
        df,_,_ = dbManager.db_search_data(search_content, search_date_range_in, search_date_range_out,page_index,is_p_index_used=False) # 不启用页数限制，以返回所有结果

        # 获得结果数量
        search_result_num = len(df)

        if search_result_num < 2:
            # 没有结果的处理
            print("none")
            
            _, noocred_count = files.get_videos_and_ocred_videos_count(config.record_videos_dir)
            return False,noocred_count,0,None,None,None
        else:
            # 有结果 - 返回其中最早、最晚的结果，以写入slider；提供总索引数目、未索引数量
            min_timestamp = df['videofile_time'].min()
            max_timestamp = df['videofile_time'].max()
            min_timestamp_dt = utils.seconds_to_datetime(min_timestamp)
            max_timestamp_dt = utils.seconds_to_datetime(max_timestamp)
            _, noocred_count = files.get_videos_and_ocred_videos_count(config.record_videos_dir)
            return True,noocred_count-1,search_result_num,min_timestamp_dt,max_timestamp_dt,df
        # 返回：当天是否有数据、没有索引的文件数量、搜索结果总数、最早时间datetime、最晚时间datetime、df
    

    # 获得当天表中的时间轴统计数据
    def get_day_statistic_chart(self,df,start,end):
        # 入参：df、开始小时数、结束小时数
        if start == end:
            end += 1
        
        df_B = df.copy()
        df_B['videofile_time'] = df_B['videofile_time'].apply(utils.seconds_to_24numfloat)
      
        df_C = pd.DataFrame(columns=['hour', 'data'])
        for step in range(int(start), int(end)):
          filtered = df_B[(df_B['videofile_time'] >= step) & (df_B['videofile_time'] < step + 0.5)]
          df_C.loc[len(df_C)] = [step, len(filtered)]
      
        return df_C





