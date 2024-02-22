import datetime
import math
import os
import shutil
import sqlite3
from itertools import product
from subprocess import CalledProcessError

import numpy as np
import pandas as pd

import windrecorder.utils as utils
from windrecorder import file_utils
from windrecorder.config import config
from windrecorder.logger import get_logger

logger = get_logger(__name__)


class _DBManager:
    def __init__(self, db_path, db_max_page_result, user_name):
        self.db_path = db_path  # 存放数据库的目录
        file_utils.ensure_dir(self.db_path)
        self.db_max_page_result = db_max_page_result  # 最大查询页数
        self.user_name = user_name  # 用户名
        self._db_filename_dict = self._init_db_filename_dict()

        self.db_main_initialize()
        self.db_update_table_product_routine()  # 程序更新后调整数据结构

    # 根据传入的时间段取得对应数据库的文件名词典
    def db_get_dbfilename_by_datetime(self, db_query_datetime_start, db_query_datetime_end):
        db_query_datetime_start_YMD = utils.set_full_datetime_to_YYYY_MM(db_query_datetime_start)
        db_query_datetime_end_YMD = utils.set_full_datetime_to_YYYY_MM(db_query_datetime_end)

        result = []
        for key, value in self.get_db_filename_dict().items():
            if db_query_datetime_start_YMD <= value <= db_query_datetime_end_YMD:
                result.append(key)
        return result

    # ___
    # 初始化对应时间的数据库流程
    def db_main_initialize(self):
        logger.info("Initialize the database...")
        db_filepath_today = file_utils.get_db_filepath_by_datetime(datetime.datetime.today())

        # 初始化最新的数据库
        conn_check = self.db_initialize(db_filepath_today)

        return conn_check

    # 初始化数据库：检查、创建、连接入参数据库对象，如果内容为空，则创建表初始化
    def db_initialize(self, db_filepath):
        is_db_exist = os.path.exists(db_filepath)

        # 检查数据库是否存在
        if not is_db_exist:
            logger.info("db not existed")
            if not os.path.exists(self.db_path):
                os.mkdir(self.db_path)
                logger.info("db dir not existed, mkdir")
            db_filename = os.path.basename(db_filepath)
            self._db_filename_dict[db_filename] = utils.extract_date_from_db_filename(db_filename)

        conn = sqlite3.connect(db_filepath)
        c = conn.cursor()
        c.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='video_text'")

        if c.fetchone() is None:
            logger.info("db is empty, writing new table.")
            self.db_create_table(db_filepath)
            now = datetime.datetime.now()
            now_name = now.strftime("%Y-%m-%d_%H-%M-%S")
            now_time = int(utils.date_to_seconds(now_name))
            # default_base64 = "iVBORw0KGgoAAAANSUhEUgAAAEYAAAAnCAYAAACyhj57AAAAoUlEQVRoBe3BAQEAAAwBMCrpp6RCHkCFb7RSvEErxRu0UrxBK8UbtFK8QSvFG7RSvEErxRu0UrxBK8UbtFK8QSvFG7RSvEErxRu0UrxBK8UbtFK8QSvFG7RSvEErxRu0UrxBK8UbtFK8QSvFG7RSvEErxRu0UrxBK8UbtFK8QSvFG7RSvEErxRu0UrxBK8UbtFK8QSvFG7RSvEErxRu0UrxxUOdhqPjngTYAAAAASUVORK5CYII="
            self.db_update_data(
                now_name + ".mp4",
                "0.jpg",
                now_time,
                "Welcome! Go to Setting and Update your screen recording files.",
                False,
                False,
                None,
                None,
            )
        else:
            logger.info("db existed and not empty")

        return is_db_exist

    # 重新读取配置文件
    def db_update_read_config(self, config):
        self.db_max_page_result = int(config.max_page_result)

    # 检查 column_name 列是否存在，若无则新增
    def db_ensure_row_exist(self, db_filepath, column_name, column_type, table_name="video_text"):
        conn = sqlite3.connect(db_filepath)
        cursor = conn.cursor()

        # 查询表信息
        cursor.execute(f"PRAGMA table_info({table_name});")
        table_info = cursor.fetchall()

        # 检查新列是否已存在
        if column_name not in [column[1] for column in table_info]:
            # 新列不存在，添加新列
            cursor.execute(f"ALTER TABLE {table_name} ADD COLUMN {column_name} {column_type};")
            logger.info(f"Column {column_name} added to {table_name}.")
        else:
            logger.debug(f"Column {column_name} already exists in {table_name}.")

        # 提交更改并关闭连接
        conn.commit()
        cursor.close()
        conn.close()

    # 根据程序更新调整原有数据表结构
    def db_update_table_product_routine(self):
        for key, value in self._db_filename_dict.items():
            db_filepath = os.path.join(self.db_path, key)

            # 新增了记录前台进程名功能，需要增加一列 win_title TEXT
            self.db_ensure_row_exist(
                db_filepath=db_filepath, column_name="win_title", column_type="TEXT", table_name="video_text"
            )

    # 创建表
    def db_create_table(self, db_filepath):
        logger.info("Making table")
        conn = sqlite3.connect(db_filepath)
        conn.execute(
            """CREATE TABLE video_text
                   (videofile_name VARCHAR(100),
                   picturefile_name VARCHAR(100),
                   videofile_time INT,
                   ocr_text TEXT,
                   is_videofile_exist BOOLEAN,
                   is_picturefile_exist BOOLEAN,
                   thumbnail TEXT,
                   win_title TEXT);"""
        )
        conn.close()

    # 插入数据
    def db_update_data(
        self,
        videofile_name,
        picturefile_name,
        videofile_time,
        ocr_text,
        is_videofile_exist,
        is_picturefile_exist,
        thumbnail,
        win_title,
    ):
        logger.info("Inserting data")
        # 使用方法：db_update_data(db_filepath,'video1.mp4','iframe_0.jpg', 120, 'text from ocr', True, False, "window_title")

        # 获取插入时间，取得对应的数据库
        insert_db_datetime = utils.set_full_datetime_to_YYYY_MM(utils.seconds_to_datetime(videofile_time))
        db_filepath = file_utils.get_db_filepath_by_datetime(insert_db_datetime)  # 直接获取对应时间的数据库路径

        conn = sqlite3.connect(db_filepath)
        c = conn.cursor()

        c.execute(
            "INSERT INTO video_text (videofile_name, picturefile_name, videofile_time, ocr_text, is_videofile_exist, is_picturefile_exist, thumbnail, win_title) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (
                videofile_name,
                picturefile_name,
                videofile_time,
                ocr_text,
                is_videofile_exist,
                is_picturefile_exist,
                thumbnail,
                win_title,
            ),
        )
        conn.commit()
        conn.close()

    # 以df入参形式批量插入新数据，考虑到跨月数据库处理的流程
    def db_add_dataframe_to_db_process(self, dataframe):
        if len(dataframe) < 2:
            return
        # 寻找db中最大最小时间戳，以确定需要插入的数据库
        # 如果都在同一个月，则插入当月的数据库文件；如果在不同月，则找到分歧点后分开插入
        max_timestamp, min_timestamp = self.db_get_dataframe_max_min_videotimestamp(dataframe)
        max_datetime = utils.seconds_to_datetime(max_timestamp)
        min_datetime = utils.seconds_to_datetime(min_timestamp)

        if max_datetime.month == min_datetime.month:
            database_path = file_utils.get_db_filepath_by_datetime(max_datetime)
            self.db_add_dataframe_to_db(database_path, dataframe)
        else:
            # 分流处理
            neariest_timestamp = utils.datetime_to_seconds(
                datetime.datetime(max_datetime.year, max_datetime.month, 1, 0, 0, 1)
            )  # 以最大月第一天作为分割线
            df_before, df_after = self.split_dataframe_by_nearest_timestamp(dataframe, neariest_timestamp)  # 以此时间点分为两部分df
            database_path_before = file_utils.get_db_filepath_by_datetime(min_datetime)  # 获取两部分的数据库
            database_path_after = file_utils.get_db_filepath_by_datetime(min_datetime)  # 获取两部分的数据库
            # 由于出现在新的一月开头，所以得先初始下新月的数据库
            self.db_initialize(database_path_after)

            self.db_add_dataframe_to_db(database_path_before, df_before)
            self.db_add_dataframe_to_db(database_path_after, df_after)

    # 将df插入到数据库中
    def db_add_dataframe_to_db(self, database_path, dataframe):
        conn = sqlite3.connect(database_path)

        # 设置数据类型映射，确保列的数据类型在写入数据库时不会出错
        dtypes_dict = {
            "videofile_name": "VARCHAR(100)",
            "picturefile_name": "VARCHAR(100)",
            "videofile_time": "INT",
            "ocr_text": "TEXT",
            "is_videofile_exist": "BOOLEAN",
            "is_picturefile_exist": "BOOLEAN",
            "thumbnail": "TEXT",
            "win_title": "TEXT",
        }

        # 将dataframe的数据写入数据库的video_text表中
        dataframe.to_sql("video_text", conn, if_exists="append", index=False, dtype=dtypes_dict)

        # 提交更改并关闭连接
        conn.commit()
        conn.close()

    # 寻找df中最大最小时间戳
    def db_get_dataframe_max_min_videotimestamp(self, df: pd.DataFrame) -> tuple:
        max_timestamp = df["videofile_time"].max()
        min_timestamp = df["videofile_time"].min()
        return max_timestamp, min_timestamp

    # 找到df中的一个最接近的时间戳并将其划分开来
    def split_dataframe_by_nearest_timestamp(self, df: pd.DataFrame, nearest_timestamp: int) -> tuple:
        # 找到最接近的时间戳
        nearest_index = abs(df["videofile_time"] - nearest_timestamp).idxmin()

        # 将数据帧分为前后两部分
        df_before = df.loc[:nearest_index]  # 包含与时间戳最接近的行
        df_after = df.loc[nearest_index + 1 :]
        return df_before, df_after

    def db_search_data(self, keyword_input, date_in, date_out, keyword_input_exclude=""):
        """
        查询选定日期当天的关键词数据，返回完整的结果 dataframe
        返回值：关于结果的所有数据 df，所有结果的总行数

        :param keyword_input: str 关键词
        :param date_in: datetime.datetime 开始时间范围
        :param date_out: datetime.datetime 结束时间范围
        :param keyword_input_exclude: str 排除词
        """
        logger.info("Querying keywords")
        # 初始化查询数据
        self.db_update_read_config(config)
        date_in_ts = int(utils.date_to_seconds(date_in.strftime("%Y-%m-%d_%H-%M-%S")))
        date_out_ts = int(utils.date_to_seconds(date_out.strftime("%Y-%m-%d_%H-%M-%S")))
        # date_in_ts = int(utils.date_to_seconds(date_in.strftime("%Y-%m-%d_00-00-00")))
        # date_out_ts = int(utils.date_to_seconds(date_out.strftime("%Y-%m-%d_23-59-59")))

        if date_in_ts == date_out_ts:
            date_out_ts += 1

        # 获得对应时间段下涉及的所有数据库
        datetime_start = utils.seconds_to_datetime(date_in_ts)
        datetime_end = utils.seconds_to_datetime(date_out_ts)
        query_db_name_list = self.db_get_dbfilename_by_datetime(datetime_start, datetime_end)
        logger.info(f"{datetime_start=}, {datetime_end=}")

        # 遍历查询所有数据库信息
        df_all = pd.DataFrame()
        row_count = 0
        for key in query_db_name_list:
            db_filepath_origin = os.path.join(self.db_path, key)  # 构建完整路径
            db_filepath = self.get_temp_dbfilepath(db_filepath_origin)  # 检查/创建临时查询用的数据库
            logger.info(f"Querying {db_filepath}")

            conn = sqlite3.connect(db_filepath)  # 连接数据库

            # 构建sql
            keywords = keyword_input.split()  # 用空格分割所有的关键词，存为list
            query = "SELECT * FROM video_text WHERE "

            if not keyword_input.isspace() and keyword_input:  # 关键词不为空时
                # 每个关键词执行相近字形匹配（配置项开）
                if config.use_similar_ch_char_to_search:
                    # 查询每个关键词的相近字形结果，获得总共需要搜索的条目
                    similar_strings_list = []
                    for keyword in keywords:
                        similar_strings = self.generate_similar_ch_strings(keyword)
                        similar_strings_list.append(similar_strings)

                    # 构建所有关键词的sql
                    conditions = []
                    for keywords in similar_strings_list:
                        group_condition = " OR ".join(f"ocr_text LIKE '%{keyword}%'" for keyword in keywords)
                        conditions.append(f"({group_condition})")

                    query = query + " AND ".join(conditions)
                    # 输出参考：(ocr_text LIKE '%a1%' AND ocr_text LIKE '%a2%' AND ocr_text LIKE '%a3%') OR (ocr_text LIKE '%b1%' AND ocr_text LIKE '%b2%') OR (ocr_text LIKE '%c%');

                else:
                    # 不使用相近字形搜索：直接遍历所有空格区分开的关键词
                    conditions = []
                    for keyword in keywords:
                        conditions.append(f"ocr_text LIKE '%{keyword}%'")
                    query += " AND ".join(conditions)

            else:  # 关键词为空
                query += f"ocr_text LIKE '%{keyword_input}%'"

            # 是否排除关键词
            if keyword_input_exclude and not keyword_input_exclude.isspace():
                query += " AND "
                keywords_exclude = keyword_input_exclude.split()
                conditions = []
                for keyword_exclude in keywords_exclude:
                    conditions.append(f"ocr_text NOT LIKE '%{keyword_exclude}%'")
                query += " AND ".join(conditions)

            # 限定查询的时间范围
            query += f" AND (videofile_time BETWEEN {date_in_ts} AND {date_out_ts})"

            logger.info(f"SQL query:\n {query}")
            df = pd.read_sql_query(query, conn)

            # 查询所有关键词和时间段下的结果
            # if keyword_input_exclude:
            #     df = pd.read_sql_query(f"""
            #                           SELECT * FROM video_text
            #                           WHERE ocr_text LIKE '%{keyword_input}%'
            #                           AND ocr_text NOT LIKE '%{keyword_input_exclude}%'
            #                           AND videofile_time BETWEEN {date_in_ts} AND {date_out_ts} """
            #                            , conn)
            # else:
            #     df = pd.read_sql_query(f"""
            #                           SELECT * FROM video_text
            #                           WHERE ocr_text LIKE '%{keyword_input}%'
            #                           AND videofile_time BETWEEN {date_in_ts} AND {date_out_ts} """
            #                            , conn)

            df_all = pd.concat([df_all, df], ignore_index=True)
            conn.close()

        row_count = len(df_all)
        page_count_all = int(math.ceil(int(row_count) / int(self.db_max_page_result)))

        return df_all, row_count, page_count_all

    # 拿到完整df后进行翻页检索操作
    def db_search_data_page_turner(self, df, page_index):
        # page_index 从 1 计起
        row_count = len(df)  # 总行数

        page_count = int(math.ceil(int(row_count) / int(self.db_max_page_result)))  # 根据结果与用户配置，计算需要多少页读取
        if page_count <= 1:
            page_count = 1

        row_start_index = (page_index - 1) * self.db_max_page_result
        row_end_index = row_start_index + self.db_max_page_result

        df_current_page = df[row_start_index:row_end_index]

        # 返回当前页的dataframe
        return df_current_page

    # 优化全局搜索数据结果的展示
    def db_refine_search_data_global(self, df, cache_videofile_ondisk_list=None):
        # 1. Add a new column "locate_time"
        df["locate_time"] = df.apply(
            lambda row: utils.convert_seconds_to_hhmmss(
                utils.get_video_timestamp_by_filename_and_abs_timestamp(row["videofile_name"], row["videofile_time"])
            ),
            axis=1,
        )
        df["timestamp"] = df.apply(
            lambda row: utils.seconds_to_date_goodlook_formart(row["videofile_time"]),
            axis=1,
        )
        df["thumbnail"] = "data:image/png;base64," + df["thumbnail"]

        # 磁盘上有无对应视频检测
        cache_videofile_ondisk_str = ""
        if cache_videofile_ondisk_list is None:
            cache_videofile_ondisk_str = cache_videofile_ondisk_str.join(
                file_utils.get_file_path_list(config.record_videos_dir_ud)
            )
        else:
            cache_videofile_ondisk_str = cache_videofile_ondisk_str.join(cache_videofile_ondisk_list)

        def is_videofile_ondisk(filename, video_ondisk_str):
            if filename[:19] in video_ondisk_str:
                return True
            else:
                return False

        df["videofile"] = df.apply(
            lambda row: is_videofile_ondisk(row["videofile_name"], cache_videofile_ondisk_str),
            axis=1,
        )

        # 2. Remove specified columns
        df = df.drop(columns=["picturefile_name", "is_picturefile_exist", "is_videofile_exist"])

        # 3. Rearrange columns and return the processed dataframe
        df = df[
            [
                "thumbnail",
                "timestamp",
                "win_title",
                "ocr_text",
                "videofile",
                "videofile_name",
                "locate_time",
                "videofile_time",
            ]
        ]
        return df

    # 优化一天之时数据结果的展示
    def db_refine_search_data_day(self, df, cache_videofile_ondisk_list=None):
        df["locate_time"] = df.apply(
            lambda row: utils.convert_seconds_to_hhmmss(
                utils.get_video_timestamp_by_filename_and_abs_timestamp(row["videofile_name"], row["videofile_time"])
            ),
            axis=1,
        )
        df["timestamp"] = df.apply(lambda row: utils.seconds_to_date_dayHMS(row["videofile_time"]), axis=1)
        if "data:image/png;base64," not in df["thumbnail"].iloc[0]:
            df["thumbnail"] = "data:image/png;base64," + df["thumbnail"]

        # 磁盘上有无对应视频检测
        cache_videofile_ondisk_str = ""
        if cache_videofile_ondisk_list is None:
            cache_videofile_ondisk_str = cache_videofile_ondisk_str.join(
                file_utils.get_file_path_list(config.record_videos_dir_ud)
            )
        else:
            cache_videofile_ondisk_str = cache_videofile_ondisk_str.join(cache_videofile_ondisk_list)

        def is_videofile_ondisk(filename, video_ondisk_str):
            if filename[:19] in video_ondisk_str:
                return True
            else:
                return False

        df["videofile"] = df.apply(
            lambda row: is_videofile_ondisk(row["videofile_name"], cache_videofile_ondisk_str),
            axis=1,
        )
        df = df.drop(columns=["picturefile_name", "is_picturefile_exist", "is_videofile_exist"])

        df = df[
            [
                "thumbnail",
                "timestamp",
                "win_title",
                "ocr_text",
                "videofile",
                "videofile_name",
                "locate_time",
                "videofile_time",
            ]
        ]

        return df

    # 根据视频文件名字返回对应行列 dataframe (rowid included)
    def db_get_row_from_vid_filename(self, vid_filename):
        vid_filepath = file_utils.convert_vid_filename_as_vid_filepath(vid_filename)
        vid_datetime_start = utils.date_to_datetime(vid_filename[:19])
        if os.path.exists(vid_filepath):  # 视频文件存在情况下，尝试拿其真实时长，若无用 config 录制值兜底
            try:
                vid_datetime_end = vid_datetime_start + datetime.timedelta(
                    seconds=int(float(utils.get_vidfilepath_info(vid_filepath)["duration"]))
                )
            except CalledProcessError:
                vid_datetime_end = vid_datetime_start + datetime.timedelta(seconds=config.record_seconds)
        else:
            vid_datetime_end = vid_datetime_start + datetime.timedelta(seconds=config.record_seconds)
        # 根据datetime定位数据库（考虑需跨数据库情况）
        db_name_list = self.db_get_dbfilename_by_datetime(vid_datetime_start, vid_datetime_end)

        df_origin = pd.DataFrame()
        for item in db_name_list:
            db_filepath = os.path.join(self.db_path, item)
            db_filepath = self.get_temp_dbfilepath(db_filepath)
            conn = sqlite3.connect(db_filepath)

            # 使用pandas的read_sql_query函数执行查询并将结果转换为DataFrame
            query = f"SELECT rowid, * FROM video_text WHERE videofile_name LIKE '%{vid_filename[:19]}%'"
            df = pd.read_sql_query(query, conn)

            conn.close()
            df_origin = pd.concat([df_origin, df])

        return df_origin

    def db_get_rowid_and_similar_tuple_list_rows(self, rowid_probs_list, db_filename):
        """
        根据 rowid - 相似度 元组构成的 list 提取数据库文件对应行与标注对应相似度，合在以 dataframe 形式返回
        """
        db_filepath = os.path.join(self.db_path, db_filename)
        db_filepath = self.get_temp_dbfilepath(db_filepath)
        conn = sqlite3.connect(db_filepath)
        rowid_list = [tuple[0] for tuple in rowid_probs_list]
        probs_list = [tuple[1] for tuple in rowid_probs_list]
        rowid_str = ",".join(map(str, rowid_list))  # 将 rowid 列表转换为逗号分隔的字符串

        # 构建SQL查询语句
        query = f"SELECT * FROM video_text WHERE rowid IN ({rowid_str})"
        result_df = pd.read_sql_query(query, conn)
        conn.close()

        result_df["probs"] = probs_list
        return result_df

    # 列出所有数据
    def db_list_all_data(self):
        logger.debug("List all data in all databases")
        # 获取游标
        # 使用SELECT * 从video_text表查询所有列的数据
        # 使用fetchall()获取所有结果行
        # 遍历结果行,打印出每一行
        full_db_name_ondisk_dict = self.get_db_filename_dict()
        for key, value in full_db_name_ondisk_dict.items():
            db_filepath_origin = os.path.join(self.db_path, key)
            db_filepath = self.get_temp_dbfilepath(db_filepath_origin)

            conn = sqlite3.connect(db_filepath)
            c = conn.cursor()
            c.execute("SELECT * FROM video_text")
            rows = c.fetchall()
            for row in rows:
                logger.debug(str(row))
            conn.close()

    # 查询全部数据库一共有多少行
    def db_num_records(self):
        full_db_name_ondisk_dict = self.get_db_filename_dict()
        rows_count_all = 0
        for key, value in full_db_name_ondisk_dict.items():
            db_filepath_origin = os.path.join(self.db_path, key)
            db_filepath = self.get_temp_dbfilepath(db_filepath_origin)
            conn = sqlite3.connect(db_filepath)
            c = conn.cursor()
            c.execute("SELECT COUNT(*) FROM video_text")
            rows_count = c.fetchone()[0]
            conn.close()
            rows_count_all += rows_count
            logger.info(f"db_filepath: {db_filepath}, rows_count: {rows_count}")
        logger.info(f"rows_count_all: {rows_count_all}")
        return rows_count_all

    # 获取表内最新的记录时间
    def db_latest_record_time(self):
        full_db_name_ondisk_dict = self.get_db_filename_dict()
        db_name_ondisk_lastest = utils.get_lastest_datetime_key(full_db_name_ondisk_dict)
        db_filepath_origin = os.path.join(self.db_path, db_name_ondisk_lastest)
        db_filepath = self.get_temp_dbfilepath(db_filepath_origin)

        conn = sqlite3.connect(db_filepath)
        c = conn.cursor()

        c.execute("SELECT MAX(videofile_time) FROM video_text")
        max_time = c.fetchone()[0]
        conn.close()
        return max_time  # 返回时间戳

    # 获取表内最早的记录时间
    def db_first_earliest_record_time(self):
        full_db_name_ondisk_dict = self.get_db_filename_dict()
        db_name_ondisk_lastest = utils.get_earliest_datetime_key(full_db_name_ondisk_dict)
        db_filepath_origin = os.path.join(self.db_path, db_name_ondisk_lastest)
        db_filepath = self.get_temp_dbfilepath(db_filepath_origin)

        conn = sqlite3.connect(db_filepath)
        c = conn.cursor()

        c.execute("SELECT MIN(videofile_time) FROM video_text")
        min_time = c.fetchone()[0]
        conn.close()
        return min_time  # 返回时间戳

    # 回滚操作：删除输入视频文件名相关的所有条目
    def db_rollback_delete_video_refer_record(self, videofile_name):
        logger.info(f"removing record {videofile_name}")
        # 根据文件名定位数据库文件地址
        db_filepath = file_utils.get_db_filepath_by_datetime(
            utils.set_full_datetime_to_YYYY_MM(utils.date_to_datetime(os.path.splitext(videofile_name)[0]))
        )

        conn = sqlite3.connect(db_filepath)
        c = conn.cursor()

        # 构建SQL语句，使用LIKE操作符进行模糊匹配
        sql = f"DELETE FROM video_text WHERE videofile_name LIKE '%{videofile_name}%'"
        # 精确匹配的方式
        # sql = f"DELETE FROM video_text WHERE videofile_name = '{videofile_name}'"
        c.execute(sql)
        conn.commit()
        conn.close()

    # 获取某个时间点附近最接近的一行数据
    def db_get_closest_row_around_by_datetime(self, dt: datetime.datetime, time_threshold=60):
        df, all_result_counts, _ = self.db_search_data(
            "",
            utils.get_datetime_in_day_range_pole_by_config_day_begin(dt, range="start"),
            utils.get_datetime_in_day_range_pole_by_config_day_begin(dt, range="end"),
        )
        timestamp = utils.datetime_to_seconds(dt)
        closest_timestamp = df[np.abs(df["videofile_time"] - timestamp) <= time_threshold][
            "videofile_time"
        ].max()  # 差距阈值:second
        if math.isnan(closest_timestamp):  # 如果无结果为 NaN
            return pd.DataFrame()
        row = df[df["videofile_time"] == closest_timestamp]
        return row

    # 获取某个时间的当天最早与最晚记录时间
    def db_get_time_min_and_max_through_datetime(self, dt: datetime.datetime):
        df, all_result_counts, _ = self.db_search_data(
            "",
            utils.get_datetime_in_day_range_pole_by_config_day_begin(dt, range="start"),
            utils.get_datetime_in_day_range_pole_by_config_day_begin(dt, range="end"),
        )
        time_min = df["videofile_time"].min()
        time_max = df["videofile_time"].max()
        return time_min, time_max

    # 获取一个时间段内，按时间戳等均分的几张缩略图
    def db_get_day_thumbnail_by_timeavg(self, dt_in: datetime.datetime, dt_out: datetime.datetime, back_pic_num):
        df, all_result_counts, _ = self.db_search_data("", dt_in, dt_out)

        if all_result_counts < back_pic_num:
            return None

        # 获取df内最早与最晚记录时间
        time_min = df["videofile_time"].min()
        time_max = df["videofile_time"].max()
        if time_min == time_max:
            return None

        # 计算均分时间间隔
        time_range = time_max - time_min
        time_gap = int(time_range / back_pic_num)

        # 生成理想的时间间隔表
        timestamp_list = [time_min + i * time_gap for i in range(back_pic_num + 1)]

        # 寻找最近的时间戳数据
        closest_timestamp_result = []
        for timestamp in timestamp_list:
            closest_timestamp = df[np.abs(df["videofile_time"] - timestamp) <= 300]["videofile_time"].max()  # 差距阈值:second

            if math.isnan(closest_timestamp):  # 如果无结果为 NaN
                closest_timestamp = 0
            closest_timestamp_result.append(closest_timestamp)

        # 返回对应的缩略图数据
        thumbnails_result = []
        for timestamp in closest_timestamp_result:
            if timestamp == 0:
                thumbnails_result.append(None)
            else:
                thumbnail = df[df["videofile_time"] == timestamp]["thumbnail"].values
                if len(thumbnail) > 0:
                    thumbnails_result.append(thumbnail[0])
                else:
                    thumbnails_result.append(None)

        return thumbnails_result

    # 获取一个时间段内，按数据分布等均分的几张缩略图
    def db_get_day_thumbnail_by_distributeavg(self, date_in, date_out, pic_num):
        df, all_result_counts, _ = self.db_search_data("", date_in, date_out)

        # 平均地获取结果图片，而不是平均地按时间分
        img_list = []
        thumbnails_result = df["thumbnail"].tolist()
        rows = len(df)

        if rows < pic_num:
            return None

        gap_num = all_result_counts // pic_num

        for i in range(0, rows, gap_num):
            img_list.append(thumbnails_result[i])

        return img_list

    # 相似的单个中文字符查找
    def find_similar_ch_characters(
        self, input_str, file_path=os.path.join(config.config_src_dir, "similar_CN_characters.txt")
    ):
        similar_chars = []

        with open(file_path, "r", encoding="utf-8") as file:
            lines = file.readlines()
            for line in lines:
                line = line.strip()
                characters = line.split("，")
                if input_str in characters:
                    similar_chars.extend(characters)

        similar_chars = list(set(similar_chars))
        if len(similar_chars) == 0:
            similar_chars.append(input_str)

        similar_chars = list(filter(None, similar_chars))  # 过滤空字符串内容
        return similar_chars

    # 遍历得到每种可能性
    def generate_similar_ch_strings(self, input_str):
        words = list(input_str)
        similar_words_list = [self.find_similar_ch_characters(word) for word in words]
        result = ["".join(similar_words) for similar_words in product(*similar_words_list)]

        if len(result) > 100:
            logger.info("The complexity of similar keyword combinations is too high, so do not use fuzzy queries.")
            result = [input_str]

        return result

    # 所有读的操作都访问已复制的临时数据库，不与原有数据库冲突
    def get_temp_dbfilepath(self, db_filepath):
        db_filename = os.path.basename(db_filepath)

        maintaining = os.path.isfile(config.maintain_lock_path)

        if "_TEMP_READ" not in db_filename:
            db_filename_temp = os.path.splitext(db_filename)[0] + "_TEMP_READ.db"  # 创建临时文件名
            filepath_temp_read = os.path.join(self.db_path, db_filename_temp)  # 创建读取的临时路径
            if os.path.exists(filepath_temp_read):  # 检测是否已存在临时数据库
                # 是，检查同根数据库是否更新，阈值为大于5分钟
                (
                    db_origin_newer,
                    db_timestamp_diff,
                ) = file_utils.is_fileA_modified_newer_than_fileB(db_filepath, filepath_temp_read)
                if db_origin_newer and db_timestamp_diff > 5:
                    # 过时了，复制创建一份
                    if not maintaining:  # 数据库是否正在被索引？是则用上一份，不进行复制更新。
                        shutil.copy2(db_filepath, filepath_temp_read)  # 保留原始文件的修改时间以更好地对比策略
            else:
                # 不存在临时数据库，复制创建一份
                shutil.copy2(db_filepath, filepath_temp_read)

            return filepath_temp_read  # 返回临时路径
        else:
            return filepath_temp_read

    # 检查更新数据库中的条目是否有对应视频
    def db_update_videofile_exist_status(self):
        db_file_path_dict = self.get_db_filename_dict()
        db_file_path_list = []
        video_file_path_list = file_utils.get_file_path_list(config.record_videos_dir_ud)

        for key in db_file_path_dict.keys():
            db_filepath = os.path.join(config.db_path_ud, key)
            db_file_path_list.append(db_filepath)

        # Get only first 19 characters of video files in video_file_path_list
        video_file_names = {video_file[:19]: True for video_file in video_file_path_list}

        for db_file in db_file_path_list:
            logger.info(f"checking db_file:{db_file}")
            conn = sqlite3.connect(db_file)
            cursor = conn.cursor()

            # Get all rows from database
            cursor.execute("SELECT * FROM video_text")
            rows = cursor.fetchall()

            # Get the index of the "videofile_name" column
            col_names = [description[0] for description in cursor.description]
            videofile_name_index = col_names.index("videofile_name")

            # Begin transaction to speed up the update process
            cursor.execute("BEGIN TRANSACTION")

            i = 0

            for row in rows:
                videofile_name = row[videofile_name_index]

                # Check if videofile_name exists in video_file_names using dictionary lookup
                is_videofile_exist = video_file_names.get(videofile_name[:19], False)

                # Update the is_videofile_exist column in the database
                cursor.execute(
                    "UPDATE video_text SET is_videofile_exist = ? WHERE videofile_name = ?",
                    (is_videofile_exist, videofile_name),
                )

                i += 1

            # Commit the transaction
            conn.commit()
            conn.close()

    def get_db_filename_dict(self):
        return self._db_filename_dict

    # 取得数据库文件夹下的完整数据库路径列表
    def _init_db_filename_dict(self):
        db_list = os.listdir(self.db_path)
        if len(db_list) == 0:
            # 目录为空
            return {}

        # 去除非当前用户、且临时使用的内容
        db_list = list(filter(lambda file: file.startswith(self.user_name) and not file.endswith("_TEMP_READ.db"), db_list))

        if len(db_list) == 0:  # 如果去除了非当前用户内容后为空
            return {}

        db_list_datetime = [utils.extract_date_from_db_filename(file) for file in db_list]

        return dict(sorted(zip(db_list, db_list_datetime), key=lambda x: x[1]))

    # 检测是否初次使用工具，如果不存在数据库/数据库中只有一条数据，则判定为是
    def check_is_onboarding(self):
        is_db_existed = self.db_main_initialize()
        db_file_count = len(self.get_db_filename_dict())
        if not is_db_existed:
            return True
        latest_db_records = self.db_num_records()
        if latest_db_records == 1 and db_file_count == 1:
            return True
        return False


db_manager = _DBManager(
    config.db_path_ud,
    int(config.max_page_result),
    config.user_name,
)
