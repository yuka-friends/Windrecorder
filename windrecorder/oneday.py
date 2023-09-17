import os
import datetime
import re

import pandas as pd
import numpy as np

import windrecorder.utils as utils
import windrecorder.files as files
from windrecorder.dbManager import dbManager
from windrecorder.config import config


# 一天之时功能模块
class OneDay:
    def __init__(self):
        pass


    # 在数据库中搜索当天所有关于xx的数据
    def search_day_data(self,dt_in, search_content = ""):
        # 入参：查询时间，搜索内容
        search_date_range_in = dt_in.replace(hour=0, minute=0, second=0, microsecond=0)
        search_date_range_out = dt_in.replace(hour=23, minute=59, second=59, microsecond=0)
        page_index = 0
        df,_,_ = dbManager.db_search_data(search_content, search_date_range_in, search_date_range_out,page_index,is_p_index_used=False) # 不启用页数限制，以返回所有结果
        return df


    # 检查当天数据索引情况
    def checkout(self, dt_in):
        # 获取输入的时间
        # dt_in 的输入格式：datetime.datetime

        # 划定日期范围，取得其中所有数据
        # search_content = ""
        # search_date_range_in = dt_in.replace(hour=0, minute=0, second=0, microsecond=0)
        # search_date_range_out = dt_in.replace(hour=23, minute=59, second=59, microsecond=0)
        # page_index = 0
        # # 获取当日所有的索引信息
        # df,_,_ = dbManager.db_search_data(search_content, search_date_range_in, search_date_range_out,page_index,is_p_index_used=False) # 不启用页数限制，以返回所有结果
        df = OneDay().search_day_data(dt_in)

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
    def get_day_statistic_chart_overview(self,df,start,end):
        # 入参：df、开始小时数、结束小时数
        if start == end:
            end += 1
        
        # 复制一份表，然后把视频文件名的时间都转成x.x的格式用于统计
        df_B = df.copy()
        df_B['videofile_time'] = df_B['videofile_time'].apply(utils.seconds_to_24numfloat)
      
        # 新建一份表，统计每个时间段中有多少视频
        df_C = pd.DataFrame(columns=['hour', 'data'])
        for step in np.arange(float(start), float(end),0.1):
            filtered = df_B[(df_B['videofile_time'] >= step) & (df_B['videofile_time'] < step + 0.1)]
            df_C.loc[len(df_C)] = [step, len(filtered)]
        
        df_C['hour'] = df_C['hour'].round(1)
        # df_C['hour'] = df_C['hour'].apply(int)
        
        return df_C


    # 当输入时间戳时，查询最近的视频文件，同时检查是否为合法的对应范围（通过config 录制视频时间长度来比对）
    # 以寻找视频文件的方式
    def find_closest_video_by_filesys(self,target_datetime):
        # 获取视频文件名列表 
        video_files = os.listdir(config.record_videos_dir)

        # 提取视频文件名中的时间信息
        file_times = []
        for f in video_files:
            match = re.match(r'(\d{4}-\d{2}-\d{2}_\d{2}-\d{2}-\d{2})', f)
            if match:
                file_dt = datetime.datetime.strptime(match.group(1), '%Y-%m-%d_%H-%M-%S')
                if file_dt < target_datetime: 
                    file_times.append((f, file_dt))

        # 寻找时间距离target_datetime最近的先前时间的视频文件
        closest_file = max(file_times, key=lambda x: x[1]) 

        # 判断时间差是否在阈值内 
        time_diff = abs(closest_file[1] - target_datetime).total_seconds()
        if time_diff > config.record_seconds:
           return False, None
        else:
           return True, closest_file[0]

    # 同上功能，但以搜索数据库的方式
    def find_closest_video_by_database(self,df, time):
        # Find the closest previous time in the dataframe
        prev_time = df['videofile_time'].iloc[(df['videofile_time'] - time).abs().argsort()[:1]].values[0]
        # Check if difference is less than CONFIG seconds
        if time - prev_time < config.record_seconds:
            # Return video name if difference is small enough
            row = df.loc[df['videofile_time'] == prev_time]
            # 只返回时间戳
            # return True, df.loc[df['videofile_time'] == prev_time, 'videofile_name'].values[0]
            return True, row
        else:
            return False, None


    # 通过输入的数据库与index、找到是否有视频文件、返回其时间戳与视频文件名
    def get_result_df_video_time(self,df,index):
        video_name = df.loc[index, 'videofile_name']
        video_search_result_timestamp = df.loc[index, 'videofile_time']
        check_on_disk_path = files.check_video_exist_in_videos_dir(video_name)
        if check_on_disk_path == None:
            # 磁盘上没有文件
            return False,video_name,None
        else:
            # 磁盘上有视频文件
            video_name_timestamp = utils.calc_vid_name_to_timestamp(video_name)
            local_video_timestamp = video_search_result_timestamp - video_name_timestamp
            return True,check_on_disk_path,local_video_timestamp






