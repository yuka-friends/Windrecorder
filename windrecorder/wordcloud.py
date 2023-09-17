from datetime import datetime

from wordcloud import WordCloud
# doc: https://amueller.github.io/word_cloud/generated/wordcloud.WordCloud.html
from PIL import Image
import numpy as np
import matplotlib.pyplot as plt
import jieba
import pandas as pd

import windrecorder.utils as utils
from windrecorder.dbManager import dbManager
import windrecorder.files as files

# 生成词云
def generate_word_cloud_pic(text_file_path,img_save_path):
    # 打开文本
    # with open(text_file_path,encoding="utf-8") as f:
    #     s = f.read()
    with open(text_file_path) as f:
        s = f.read()

    # 中文分词
    text = ' '.join(jieba.cut(s))

    # 生成对象
    img = Image.open("__assets__/mask_cloud.png") # 打开遮罩图片
    mask = np.array(img) #将图片转换为数组

    stopwords = ["我","你","她","的","是","了","在","也","和","就","都","这"]
    wc = WordCloud(font_path="msyh.ttc",
                   mask=mask,
                   width = 800,
                   height = 600,
                   background_color=None,
                   mode="RGBA",
                   max_words=200,
                   stopwords=None).generate(text)

    # 显示词云
    plt.imshow(wc, interpolation='bilinear')# 用plt显示图片
    plt.axis("off")  # 不显示坐标轴
    plt.show() # 显示图片

    # 保存到文件
    wc.to_file(img_save_path)


# 获取某个时间戳下当月的所有识别内容
def get_month_ocr_result(timestamp):
    timestamp_datetime = utils.seconds_to_datetime(timestamp)
    #查询当月所有识别到的数据，存储在文本中
    date_in = datetime(timestamp_datetime.year,
                       timestamp_datetime.month,
                       1,
                       0,0,1)
    date_out = datetime(timestamp_datetime.year,
                       timestamp_datetime.month,
                       utils.get_days_in_month(timestamp_datetime.year,timestamp_datetime.month),
                       23,59,59)
    df,_,_ = dbManager.db_search_data("",date_in,date_out,0,is_p_index_used=False)
    # ocr_text_data = df["ocr_text"].to_string(index=False)
    ocr_text_data = ''.join(df['ocr_text'].tolist()) # 用空格不换行连接的方式实现

    # 移除换行符
    ocr_text_data = ocr_text_data.replace("\n", "").replace("\r", "")
    # 输出到文件
    files.check_and_create_folder("catch")
    text_file_path = "catch/get_month_ocr_result_out.txt"
    with open(text_file_path, "w") as file:
        file.write(ocr_text_data)
    return text_file_path

    # 以csv列输出
    # output_file = "catch/out.txt"
    # ocr_text_data.to_csv(output_file, index=False, header=False, sep="\t")

  
# 根据某时数据生成该月的词云
def generate_word_cloud_in_month(timestamp):
    text_file_path = get_month_ocr_result(timestamp)
    img_save_path = "wordcloud_result"
    files.check_and_create_folder(img_save_path)
    generate_word_cloud_pic(text_file_path,img_save_path)
    