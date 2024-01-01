# 用来将图像转换为 embedding
# 处理 faiss 数据库事务（建立、添加索引、搜索）

# vdb == VectorDatabase

import os

import faiss
import numpy as np
import torch
import uform
from PIL import Image

device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
is_cuda_available = torch.cuda.is_available()

# TODO 添加在本地路径预加载与管理模型选型，以便打包形态使用


def get_model(mode="cpu"):
    """
    加载模型
    """
    model = uform.get_model("unum-cloud/uform-vl-multilingual-v2")
    if mode == "cpu":
        print("emb run on cpu.")
    if mode == "cuda":
        print("emb run on cuda.")
        if is_cuda_available:
            model.to(device=device)
        else:
            print("cude not available, emb run on cpu.")

    return model


def embed_img(model: uform.models.VLM, img_filepath):
    """
    将图像转为 embedding vector
    """
    image = Image.open(img_filepath)
    image_data = model.preprocess_image(image)
    if is_cuda_available:
        image_features, image_embedding = model.encode_image(image_data.to(device=device), return_features=True)
    else:
        image_features, image_embedding = model.encode_image(image_data, return_features=True)
    return image_embedding


def embed_text(model: uform.models.VLM, text_query):
    """
    将文本转为 embedding vector
    注意：model 必须运行在 cpu 模式下
    """
    # 对文本进行编码
    text_data = model.preprocess_text(text_query)
    text_features, text_embedding = model.encode_text(text_data, return_features=True)

    # 预处理张量
    text_np = text_embedding.detach().cpu().numpy()
    text_np = np.float32(text_np)
    faiss.normalize_L2(text_np)
    return text_np


class VectorDatabase:
    """
    向量数据库事务
    """

    def __init__(self, vdb_filename, db_dir="", dimension=256) -> None:  # FIXME:make it config
        """
        初始化新建/载入数据库
        """
        self.dimension = dimension
        self.vdb_filepath = os.path.join(db_dir, vdb_filename)
        self.all_ids_list = []
        if os.path.exists(self.vdb_filepath):
            self.index = faiss.read_index(self.vdb_filepath)
            self.all_ids_list = faiss.vector_to_array(self.index.id_map).tolist()  # 准备其中的 ROWID 以供写入时比对
        else:
            self.index = faiss.IndexIDMap(faiss.IndexFlatL2(self.dimension))

    def add_vector(self, vector, rowid: int):
        """
        添加向量到 index

        :param vector: 图像 embedding 后的向量
        :param rowid: sqlite 对应的 ROWID
        """
        vector = vector.detach().cpu().numpy()  # 转换为numpy数组
        vector = np.float32(vector)  # 转换为float32类型的numpy数组
        faiss.normalize_L2(vector)  # 规范化向量，避免在搜索时出现错误的结果

        if rowid in self.all_ids_list:  # 如果 rowid 已经存在了，删除后再更新
            self.index.remove_ids(np.array([rowid]))
        self.index.add_with_ids(vector, np.array([rowid]))  # 踩坑：使用faiss来管理就好，先用list/dict缓存再集中写入的思路会OOM

    def search_vector(self, vector, k=20):
        """在数据库中查询最近的k个向量，返回对应 rowid, 相似度 列表"""
        probs, indices = self.index.search(vector, k)
        return [(i, probs[0][j]) for j, i in enumerate(indices[0])]

    def save_to_file(self):
        faiss.write_index(self.index, self.vdb_filepath)
        self.all_ids_list = faiss.vector_to_array(self.index.id_map).tolist()


def embed_img_in_iframe_by_rowid_dict(model: uform.models.VLM, img_dict: dict, img_dir_filepath, vdb: VectorDatabase):
    """
    流程：根据 sqlite's ROWID:图像文件名 对应关系的 dict，
    将 iframe 临时文件夹中的所有图像转为对应的 embedding 并写入 vdb.index
    """
    for rowid, img_filename in img_dict.items():
        print(f"Embedding {rowid=}, {img_filename=}")
        vdb.add_vector(vector=embed_img(model, os.path.join(img_dir_filepath, img_filename)), rowid=rowid)
        # time.sleep(0.01)
    vdb.save_to_file()


# 测试用例
if __name__ == "__main__":
    # 1. 准备一组测试图片放在 i_frames 目录下
    img_dataset_filepath = "i_frames"
    file_names = os.listdir(img_dataset_filepath)
    test_dataset_dict = {}
    for item in file_names:
        test_dataset_dict[len(test_dataset_dict)] = item

    # 2. 将图片嵌入为向量
    model = get_model(mode="cuda")
    vdb = VectorDatabase(vdb_filename="test.index", db_dir="")
    vector = embed_img_in_iframe_by_rowid_dict(
        model=model, img_dict=test_dataset_dict, img_dir_filepath=img_dataset_filepath, vdb=vdb
    )

    # 3. 使用语义查询 ROWID / 图片
    model = get_model("cpu")
    text_query_vector = embed_text(model=model, text_query="棕色头发的人")
    res = vdb.search_vector(vector=text_query_vector)
    res_parse = []
    for item in res:
        res_parse.append((test_dataset_dict[item[0]], item[1]))
    print(f"{res_parse=}")
