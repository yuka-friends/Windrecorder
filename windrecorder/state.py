import os
import datetime
import calendar

import pandas as pd
import numpy as np

import windrecorder.utils as utils
from windrecorder.dbManager import DBManager
from windrecorder.config import config


# 统计当月数据概览
def get_month_data_overview(dt:datetime.datetime):
    month_days = calendar.monthrange(dt.year, dt.month)[1]

    df_month_data = pd.DataFrame(columns=['day', 'data_count'])
    for day in range(1, month_days+1):
        day_datetime_start = datetime.datetime(dt.year, dt.month, day, 0,0,1)
        day_datetime_end = datetime.datetime(dt.year, dt.month, day, 23,59,59)

        df,_,_ = DBManager().db_search_data("",day_datetime_start,day_datetime_end)

        row_count = len(df)
        df_month_data.loc[day-1] = [day, row_count]
    
    return df_month_data


# 统计全年数据概览
def get_year_data_overview(dt:datetime.datetime):
    months_count = 12

    df_year_data = pd.DataFrame(columns=['month', 'data_count'])
    for month in range(1, months_count+1):
        month_days = calendar.monthrange(dt.year, month)[1]
        dt_month_start = datetime.datetime(dt.year,month,1,0,0,1)
        dt_month_end = datetime.datetime(dt.year,month,month_days,23,23,59)

        df,_,_ = DBManager().db_search_data("",dt_month_start,dt_month_end)

        row_count = len(df)
        df_year_data.loc[month-1] = [month, row_count]
    
    return df_year_data
