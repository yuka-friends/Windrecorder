# 用来将图像转换为 embedding
# 处理 faiss 数据库事务（建立、添加索引、搜索）
# 处理向量搜索与 sqlite 数据库召回

# vdb: VectorDatabase

# import 前确保 config.img_embed_module_install is True
# if config.img_embed_module_install:
#     try:
#         from windrecorder import img_embed_manager
#     except ModuleNotFoundError:
#         config.set_and_save_config("img_embed_module_install", False)

import datetime
import math
import os
import shutil

import faiss
import numpy as np
import pandas as pd
from PIL import Image
from tqdm import tqdm
from uform import Modality, get_model

from windrecorder import file_utils, utils
from windrecorder.config import config
from windrecorder.db_manager import db_manager
from windrecorder.logger import get_logger
from windrecorder.ocr_manager import extract_iframe

logger = get_logger(__name__)

MODEL_NAME = "unum-cloud/uform3-image-text-multilingual-base"


def get_model_and_processor():
    processors, models = get_model("unum-cloud/uform3-image-text-multilingual-base")
    model_text = models[Modality.TEXT_ENCODER]
    model_image = models[Modality.IMAGE_ENCODER]
    processor_text = processors[Modality.TEXT_ENCODER]
    processor_image = processors[Modality.IMAGE_ENCODER]

    return model_text, model_image, processor_text, processor_image


def embed_img(model_image, processor_image, img_filepath):
    """
    将图像转为 embedding vector
    """
    image = Image.open(img_filepath)
    image_data = processor_image(image)
    image_features, image_embedding = model_image.encode(image_data, return_features=True)

    return image_embedding


def embed_text(model_text, processor_text, text_query, detach_numpy=True):
    """
    将文本转为 embedding vector

    :param detach_numpy 是否预处理张量
    """
    # 对文本进行编码
    text_data = processor_text(text_query)
    text_features, text_embedding = model_text.encode(text_data, return_features=True)

    # 预处理张量
    if detach_numpy:
        # text_np = text_embedding.detach().cpu().numpy()
        text_np = text_embedding
        text_np = np.float32(text_np)
        faiss.normalize_L2(text_np)
        return text_np
    else:
        return text_embedding


def get_vdb_filename_via_video_filename(video_filename):
    """
    根据视频名获得 vdb 本地数据库文件名
    构成：username_YYYY-MM_imgemb.index
    """
    return f"{config.user_name}_{file_utils.convert_vid_filename_as_YYYY_MM(video_filename)}_imgemb.index"


class VectorDatabase:
    """
    向量数据库事务
    以 IndexIDMap 存储，对应关系为 向量 - sqlite 的 ROWID
    """

    def __init__(self, vdb_filename, db_dir=config.vdb_img_path_ud, dimension=256):  # uform 使用 256d 向量
        """
        初始化新建/载入数据库

        :param vdb_filename, 向量数据库名字
        :param db_dir, 向量数据库路径
        """
        self.dimension = dimension
        self.vdb_filepath = os.path.join(db_dir, vdb_filename)
        self.all_ids_list = []
        file_utils.ensure_dir(db_dir)
        if os.path.exists(self.vdb_filepath):
            self.index = faiss.read_index(self.vdb_filepath)
            self.all_ids_list = faiss.vector_to_array(self.index.id_map).tolist()  # 获得向量数据库中已有 ROWID 列表，以供写入时比对
        else:
            self.index = faiss.IndexIDMap(faiss.IndexFlatL2(self.dimension))

    def add_vector(self, vector, rowid: int):
        """
        添加向量到 index

        :param vector: 图像 embedding 后的向量
        :param rowid: sqlite 对应的 ROWID
        """
        # vector = vector.detach().cpu().numpy()  # 转换为numpy数组
        vector = np.float32(vector)  # 转换为float32类型的numpy数组
        faiss.normalize_L2(vector)  # 规范化向量，避免在搜索时出现错误的结果

        if rowid in self.all_ids_list:  # 如果 rowid 已经存在于向量数据库，删除后再更新
            self.index.remove_ids(np.array([rowid]))
        self.index.add_with_ids(vector, np.array([rowid]))  # 踩坑：使用faiss来管理就好，先用list/dict缓存再集中写入的思路会OOM

    def search_vector(self, vector, k=20):
        """在数据库中查询最近的k个向量，返回对应 (rowid, 相似度) 列表"""
        probs, indices = self.index.search(vector, k)
        return [(i, probs[0][j]) for j, i in enumerate(indices[0])]

    def save_to_file(self):
        """将向量数据库写入本地文件"""
        faiss.write_index(self.index, self.vdb_filepath)
        self.all_ids_list = faiss.vector_to_array(self.index.id_map).tolist()  # 更新 ROWID 列表


def find_closest_iframe_img_dict_item(target: str, img_dict: dict, threshold=3):
    """
    寻找 dict {sqlite_ROWID:图像文件名} 中最邻近输入图像名的一项
    如输入 "123.jpg"，返回字典中最接近的 "125.jpg"
    """
    closest_item = None
    min_difference = float("inf")

    for key, value in img_dict.items():
        difference = abs(int(value.split(".")[0]) - int(target.split(".")[0]))
        if difference <= threshold and difference < min_difference:
            closest_item = value
            min_difference = difference

    return closest_item


def embed_img_in_iframe_by_rowid_dict(model_image, processor_image, img_dict: dict, img_dir_filepath, vdb: VectorDatabase):
    """
    流程：根据 dict {sqlite_ROWID:图像文件名} 对应关系，
    将（i_frame 临时）文件夹中的对应图像转为对应的 embedding 并写入 vdb.index
    """
    for rowid, img_filename in img_dict.items():
        logger.debug(f"Embedding {rowid=}, {img_filename=}")
        img_filepath = os.path.join(img_dir_filepath, img_filename)
        if not os.path.exists(img_filepath):
            # 提取的图像列表有时出于换了提取iframe方式、cv可能的随机性等缘故，可能无法保证与db过去记录的完全一致，在 embedding 时有则 embed，无则寻找最近的阈值、再无则跳过。但考虑到相似图像仍会出现在附近时间范围，结果应尚可。
            closest_img_filename = find_closest_iframe_img_dict_item(target=img_filename, img_dict=img_dict)
            if closest_img_filename is None:
                logger.info(f"{img_filepath} closest item not found, skipped.")
                continue
            else:
                img_filepath = os.path.join(img_dir_filepath, closest_img_filename)
                if not os.path.exists(img_filepath):
                    logger.info(f"{img_filepath} not existed, skipped.")
                    continue
                logger.info(f"{img_filepath} replaced.")
        vdb.add_vector(vector=embed_img(model_image, processor_image, img_filepath), rowid=rowid)

    vdb.save_to_file()


def embed_vid_file(
    model_image,
    processor_image,
    vdb: VectorDatabase,
    vid_file_name,
    video_saved_dir=config.record_videos_dir_ud,
    iframe_path=config.iframe_dir,
):
    """
    流程：输入一个视频文件路径，根据 sqlite 数据库，获得 dict {sqlite_ROWID:图像文件名}
    建议用 try 调用，避免因索引数据可能不全报错而阻塞。

    param: vid_file_name, 视频文件名，看起来像"2023-10-01_12-04-28-OCRED.mp4"
    """
    vid_filepath = os.path.join(video_saved_dir, file_utils.convert_vid_filename_as_YYYY_MM(vid_file_name), vid_file_name)

    # 获取视频名在 sqlite db 中的对应 iframe cnt index
    img_db_recorded_dict = {}
    df_video_related = db_manager.db_get_row_from_vid_filename(vid_file_name)
    for index, row in df_video_related.iterrows():
        img_db_recorded_dict[row["rowid"]] = row["picturefile_name"]
    if len(img_db_recorded_dict) == 0:
        return False

    # 判断是否存在图片缓存文件，若无则提取
    iframe_sub_path = os.path.join(iframe_path, os.path.splitext(vid_file_name)[0][:19])  # FIXME 硬编码取了文件名的日期范围
    iframe_img_list = []
    if os.path.exists(iframe_sub_path):
        iframe_img_list = os.listdir(iframe_sub_path)

    if not all(
        element in iframe_img_list for element in list(img_db_recorded_dict.values())
    ):  # 已有缓存图像文件是否包含了sqlite db中记录的图像文件，否则重新提取
        # 清理缓存
        try:
            shutil.rmtree(iframe_sub_path)
        except FileNotFoundError:
            pass
        file_utils.ensure_dir(iframe_sub_path)
        extract_iframe(video_file=vid_filepath, iframe_path=iframe_sub_path)
        # FIXME 提取后需要对图像进行遮减处理？

    # 因为是原子操作，不用添加回滚机制，完成了所有的索引才写入 faiss index db file
    embed_img_in_iframe_by_rowid_dict(
        model_image=model_image,
        processor_image=processor_image,
        img_dict=img_db_recorded_dict,
        img_dir_filepath=iframe_sub_path,
        vdb=vdb,
    )
    # 清理图像缓存
    try:
        shutil.rmtree(iframe_sub_path)
    except FileNotFoundError:
        pass

    os.rename(vid_filepath, vid_filepath.replace("-OCRED", "-IMGEMB-OCRED"))
    return True


def all_videofile_do_img_embedding_routine(video_queue_batch=14):
    """
    流程：处理未嵌入的视频，提取嵌入视频 iframe embedding 到向量数据库。默认计算时间控制在 30 分钟左右内（即索引 12~15 个视频）
    """
    video_process_count = 0

    model_text, model_image, processor_text, processor_image = get_model_and_processor()

    video_dirs = os.listdir(config.record_videos_dir_ud)[::-1]  # 倒序列表，以先索引较新的视频
    for video_dir in tqdm(video_dirs):
        videos_names = os.listdir(os.path.join(config.record_videos_dir_ud, video_dir))[::-1]
        for video_name in tqdm(videos_names):
            logger.debug(f"img_embed({video_process_count}/{video_queue_batch}): embedding {video_dir}, {video_name}")
            # 确认视频已被 OCR 索引，且没含有 -IMGEMB 标签
            # 如果视频被压缩了，目前跳过；TODO 未来如果使用时间戳手段提取、或者可以接受iframe提取的时域误差，则不需要这条规则了
            if "-OCRED" not in video_name:
                continue
            if "-IMGEMB" in video_name or "-COMPRESS" in video_name:
                continue
            vdb = VectorDatabase(vdb_filename=get_vdb_filename_via_video_filename(video_name))
            print(f"embedding {video_name}")
            embed_vid_file(model_image=model_image, processor_image=processor_image, vdb=vdb, vid_file_name=video_name)
            video_process_count += 1
            if video_process_count > video_queue_batch:
                break
        if video_process_count > video_queue_batch:
            break


def get_vdbs_filename_via_time_range(start_datetime: datetime.datetime, end_datetime: datetime.datetime):
    """
    根据输入输出时间范围获取 vdb filename list
    """
    start_datetime = utils.set_full_datetime_to_YYYY_MM(start_datetime)
    end_datetime = utils.set_full_datetime_to_YYYY_MM(end_datetime)

    file_utils.ensure_dir(config.vdb_img_path_ud)
    vdb_filename_list = file_utils.get_file_path_list_first_level(config.vdb_img_path_ud)
    vdb_filename_list = [
        item for item in vdb_filename_list if (item.startswith(config.user_name) and item.endswith("_imgemb.index"))
    ]  # 去除非当前用户、且非 vdb 的项
    if len(vdb_filename_list) == 0:
        return None

    vdb_filename_list_datetime = [utils.extract_date_from_db_filename(file) for file in vdb_filename_list]
    vdb_filename_list_datetime_dict = dict(sorted(zip(vdb_filename_list, vdb_filename_list_datetime), key=lambda x: x[1]))
    result = []
    for key, value in vdb_filename_list_datetime_dict.items():
        if start_datetime <= value <= end_datetime:
            result.append(key)
    return result


def query_vector_in_img_vdbs(vector, start_datetime, end_datetime):
    """
    流程：在 vdb list 中搜索向量，提取对应 sqlite rowid 项，合并排序返回 df
    """
    vdb_filenames = get_vdbs_filename_via_time_range(start_datetime=start_datetime, end_datetime=end_datetime)
    if vdb_filenames is None:
        return pd.DataFrame(), 0, 0

    df_list = []
    for vdb_filename in vdb_filenames:
        logger.info(f"recalling {vdb_filename}")
        vdb = VectorDatabase(vdb_filename=vdb_filename)
        res_tuple_list = vdb.search_vector(vector, k=config.img_embed_search_recall_result_per_db)
        res_tuple_list = [t for t in res_tuple_list if t[0] != -1]  # 相似度结果不足时，会以 -1 的 index 填充，在进 sqlite 搜索前需过滤

        len_prefix = len(config.user_name) + 1
        db_filename = f"{vdb_filename[0:len_prefix+7]}_wind.db"
        df = db_manager.db_get_rowid_and_similar_tuple_list_rows(rowid_probs_list=res_tuple_list, db_filename=db_filename)
        df_list.append(df)

    merged_df = pd.concat(df_list)
    sorted_df = merged_df.sort_values(by="probs", ascending=True)
    sorted_df = sorted_df.reset_index(drop=True)
    row_count = len(sorted_df)
    page_count_all = int(math.ceil(int(row_count) / int(config.max_page_result)))
    return sorted_df, row_count, page_count_all


def text_embedding_all_sqlitedb_ocr_text():
    """
    流程：嵌入 sqlite 数据库中的 ocr text
    """
    # FIXME
    # 读取所有rowid，维护一个rowid表。通过维护ROWID判断有无被嵌入，有则跳过
    # 因为嵌入速度很快，所以可以一次对所有sqlite完成嵌入。整个表完成嵌入后，给一个标志（区分是否为当月、还有更新可能性

    # 读取所有sqdb文件列表
    # 读取sqdb的所有数据作为df


# 测试用例
if __name__ == "__main__":
    # 1. 准备一组测试图片放在 i_frames 目录下
    img_dataset_filepath = "i_frames"
    file_names = os.listdir(img_dataset_filepath)
    test_dataset_dict = {}
    for item in file_names:
        test_dataset_dict[len(test_dataset_dict)] = item

    # 2. 将图片嵌入为向量
    model_text, model_image, processor_text, processor_image = get_model_and_processor()
    vdb = VectorDatabase(vdb_filename="test.index", db_dir="")
    vector = embed_img_in_iframe_by_rowid_dict(
        model_image=model_image,
        processor_image=processor_image,
        img_dict=test_dataset_dict,
        img_dir_filepath=img_dataset_filepath,
        vdb=vdb,
    )

    # 3. 使用语义查询 ROWID / 图片
    text_query_vector = embed_text(model_text=model_text, processor_text=processor_text, text_query="棕色头发的人")
    res = vdb.search_vector(vector=text_query_vector)
    res_parse = []
    for item in res:
        res_parse.append((test_dataset_dict[item[0]], item[1]))
    logger.info(f"{res_parse=}")
