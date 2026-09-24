import datetime
import math
import os
import re
import sqlite3
import tempfile
from contextlib import closing
from itertools import product
from pathlib import Path
from subprocess import CalledProcessError

import numpy as np
import pandas as pd

import windrecorder.utils as utils
from windrecorder import file_utils
from windrecorder.config import config
from windrecorder.logger import get_logger

logger = get_logger(__name__)

VIDEO_TEXT_COLUMNS = [
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


class _DBManager:
    def __init__(self, db_path, db_max_page_result, user_name):
        self.db_path = db_path  # 存放数据库的目录
        file_utils.ensure_dir(self.db_path)
        self.db_max_page_result = db_max_page_result  # 最大查询页数
        self.user_name = user_name  # 用户名
        self._db_filename_dict = self._init_db_filename_dict()
        self._snapshot_signatures = {}

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
        db_filepath_today = file_utils.get_db_filepath_by_datetime(datetime.datetime.today(), self.db_path, self.user_name)

        # 初始化最新的数据库
        conn_check = self.db_initialize(db_filepath_today, insert_welcome=True)

        return conn_check

    # 初始化数据库：检查、创建、连接入参数据库对象，如果内容为空，则创建表初始化
    def db_initialize(self, db_filepath, *, insert_welcome=False):
        is_db_exist = os.path.exists(db_filepath)
        with closing(sqlite3.connect(db_filepath)) as conn:
            has_table = (
                conn.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='video_text'").fetchone() is not None
            )
        if not has_table:
            self.db_create_table(db_filepath)
            if insert_welcome:
                now = datetime.datetime.now()
                self.db_update_data(
                    now.strftime("%Y-%m-%d_%H-%M-%S") + ".mp4",
                    "0.jpg",
                    utils.datetime_to_seconds(now),
                    "Welcome! Go to Setting and Update your screen recording files.",
                    False,
                    False,
                    "iVBORw0KGgoAAAANSUhEUgAAAEYAAAAnCAYAAACyhj57AAAAoUlEQVRoBe3BAQEAAAwBMCrpp6RCHkCFb7RSvEErxRu0UrxBK8UbtFK8QSvFG7RSvEErxRu0UrxBK8UbtFK8QSvFG7RSvEErxRu0UrxBK8UbtFK8QSvFG7RSvEErxRu0UrxBK8UbtFK8QSvFG7RSvEErxRu0UrxBK8UbtFK8QSvFG7RSvEErxRu0UrxBK8UbtFK8QSvFG7RSvEErxRu0UrxBK8UbtFK8QSvFG7RSvEErxRu0UrxxUOdhqPjngTYAAAAASUVORK5CYII=",
                    None,
                    "",
                )
        self._db_filename_dict = self._init_db_filename_dict()
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

            # 新增了记录前台（浏览器）deep linking，需要增加一列 deep_linking TEXT
            self.db_ensure_row_exist(
                db_filepath=db_filepath, column_name="deep_linking", column_type="TEXT", table_name="video_text"
            )
            self.db_ensure_indexes(db_filepath)

    def db_ensure_indexes(self, db_filepath):
        # Additive, non-unique indexes preserve every existing row and FAISS rowid.
        with closing(sqlite3.connect(db_filepath)) as conn, conn:
            conn.execute("CREATE INDEX IF NOT EXISTS wr_video_time ON video_text(videofile_time)")
            conn.execute(
                "CREATE INDEX IF NOT EXISTS wr_capture_identity "
                "ON video_text(videofile_name, picturefile_name, videofile_time)"
            )

    def read_connection(self, db_filepath):
        """Short-lived, committed SQLite reads; never create a missing shard."""
        return closing(sqlite3.connect(Path(db_filepath).resolve().as_uri() + "?mode=ro", uri=True, timeout=5))

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
                   win_title TEXT,
                   deep_linking TEXT);"""
        )
        conn.close()
        self.db_ensure_indexes(db_filepath)

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
        deep_linking="",
    ):
        logger.info("Inserting data")
        # 使用方法：db_update_data(db_filepath,'video1.mp4','iframe_0.jpg', 120, 'text from ocr', True, False, "window_title")

        # 获取插入时间，取得对应的数据库
        insert_db_datetime = utils.set_full_datetime_to_YYYY_MM(utils.seconds_to_datetime(videofile_time))
        db_filepath = file_utils.get_db_filepath_by_datetime(
            insert_db_datetime, self.db_path, self.user_name
        )  # 直接获取对应时间的数据库路径

        conn = sqlite3.connect(db_filepath)
        c = conn.cursor()

        c.execute(
            "INSERT INTO video_text (videofile_name, picturefile_name, videofile_time, ocr_text, is_videofile_exist, is_picturefile_exist, thumbnail, win_title, deep_linking) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                videofile_name,
                picturefile_name,
                videofile_time,
                ocr_text,
                is_videofile_exist,
                is_picturefile_exist,
                thumbnail,
                win_title,
                deep_linking,
            ),
        )
        conn.commit()
        conn.close()

    # 以df入参形式批量插入新数据，考虑到跨月数据库处理的流程
    def db_add_dataframe_to_db_process(self, dataframe):
        if dataframe.empty:
            return
        # Group by full year/month, independent of row ordering or DataFrame index.
        months = dataframe["videofile_time"].map(lambda value: utils.seconds_to_datetime(value).strftime("%Y-%m"))
        for month, rows in dataframe.groupby(months, sort=True):
            database_path = file_utils.get_db_filepath_by_datetime(
                datetime.datetime.strptime(month, "%Y-%m"), self.db_path, self.user_name
            )
            self.db_initialize(database_path)
            self.db_add_dataframe_to_db(database_path, rows)

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
            "deep_linking": "TEXT",
        }

        # 将dataframe的数据写入数据库的video_text表中
        dataframe.to_sql("video_text", conn, if_exists="append", index=False, dtype=dtypes_dict)

        # 提交更改并关闭连接
        conn.commit()
        conn.close()
        self.db_ensure_indexes(database_path)

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

    def db_search_data(self, keyword_input, date_in, date_out, keyword_input_exclude="", *, defer_payload=False):
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
        date_in_ts = int(utils.dtstr_to_seconds(date_in.strftime("%Y-%m-%d_%H-%M-%S")))
        date_out_ts = int(utils.dtstr_to_seconds(date_out.strftime("%Y-%m-%d_%H-%M-%S")))
        # date_in_ts = int(utils.date_to_seconds(date_in.strftime("%Y-%m-%d_00-00-00")))
        # date_out_ts = int(utils.date_to_seconds(date_out.strftime("%Y-%m-%d_23-59-59")))

        if date_in_ts == date_out_ts:
            date_out_ts += 1

        # 获得对应时间段下涉及的所有数据库
        datetime_start = utils.seconds_to_datetime(date_in_ts)
        datetime_end = utils.seconds_to_datetime(date_out_ts)
        query_db_name_list = self.db_get_dbfilename_by_datetime(datetime_start, datetime_end)
        logger.info(f"{datetime_start=}, {datetime_end=}")

        conditions = []
        params = []
        for keyword in keyword_input.split():
            variants = (
                self.generate_similar_ch_strings(keyword)
                if config.use_similar_ch_char_to_search
                else [re.sub(r"(?<=\w)-(?=\w)", " ", keyword)]
            )
            group = []
            for variant in variants:
                group.append("(ocr_text LIKE ? OR win_title LIKE ?)")
                params.extend([f"%{variant}%", f"%{variant}%"])
            conditions.append("(" + " OR ".join(group) + ")")
        if not conditions:
            conditions.append("ocr_text LIKE ?")
            params.append("%")
        for keyword in keyword_input_exclude.split():
            keyword = re.sub(r"(?<=\w)-(?=\w)", " ", keyword)
            conditions.append("ocr_text NOT LIKE ?")
            params.append(f"%{keyword}%")
        conditions.append("videofile_time BETWEEN ? AND ?")
        params.extend([date_in_ts, date_out_ts])
        columns = "rowid, videofile_time" if defer_payload else "*"
        query = f"SELECT {columns} FROM video_text WHERE " + " AND ".join(conditions)
        query += " ORDER BY videofile_time, rowid"

        # 遍历查询所有数据库信息
        frames = []
        row_count = 0
        for key in query_db_name_list:
            db_filepath_origin = os.path.join(self.db_path, key)  # 构建完整路径
            db_filepath = db_filepath_origin
            logger.info(f"Querying {db_filepath}")

            with self.read_connection(db_filepath) as conn:
                df = pd.read_sql_query(query, conn, params=params)
            if defer_payload:
                df["_db_filename"] = key
            frames.append(df)

        # A missing monthly shard and a query with no matches have the same contract.
        empty_columns = ["rowid", "videofile_time", "_db_filename"] if defer_payload else VIDEO_TEXT_COLUMNS
        df_all = pd.concat(frames, ignore_index=True) if frames else pd.DataFrame(columns=empty_columns)
        row_count = len(df_all)
        page_count_all = int(math.ceil(int(row_count) / int(self.db_max_page_result)))

        return df_all, row_count, page_count_all

    def db_get_record_counts(self, start, end, frequency):
        """Count calendar buckets in [start, end), without loading OCR text/images.

        Stored seconds represent naive wall-clock time. SQLite's unixepoch modifier
        decodes those numbers without applying the host timezone or DST rules.
        """
        formats = {"hour": "%Y-%m-%d %H:00:00", "day": "%Y-%m-%d 00:00:00", "month": "%Y-%m-01 00:00:00"}
        date_format = formats[frequency]
        counts = {}
        for name in self.db_get_dbfilename_by_datetime(start, end - datetime.timedelta(microseconds=1)):
            path = (Path(self.db_path) / name).resolve()
            with closing(sqlite3.connect(path.as_uri() + "?mode=ro", uri=True)) as conn:
                rows = conn.execute(
                    "SELECT strftime(?, videofile_time, 'unixepoch'), COUNT(*) FROM video_text "
                    "WHERE videofile_time >= ? AND videofile_time < ? GROUP BY 1",
                    (date_format, utils.datetime_to_seconds(start), utils.datetime_to_seconds(end)),
                ).fetchall()
            for bucket, count in rows:
                counts[bucket] = counts.get(bucket, 0) + count
        return counts

    def db_period_signature(self, start, end):
        """Invalidate derived statistics after imports/deletions, including WAL commits."""
        result = []
        for name in sorted(self.db_get_dbfilename_by_datetime(start, end - datetime.timedelta(microseconds=1))):
            source = Path(self.db_path) / name
            signatures = []
            for path in (source, Path(str(source) + "-wal")):
                try:
                    info = path.stat()
                    signatures.append([info.st_mtime_ns, info.st_size, info.st_ino])
                except FileNotFoundError:
                    signatures.append(None)
            result.append([str(source.resolve()), signatures])
        return result

    # 拿到完整df后进行翻页检索操作
    def db_search_data_page_turner(self, df, page_index):
        # page_index 从 1 计起
        row_count = len(df)  # 总行数

        page_count = int(math.ceil(int(row_count) / int(self.db_max_page_result)))  # 根据结果与用户配置，计算需要多少页读取
        if page_count <= 1:
            page_count = 1

        row_start_index = (page_index - 1) * self.db_max_page_result
        row_end_index = row_start_index + self.db_max_page_result

        df_current_page = df.iloc[row_start_index:row_end_index].copy()
        if "_db_filename" in df_current_page.columns:
            frames = []
            for name, references in df_current_page.groupby("_db_filename", sort=False):
                path = Path(self.db_path) / name
                if not path.exists():
                    continue  # A recording may have been removed since this search.
                with self.read_connection(path) as conn:
                    for offset in range(0, len(references), 900):
                        batch = references.iloc[offset : offset + 900]
                        ids = batch.rowid.tolist()
                        placeholders = ",".join("?" for _ in ids)
                        rows = pd.read_sql_query(
                            f"SELECT rowid, * FROM video_text WHERE rowid IN ({placeholders})", conn, params=ids
                        ).set_index("rowid")
                        batch = batch[batch.rowid.isin(rows.index)]
                        rows = rows.reindex(batch.rowid.tolist())
                        valid = rows.videofile_time.to_numpy() == batch.videofile_time.to_numpy()
                        rows = rows.loc[valid].copy()
                        rows.index = batch.index[valid]
                        frames.append(rows)
            return (
                pd.concat(frames).sort_index().reset_index(drop=True) if frames else pd.DataFrame(columns=VIDEO_TEXT_COLUMNS)
            )

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
                "deep_linking",
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
        if df["thumbnail"].iloc[0] is not None:
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
                "deep_linking",
            ]
        ]

        return df

    # 根据视频文件名字返回对应行列 dataframe (rowid included)
    def db_get_row_from_vid_filename(self, vid_filename):
        vid_filepath = file_utils.convert_vid_filename_as_vid_filepath(vid_filename)
        vid_datetime_start = utils.dtstr_to_datetime(vid_filename[:19])
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
            with self.read_connection(db_filepath) as conn:
                df = pd.read_sql_query(
                    "SELECT rowid, * FROM video_text WHERE videofile_name LIKE ?", conn, params=[f"%{vid_filename[:19]}%"]
                )
            df_origin = pd.concat([df_origin, df])

        return df_origin

    def db_get_rowid_and_similar_tuple_list_rows(self, rowid_probs_list, db_filename):
        """
        根据 rowid - 相似度 元组构成的 list 提取数据库文件对应行与标注对应相似度，合在以 dataframe 形式返回
        """
        db_filepath = os.path.join(self.db_path, db_filename)
        records = []
        with self.read_connection(db_filepath) as conn:
            for offset in range(0, len(rowid_probs_list), 900):
                batch = rowid_probs_list[offset : offset + 900]
                ids = [int(identity) for identity, _ in batch]
                query = f"SELECT rowid, * FROM video_text WHERE rowid IN ({','.join('?' for _ in ids)})"
                rows = pd.read_sql_query(query, conn, params=ids).set_index("rowid")
                for identity, probability in batch:
                    if identity in rows.index:
                        records.append({**rows.loc[identity].to_dict(), "probs": probability})
        return pd.DataFrame(records, columns=[*VIDEO_TEXT_COLUMNS, "probs"])

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
            with self.read_connection(db_filepath_origin) as conn:
                for row in conn.execute("SELECT * FROM video_text"):
                    logger.debug(str(row))

    # 查询全部数据库一共有多少行
    def db_num_records(self):
        full_db_name_ondisk_dict = self.get_db_filename_dict()
        rows_count_all = 0
        for key, value in full_db_name_ondisk_dict.items():
            db_filepath_origin = os.path.join(self.db_path, key)
            with self.read_connection(db_filepath_origin) as conn:
                rows_count = conn.execute("SELECT COUNT(*) FROM video_text").fetchone()[0]
            rows_count_all += rows_count
            logger.debug(f"db_filepath: {db_filepath_origin}, rows_count: {rows_count}")
        logger.info(f"rows_count_all: {rows_count_all}")
        return rows_count_all

    # 获取表内最新的记录时间
    def db_latest_record_time(self):
        return self._record_time_bound(latest=True)

    # 获取表内最早的记录时间
    def db_first_earliest_record_time(self):
        return self._record_time_bound(latest=False)

    def _record_time_bound(self, *, latest):
        names = self.get_db_filename_dict()
        aggregate = "MAX" if latest else "MIN"
        for name in sorted(names, key=names.get, reverse=latest):
            path = (Path(self.db_path) / name).resolve()
            with closing(sqlite3.connect(path.as_uri() + "?mode=ro", uri=True)) as conn:
                value = conn.execute(f"SELECT {aggregate}(videofile_time) FROM video_text").fetchone()[0]
            if value is not None:
                return value
        return None

    # 回滚操作：删除输入视频文件名相关的所有条目
    def db_rollback_delete_video_refer_record(self, videofile_name):
        logger.info(f"removing record {videofile_name}")
        # 根据文件名定位数据库文件地址
        db_filepath = file_utils.get_db_filepath_by_datetime(
            utils.set_full_datetime_to_YYYY_MM(utils.dtstr_to_datetime(os.path.splitext(videofile_name)[0]))
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
            return df.iloc[:0].copy()
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
        source = Path(db_filepath).resolve()
        if source.stem.endswith("_TEMP_READ"):
            return str(source)
        destination = source.with_name(source.stem + "_TEMP_READ.db")

        # WAL commits may not change the main file. Track both files.
        def signature():
            result = []
            for path in (source, Path(str(source) + "-wal")):
                try:
                    info = path.stat()
                    result.append((info.st_mtime_ns, info.st_size, info.st_ino))
                except FileNotFoundError:
                    result.append(None)
            return tuple(result)

        current = signature()
        if destination.exists() and self._snapshot_signatures.get(str(source)) == current:
            return str(destination)
        fd, temporary = tempfile.mkstemp(prefix=destination.name + ".", suffix=".tmp", dir=source.parent)
        os.close(fd)
        try:
            # SQLite's backup API includes committed WAL pages and works while indexing.
            with closing(sqlite3.connect(source.as_uri() + "?mode=ro", uri=True)) as reader:
                with closing(sqlite3.connect(temporary)) as writer:
                    reader.backup(writer)
            try:
                os.replace(temporary, destination)
            except PermissionError:
                # Windows readers may still hold the last complete snapshot open.
                # Keep serving it and retry refresh on the next request.
                if destination.exists():
                    return str(destination)
                raise
            self._snapshot_signatures[str(source)] = current
        finally:
            if os.path.exists(temporary):
                os.unlink(temporary)
        return str(destination)

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
        self._db_filename_dict = self._init_db_filename_dict()
        return self._db_filename_dict

    # 取得数据库文件夹下的完整数据库路径列表
    def _init_db_filename_dict(self):
        pattern = re.compile(re.escape(self.user_name) + r"_\d{4}-\d{2}_wind\.db$")
        result = {}
        for path in Path(self.db_path).iterdir():
            if not path.is_file() or not pattern.fullmatch(path.name):
                continue
            try:
                result[path.name] = utils.extract_date_from_db_filename(path.name, self.user_name)
            except ValueError:
                logger.warning("Ignoring invalid database filename: %s", path.name)
        return dict(sorted(result.items(), key=lambda item: item[1]))

    # 检测是否初次使用工具，如果不存在数据库/数据库中只有一条数据，则判定为是
    def check_is_onboarding(self):
        if (
            len(file_utils.get_file_path_list(config.db_path_ud)) > 2
        ):  # quick check after a period of application, avoid checking all databases
            return False

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
