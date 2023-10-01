import os
import base64
import subprocess
import json
import datetime

import cv2
import numpy as np
from ocr_lib.chineseocr_lite_onnx.model import OcrHandle
import win32file
import pyautogui
from send2trash import send2trash
from PIL import Image

from windrecorder.utils import empty_directory, date_to_seconds, seconds_to_date
from windrecorder.dbManager import DBManager
from windrecorder.config import config
import windrecorder.utils as utils
import windrecorder.files as files



# ocr_short_side = int(config.ocr_short_size)

# 检查文件是否被占用
# def is_file_in_use(file_path):
#     try:
#         fd = os.open(file_path, os.O_RDWR|os.O_EXCL)
#         os.close(fd)
#         return False
#     except OSError:
#         return True

# 使用 win32file 的判断实现
def is_file_in_use(file_path):
    try:
        vHandle = win32file.CreateFile(file_path, win32file.GENERIC_READ, 0, None, win32file.OPEN_EXISTING, win32file.FILE_ATTRIBUTE_NORMAL, None)
        return int(vHandle) == win32file.INVALID_HANDLE_VALUE
    except:
        return True
    finally:
        try:
            win32file.CloseHandle(vHandle)
        except:
            pass


# 提取视频i帧
# todo - 加入检测视频是否为合法视频?
def extract_iframe(video_file, iframe_interval=4000):
    print("——提取视频i帧")
    print(video_file)
    cap = cv2.VideoCapture(video_file)
    fps = cap.get(cv2.CAP_PROP_FPS)

    frame_step = int(fps * iframe_interval / 1000)
    frame_cnt = 0
    while cap.isOpened():
        ret, frame = cap.read()
        if not ret:
            break

        if frame_cnt % frame_step == 0:
            print("extract frame cnt:" + str(frame_cnt))
            cv2.imwrite('catch\\i_frames\\%d.jpg' % frame_cnt, frame)

        frame_cnt += 1

    cap.release()


# 根据config配置裁剪图片
def crop_iframe(directory):
    # 检查目录是否存在
    files.check_and_create_folder(directory)
    top_percent = config.ocr_image_crop_URBL[0] * 0.01
    bottom_percent = config.ocr_image_crop_URBL[1] * 0.01
    left_percent = config.ocr_image_crop_URBL[2] * 0.01
    right_percent = config.ocr_image_crop_URBL[3] * 0.01

    # 获取目录下所有图片文件
    image_files = [f for f in os.listdir(directory) if f.endswith(('.jpg', '.jpeg', '.png'))]

    # 循环处理每个图片文件
    for file_name in image_files:
        # 构建图片文件的完整路径
        file_path = os.path.join(directory, file_name)

        # 打开图片文件
        image = Image.open(file_path)

        # 获取图片的原始尺寸
        width, height = image.size

        # 计算裁剪区域的像素值
        top = int(height * top_percent)
        bottom = int(height * (1 - bottom_percent))
        left = int(width * left_percent)
        right = int(width * (1 - right_percent))

        # 裁剪图片
        cropped_image = image.crop((left, top, right, bottom))

        # 保存裁剪后的图片
        # cropped_file_path = os.path.splitext(file_path)[0] + '_cropped' + os.path.splitext(file_path)[1]
        cropped_file_path = file_path
        cropped_image.save(cropped_file_path)

        # 关闭图片文件
        image.close()

        print(f"已保存裁剪后的图片: {cropped_file_path}")


# OCR 分流器
def ocr_image(img_input):
    ocr_engine = config.ocr_engine
    print(f"ocr_engine:{ocr_engine}")
    if ocr_engine == "Windows.Media.Ocr.Cli":
        return ocr_image_ms(img_input)
    elif ocr_engine == "ChineseOCR_lite_onnx":
        return ocr_image_col(img_input)


# OCR文本-chineseOCRlite
def ocr_image_col(img_input):
    print("——OCR文本")
    # 输入图片路径，like 'test.jpg'
    # 实例化OcrHandle对象
    ocr_handle = OcrHandle()
    # 读取图片,并调用text_predict()方法进行OCR识别
    img = cv2.imread(img_input)
    results = ocr_handle.text_predict(img, short_size=768)
    # results = ocr_handle.text_predict(img,short_size=ocr_short_side)
    # text_predict()方法需要传入图像和短边大小,它会处理图像,执行DBNET文本检测和CRNN文本识别,并返回结果列表。
    ocr_sentence_result = ""

    # 每个结果包含[文本框坐标, 识别文字, 置信度分数]。
    for box, text, score in results:
        # print(box,text,score)
        ocr_sentence_result = ocr_sentence_result + "," + text

    print("ocr_sentence_result:")
    print(ocr_sentence_result)
    return ocr_sentence_result


# OCR文本-MS自带方式
def ocr_image_ms(img_input):
    print("——OCR文本.MS")
    text = ""
    # 调用Windows.Media.Ocr.Cli.exe,参数为图片路径
    command = ['ocr_lib\\Windows.Media.Ocr.Cli.exe', img_input]

    proc = subprocess.run(command, capture_output=True)
    encodings_try = ['gbk', 'utf-8']  # 强制兼容
    for enc in encodings_try:
        try:
            text = proc.stdout.decode(enc)
            if text is None or text == "":
                pass
            break
        except UnicodeDecodeError:
            pass

    text = str(text.encode('utf-8').decode('utf-8'))

    return text


# 计算两次结果的重合率
def compare_strings(a, b, threshold=70):
    print("——计算两次结果的重合率")
    print(f"a:{a}")
    print(f"b:{b}")

    # a 和 b 都不含任何文字
    if len(set(a) | set(b)) == 0:
        return False

    # 计算两个字符串的重合率
    overlap = len(set(a) & set(b)) / len(set(a) | set(b)) * 100
    print("overlap:" + str(overlap))

    # 判断重合率是否超过阈值
    if overlap >= threshold:
        print("重合率超过阈值")
        return True
    else:
        print("重合率没有超过阈值")
        return False


# 计算两张图片的重合率 - 通过本地文件的方式
def compare_image_similarity(img_path1, img_path2, threshold=0.7):
    # todo: 将删除操作改为整理为文件列表，降低io开销
    print("——计算两张图片的重合率")
    img1 = cv2.imread(img_path1)
    img2 = cv2.imread(img_path2)

    # 将图片转换为灰度图
    img1_gray = cv2.cvtColor(img1, cv2.COLOR_BGR2GRAY)
    img2_gray = cv2.cvtColor(img2, cv2.COLOR_BGR2GRAY)

    img1_gray = img1_gray.astype(np.float32)
    img2_gray = img2_gray.astype(np.float32)

    # 计算两个灰度图的Structural Similarity Index
    # (score, diff) = cv2.compareHist(img1_gray, img2_gray, cv2.HISTCMP_BHATTACHARYYA)
    score = cv2.compareHist(img1_gray, img2_gray, cv2.HISTCMP_BHATTACHARYYA)

    if score >= threshold:
        print(f"Images are similar with score {score}, deleting {img_path2}")
        # os.remove(img_path2)
        return True
    else:
        print(f"Images are different with score {score}")
        return False


# 计算两张图片重合率 - 通过内存内np.array比较的方式
def compare_image_similarity_np(img1, img2):
    # 将图片数据转换为灰度图像
    gray_img1 = cv2.cvtColor(img1, cv2.COLOR_BGR2GRAY)
    gray_img2 = cv2.cvtColor(img2, cv2.COLOR_BGR2GRAY)

    # 初始化ORB特征检测器
    orb = cv2.ORB_create()

    # 检测图像的关键点和描述符
    keypoints1, descriptors1 = orb.detectAndCompute(gray_img1, None)
    keypoints2, descriptors2 = orb.detectAndCompute(gray_img2, None)

    # print("-----debug:descriptors1.dtype, descriptors1.shape",descriptors1.dtype, descriptors1.shape)
    # print("-----debug:descriptors2.dtype, descriptors2.shape",descriptors2.dtype, descriptors2.shape)

    # 初始化一个暴力匹配器
    matcher = cv2.BFMatcher(cv2.NORM_HAMMING, crossCheck=True)

    # 对描述符进行匹配
    matches = matcher.match(descriptors1, descriptors2)

    # 根据匹配结果排序
    matches = sorted(matches, key=lambda x: x.distance)

    # 计算相似度
    similarity = len(matches) / max(len(keypoints1), len(keypoints2))
    print(f"---compare_image_similarity_np:{similarity}")

    return similarity


# 将图片缩小到等比例、宽度为70px的thumbnail，并返回base64
def resize_imahe_as_base64(img_path):
    img = cv2.imread(img_path)

    # 计算缩放比例,使宽度为70
    ratio = 70 / img.shape[1]
    dim = (70, int(img.shape[0] * ratio))

    # 进行缩放
    resized = cv2.resize(img, dim, interpolation=cv2.INTER_AREA)

    # 编码为JPEG格式,质量为30
    encode_param = [int(cv2.IMWRITE_JPEG_QUALITY), 10]
    _, encimg = cv2.imencode('.jpg', resized, encode_param)

    # 转为base64字符串
    img_b64 = base64.b64encode(encimg).decode('utf-8')
    return img_b64


# 回滚操作
def rollback_data(video_path,vid_file_name):
    # 擦除db中没索引完全的数据
    vid_file_name_db = vid_file_name.replace("-INDEX","")
    print(f"——回滚操作:{vid_file_name}")
    DBManager().db_rollback_delete_video_refer_record(vid_file_name_db)

    # 回滚完毕，将命名调整回来
    # file_path = os.path.join(video_path, vid_file_name)
    # new_file_path = file_path.replace("-INDEX","")
    # os.rename(file_path,new_file_path)


# 对某个视频进行处理的过程
def ocr_process_single_video(video_path, vid_file_name, iframe_path):
    # 整合完整路径
    file_path = os.path.join(video_path, vid_file_name)

    # 判断文件是否为上次索引未完成的文件
    if "-INDEX" in vid_file_name:
        # 是-执行回滚操作
        print("——存在-INDEX标识，执行回滚操作")
        rollback_data(video_path,vid_file_name)
    else:
        # 为正在索引的视频文件改名添加"-INDEX"
        new_filename = vid_file_name.replace(".","-INDEX.")
        new_file_path = os.path.join(video_path, new_filename)
        os.rename(file_path,new_file_path)
        file_path = new_file_path

    # - 提取i帧
    extract_iframe(file_path)
    # 裁剪图片
    crop_iframe('catch\\i_frames')

    img1_path_temp = ""
    img2_path_temp = ""
    is_first_process_image_similarity = 1
    # 先清理一波看起来重复的图像
    for img_file_name in os.listdir(iframe_path):
        print("processing IMG - compare:" + img_file_name)
        img = os.path.join(iframe_path, img_file_name)
        print("img=" + img)

        # 填充slot队列
        if is_first_process_image_similarity == 1:
            img1_path_temp = img
            is_first_process_image_similarity = 2
        elif is_first_process_image_similarity == 2:
            img2_path_temp = img
            is_first_process_image_similarity = 3
        else:
            is_img_same = compare_image_similarity(img1_path_temp, img2_path_temp)
            if is_img_same:
                os.remove(img2_path_temp)
                img1_path_temp = img1_path_temp
                img2_path_temp = img
            else:
                img1_path_temp = img2_path_temp
                img2_path_temp = img

    # - OCR所有i帧图像
    ocr_result_stringA = ""
    ocr_result_stringB = ""
    # todo: os.listdir 应该进行正确的数字排序、以确保是按视频顺序索引的
    for img_file_name in os.listdir(iframe_path):
        print("_____________________")
        print("processing IMG - OCR:" + img_file_name)

        img = os.path.join(iframe_path, img_file_name)
        ocr_result_stringB = ocr_image(img)
        print(f"ocr_result_stringB:{ocr_result_stringB}")

        is_str_same = compare_strings(ocr_result_stringA, ocr_result_stringB)
        if is_str_same:
            print("内容一致，不写入数据库，跳过")
        else:
            print("内容不一致")
            if utils.is_str_contain_list_word(ocr_result_stringB, config.exclude_words):
                print("内容存在排除列表词汇，不写入数据库")
            else:
                print("写入数据库")
                # 使用os.path.splitext()可以把文件名和文件扩展名分割开来，os.path.splitext(file_name)会返回一个元组,元组的第一个元素是文件名,第二个元素是扩展名
                calc_to_sec_vidname = os.path.splitext(vid_file_name)[0]
                calc_to_sec_vidname = calc_to_sec_vidname.replace("-INDEX","")
                calc_to_sec_picname = round(int(os.path.splitext(img_file_name)[0]) / 2)
                calc_to_sec_data = date_to_seconds(calc_to_sec_vidname) + calc_to_sec_picname
                # 计算图片预览图
                img_thumbnail = resize_imahe_as_base64(img)
                # 清理ocr数据
                ocr_result_write = utils.clean_dirty_text(ocr_result_stringB)
                DBManager().db_update_data(vid_file_name, img_file_name, calc_to_sec_data,
                                         ocr_result_write, True, False, img_thumbnail)
                ocr_result_stringA = ocr_result_stringB

    # 清理文件
    empty_directory(iframe_path)

    print("重命名标记")
    new_file_path = file_path.replace("-INDEX","-OCRED")
    os.rename(file_path,new_file_path)

    # new_name = vid_file_name.split('.')[0] + "-OCRED." + vid_file_name.split('.')[1]
    # os.rename(file_path, os.path.join(video_path, new_name))



# 处理文件夹内所有视频的主要流程
def ocr_process_videos(video_path, iframe_path, db_filepath):
    print("——处理所有视频的流程")

    for root,dirs,files in os.walk(video_path):
        for file in files:
            full_file_path = os.path.join(root, file)
            print("processing VID:" + full_file_path)

            # 检查视频文件是否已被索引
            if not file.endswith('.mp4') or file.endswith("-OCRED.mp4") or file.endswith("-ERROR.mp4"):
                continue

            # 判断文件是否正在被占用
            if is_file_in_use(full_file_path):
                continue
            
            # 清理文件
            empty_directory(iframe_path)
            # ocr该文件
            try:
                ocr_process_single_video(root, file, iframe_path)
            except Exception as e:
                print("Error occurred while processing :",full_file_path,e)
                video_filename = os.path.basename(full_file_path)
                new_name = video_filename.split('.')[0] + "-ERROR." + video_filename.split('.')[1]
                new_name_dir = os.path.dirname(full_file_path)
                os.rename(full_file_path, os.path.join(new_name_dir, new_name))


# 检查视频文件夹中所有文件的日期，对超出储存时限的文件进行删除操作
def remove_outdated_videofiles():
    today_datetime = datetime.datetime.today()
    days_to_subtract = config.vid_store_day
    start_datetime = datetime.datetime(2000,1,1,0,0,1)
    end_datetime = today_datetime - datetime.timedelta(days=days_to_subtract)

    video_filepath_list = files.get_file_path_list(config.record_videos_dir)
    video_filepath_list_outdate = files.get_videofile_path_list_by_time_range(video_filepath_list, start_datetime, end_datetime)
    print(f"file to remove: {video_filepath_list_outdate}")

    if len(video_filepath_list_outdate) >0:
        for item in video_filepath_list_outdate:
            print(f"removing {item}")
            send2trash(item)


# 检查视频文件夹中所有文件的日期，对超出储存时限的文件进行压缩操作
def compress_outdated_videofiles():
    today_datetime = datetime.datetime.today()
    days_to_subtract = config.vid_compress_day
    start_datetime = datetime.datetime(2000,1,1,0,0,1)
    end_datetime = today_datetime - datetime.timedelta(days=days_to_subtract)

    video_filepath_list = files.get_file_path_list(config.record_videos_dir)
    video_filepath_list_outdate = files.get_videofile_path_list_by_time_range(video_filepath_list, start_datetime, end_datetime)
    print(f"file to compress {video_filepath_list_outdate}")

    if len(video_filepath_list_outdate) >0:
        for item in video_filepath_list_outdate:
            print(f"compressing {item}")


# 检查数据库中的条目是否有对应视频



# 备份数据库



    # _________________________________________________________________


def maintain_manager_main():
    """
    数据库主维护方式
    """

    # 添加维护标识
    lock_filepath = "catch\\LOCK_MAINTAIN.MD"
    with open(lock_filepath, 'w', encoding='utf-8') as f:
        f.write(str(datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")))

    db_path = config.db_path
    db_filename = config.db_filename
    db_filepath = os.path.join(db_path, db_filename)
    record_videos_dir = config.record_videos_dir
    i_frames_dir = 'catch\\i_frames'

    if not os.path.exists(i_frames_dir):
        os.mkdir(i_frames_dir)
    if not os.path.exists(record_videos_dir):
        os.mkdir(record_videos_dir)

    # 初始化一下数据库
    DBManager().db_main_initialize()
    # 对目录下所有视频进行OCR提取处理
    ocr_process_videos(record_videos_dir, i_frames_dir, db_filepath)

    # 移除维护标识
    send2trash(lock_filepath)

