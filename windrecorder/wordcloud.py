import os
from datetime import datetime

import jieba
import matplotlib.pyplot as plt
import numpy as np

# doc: https://amueller.github.io/word_cloud/generated/wordcloud.WordCloud.html
from PIL import Image
from send2trash import send2trash
from wordcloud import ImageColorGenerator, WordCloud

import windrecorder.utils as utils
from windrecorder import file_utils
from windrecorder.config import config
from windrecorder.db_manager import db_manager


# 读取跳过词
def read_stopwords(filename):
    stopwords = []
    with open(filename, "r", encoding="utf-8") as file:
        stopwords = file.read().split(",")
        stopwords = [word.strip() for word in stopwords]
    return stopwords


stopwords = read_stopwords("config\\src\\wordcloud_stopword.txt") + config.wordcloud_user_stop_words


# 按月数据库生成已有所有数据的词库
def generate_all_word_lexicon_by_month():
    # 取得所有数据库地址
    all_db_files_dict = db_manager.get_db_filename_dict()

    # 取得已有随机词典txt文件名
    lexicon_directory = "config\\random_lexicon"
    suffix = "_now.txt"
    file_utils.check_and_create_folder(lexicon_directory)
    file_list = [filename for filename in os.listdir(lexicon_directory) if filename.endswith(".txt")]

    # 获取需要更新索引的数据库
    file_list_to_generate_lexicon = []

    # 检查已有txt文件，是否有未生成的数据库对应词典，有着写入索引数据库队列
    file_list_str = ""
    file_list_str = file_list_str.join(file_list)
    for key, value in all_db_files_dict.items():
        if key[:-3] not in file_list_str:
            file_list_to_generate_lexicon.append(key)

    # 检查已生成词典中尾缀为'_now.txt'一项，有且超过一定时间未更新则写入索引数据库队列
    for filename in file_list:
        if suffix in filename:  # 若有
            if not file_utils.is_file_modified_recently(os.path.join(lexicon_directory, filename), time_gap=14400):  # 超过十天未修改
                send2trash(os.path.join(lexicon_directory, filename))
                file_list_to_generate_lexicon.append(filename[:-8] + ".db")

    file_list_to_generate_lexicon = list(set(file_list_to_generate_lexicon))  # 整理去重需要整理词语的数据库列表
    print(f"[wordcloud] file_list_to_generate_lexicon:{file_list_to_generate_lexicon}")

    for db_name in file_list_to_generate_lexicon:
        print(f"[wordcloud]processing {db_name}")

        # 获取对应数据库的所有ocr数据
        print(all_db_files_dict[db_name])
        ocr_text_filepath = get_month_ocr_result(
            utils.datetime_to_seconds(all_db_files_dict[db_name]),
            text_file_path="cache\\lexicon_ocr_temp.txt",
        )
        # 分词
        with open(ocr_text_filepath, "r", encoding="utf-8") as file:
            data = file.read()
            jieba_list = jieba.lcut(data)
        jieba_list = list(set(jieba_list) - set(stopwords))  # 去重 & stopwords

        # 如果是当月的数据库，添加尾缀
        if all_db_files_dict[db_name].month == datetime.now().month:
            lexicon_save_filename = db_name[:-3] + suffix
        else:
            lexicon_save_filename = db_name[:-3] + ".txt"
        lexicon_save_filepath = os.path.join(lexicon_directory, lexicon_save_filename)

        with open(lexicon_save_filepath, "w", encoding="utf-8") as file:
            for element in jieba_list:
                file.write(str(element) + "\n")


def check_if_word_lexicon_empty():
    # 取得已有随机词典txt文件名
    lexicon_directory = "config\\random_lexicon"
    file_utils.check_and_create_folder(lexicon_directory)
    file_list = [filename for filename in os.listdir(lexicon_directory) if filename.endswith(".txt")]
    if len(file_list) > 0:
        return False
    else:
        return True


# 生成词云
def generate_word_cloud_pic(text_file_path, img_save_path, mask_img="month"):
    # 打开文本
    # with open(text_file_path,encoding="utf-8") as f:
    #     s = f.read()
    try:
        with open(text_file_path, encoding="utf-8") as f:
            s = f.read()
    except FileNotFoundError:
        with open(text_file_path) as f:
            s = f.read()

    if len(s) < 10:
        return

    # 中文分词
    text = " ".join(jieba.cut(s))

    # 生成对象
    if mask_img == "month":
        img = Image.open("__assets__/mask_cloud_color.jpg")  # 打开遮罩图片
        img_width = 1000
        img_height = 800
        min_font_size = 8
        max_font_size = 150
        max_words = 300
    elif mask_img == "day":
        img = Image.open("__assets__/mask_horizon.jpg")
        img_width = 600
        img_height = 900
        min_font_size = 16
        max_font_size = 150
        max_words = 200
    mask = np.array(img)  # 将图片转换为数组

    wc = WordCloud(
        font_path="msyh.ttc",
        mask=mask,
        width=img_width,
        height=img_height,
        min_font_size=min_font_size,
        max_font_size=max_font_size,
        mode="RGBA",
        background_color=None,
        max_words=max_words,
        stopwords=stopwords,
        min_word_length=2,
        relative_scaling=0.4,
        repeat=False,
    ).generate(text)

    # 着色
    image_colors = ImageColorGenerator(mask)
    fig, axes = plt.subplots(1, 3)
    axes[0].imshow(wc, interpolation="bilinear")
    # recolor wordcloud and show
    # we could also give color_func=image_colors directly in the constructor
    axes[1].imshow(wc.recolor(color_func=image_colors), interpolation="bilinear")
    axes[2].imshow(img, cmap=plt.cm.gray, interpolation="bilinear")
    for ax in axes:
        ax.set_axis_off()

    # 显示词云
    # plt.imshow(wc, interpolation='bilinear')# 用plt显示图片
    # plt.axis("off")  # 不显示坐标轴
    # plt.show() # 显示图片

    # 保存到文件
    wc.to_file(img_save_path)


# 获取某个时间戳下当月的所有识别内容
def get_month_ocr_result(timestamp, text_file_path="cache/get_month_ocr_result_out.txt"):
    timestamp_datetime = utils.seconds_to_datetime(timestamp)
    # 查询当月所有识别到的数据，存储在文本中
    date_in = datetime(timestamp_datetime.year, timestamp_datetime.month, 1, 0, 0, 1)
    date_out = datetime(
        timestamp_datetime.year,
        timestamp_datetime.month,
        utils.get_days_in_month(timestamp_datetime.year, timestamp_datetime.month),
        23,
        59,
        59,
    )
    df, _, _ = db_manager.db_search_data("", date_in, date_out)
    # ocr_text_data = df["ocr_text"].to_string(index=False)
    ocr_text_data = "".join(df["ocr_text"].tolist())
    ocr_text_data = utils.delete_short_lines(ocr_text_data, less_than=10)

    # 移除换行符
    ocr_text_data = ocr_text_data.replace("\n", "").replace("\r", "")
    # 输出到文件
    file_utils.check_and_create_folder("cache")

    with open(text_file_path, "w", encoding="utf-8") as file:
        file.write(ocr_text_data)
    return text_file_path

    # 以csv列输出
    # output_file = "cache/out.txt"
    # ocr_text_data.to_csv(output_file, index=False, header=False, sep="\t")


# 获取某个时间戳下当天的所有识别内容
def get_day_ocr_result(timestamp):
    timestamp_datetime = utils.seconds_to_datetime(timestamp)
    # 查询当月所有识别到的数据，存储在文本中
    begin_day = config.begin_day
    date_in = datetime(
        timestamp_datetime.year,
        timestamp_datetime.month,
        timestamp_datetime.day,
        begin_day // 60,
        begin_day % 60,
        1,
    )
    date_out = datetime(
        timestamp_datetime.year,
        timestamp_datetime.month,
        timestamp_datetime.day,
        (23 + begin_day // 60) % 24,
        (59 + begin_day % 60) % 60,
        59,
    )
    df, _, _ = db_manager.db_search_data("", date_in, date_out)
    ocr_text_data = "".join(df["ocr_text"].tolist())
    ocr_text_data = utils.delete_short_lines(ocr_text_data, less_than=10)

    # 移除换行符
    ocr_text_data = ocr_text_data.replace("\n", "").replace("\r", "")
    # 输出到文件
    file_utils.check_and_create_folder("cache")
    text_file_path = "cache/get_day_ocr_result_out.txt"
    with open(text_file_path, "w", encoding="utf-8") as file:
        file.write(ocr_text_data)
    return text_file_path


# 根据某时数据生成该月的词云
def generate_word_cloud_in_month(timestamp, img_save_name="default"):
    # 取得当月内所有ocr结果
    text_file_path = get_month_ocr_result(timestamp)

    img_save_dir = config.wordcloud_result_dir
    file_utils.check_and_create_folder(img_save_dir)
    img_save_name = img_save_name
    img_save_path = os.path.join(img_save_dir, img_save_name)

    # 生成词云图片
    generate_word_cloud_pic(text_file_path, img_save_path, mask_img="month")
    os.remove(text_file_path)


# 根据某时数据生成当天的词云
def generate_word_cloud_in_day(timestamp, img_save_name="default"):
    # 取得当天内所有ocr结果
    text_file_path = get_day_ocr_result(timestamp)

    img_save_dir = config.wordcloud_result_dir
    file_utils.check_and_create_folder(img_save_dir)
    img_save_name = img_save_name
    img_save_path = os.path.join(img_save_dir, img_save_name)

    # 生成词云图片
    generate_word_cloud_pic(text_file_path, img_save_path, mask_img="day")
    os.remove(text_file_path)
