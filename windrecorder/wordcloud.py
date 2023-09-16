# 示例代码 from https://zhuanlan.zhihu.com/p/353795160
from wordcloud import WordCloud
# doc: https://amueller.github.io/word_cloud/generated/wordcloud.WordCloud.html
from PIL import Image
import numpy as np
import matplotlib.pyplot as plt
import jieba


def generate_word_cloud_pic(text_filepath,img_save_path):
    # 打开文本
    with open(text_filepath,encoding="utf-8") as f:
        s = f.read()

    # 中文分词
    text = ' '.join(jieba.cut(s))

    # 生成对象
    img = Image.open("mask_pic.png") # 打开遮罩图片
    mask = np.array(img) #将图片转换为数组

    stopwords = ["我","你","她","的","是","了","在","也","和","就","都","这"]
    wc = WordCloud(font_path="msyh.ttc",
                   mask=mask,
                   width = 1000,
                   height = 700,
                   background_color=None,
                   mode="RGBA",
                   max_words=200,
                   stopwords=stopwords).generate(text)

    # 显示词云
    plt.imshow(wc, interpolation='bilinear')# 用plt显示图片
    plt.axis("off")  # 不显示坐标轴
    plt.show() # 显示图片

    # 保存到文件
    wc.to_file(img_save_path)