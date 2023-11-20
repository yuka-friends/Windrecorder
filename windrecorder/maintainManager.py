import base64
import datetime
import os
import shutil
import subprocess

import cv2
import numpy as np
import pandas as pd
import win32file
from PIL import Image
from send2trash import send2trash

import windrecorder.record as record
import windrecorder.utils as utils
from windrecorder import file_utils
from windrecorder.config import config
from windrecorder.db_manager import db_manager
from windrecorder.utils import date_to_seconds, empty_directory

if config.enable_ocr_chineseocr_lite_onnx:
    from ocr_lib.chineseocr_lite_onnx.model import OcrHandle

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
        vHandle = win32file.CreateFile(
            file_path,
            win32file.GENERIC_READ,
            0,
            None,
            win32file.OPEN_EXISTING,
            win32file.FILE_ATTRIBUTE_NORMAL,
            None,
        )
        return int(vHandle) == win32file.INVALID_HANDLE_VALUE
    except Exception:
        return True
    finally:
        try:
            win32file.CloseHandle(vHandle)
        except Exception:
            pass


# 提取视频i帧
# todo - 加入检测视频是否为合法视频?
def extract_iframe(video_file, iframe_interval=4000):
    print("maintainManager: extracting video i-frame")
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
            print("maintainManager: extract frame cut:" + str(frame_cnt))
            cv2.imwrite("cache\\i_frames\\%d.jpg" % frame_cnt, frame)

        frame_cnt += 1

    cap.release()


# 根据config配置裁剪图片
def crop_iframe(directory):
    # 检查目录是否存在
    file_utils.check_and_create_folder(directory)
    top_percent = config.ocr_image_crop_URBL[0] * 0.01
    bottom_percent = config.ocr_image_crop_URBL[1] * 0.01
    left_percent = config.ocr_image_crop_URBL[2] * 0.01
    right_percent = config.ocr_image_crop_URBL[3] * 0.01

    # 获取目录下所有图片文件
    image_files = [f for f in os.listdir(directory) if f.endswith((".jpg", ".jpeg", ".png"))]

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

        print(f"maintainManager: saved croped img {cropped_file_path}")


# OCR 分流器
def ocr_image(img_input):
    ocr_engine = config.ocr_engine
    # print(f"maintainManager: ocr_engine:{ocr_engine}")
    if ocr_engine == "Windows.Media.Ocr.Cli":
        return ocr_image_ms(img_input)
    elif ocr_engine == "ChineseOCR_lite_onnx":
        if config.enable_ocr_chineseocr_lite_onnx:
            return ocr_image_col(img_input)
        else:
            print("maintainManager: enable_ocr_chineseocr_lite_onnx is disabled. Fallback to Windows.Media.Ocr.Cli.")
            return ocr_image_ms(img_input)


# OCR文本-chineseOCRlite
def ocr_image_col(img_input):
    print("maintainManager: OCR text by chineseOCRlite")
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

    print("maintainManager: ocr_sentence_result:")
    print(ocr_sentence_result)
    return ocr_sentence_result


# OCR文本-MS自带方式
def ocr_image_ms(img_input):
    print("maintainManager: OCR text by Windows.Media.Ocr.Cli")
    text = ""
    # 调用Windows.Media.Ocr.Cli.exe,参数为图片路径
    command = ["ocr_lib\\Windows.Media.Ocr.Cli.exe", "-l", config.ocr_lang, img_input]

    proc = subprocess.run(command, capture_output=True)
    encodings_try = ["gbk", "utf-8"]  # 强制兼容
    for enc in encodings_try:
        try:
            text = proc.stdout.decode(enc)
            if text is None or text == "":
                pass
            break
        except UnicodeDecodeError:
            pass

    text = str(text.encode("utf-8").decode("utf-8"))

    return text


# 计算两次结果的重合率
def compare_strings(a, b, threshold=70):
    print("maintainManager: Calculate the coincidence rate of two results")

    # a 和 b 都不含任何文字
    if not a and not b:
        return True, 0

    if a.isspace() and b.isspace():
        return True, 0

    # 计算两个字符串的重合率
    # TODO: WTF is this?
    # For example:
    # "ababababab" is very similar to "aaaaabbbbb"
    overlap = len(set(a) & set(b)) / len(set(a) | set(b)) * 100
    print("overlap:" + str(overlap))

    # 判断重合率是否超过阈值
    if overlap >= threshold:
        print("The coincidence rate exceeds the threshold.")
        return True, overlap
    else:
        print("The coincidence rate does not exceed the threshold.")
        return False, overlap


# 计算两张图片的重合率 - 通过本地文件的方式
def compare_image_similarity(img_path1, img_path2, threshold=0.7):
    # todo: 将删除操作改为整理为文件列表，降低io开销
    print("maintainManager: Calculate the coincidence rate of two pictures.")
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
    print(f"maintainManager: compare_image_similarity_np:{similarity}")

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
    _, encimg = cv2.imencode(".jpg", resized, encode_param)

    # 转为base64字符串
    img_b64 = base64.b64encode(encimg).decode("utf-8")
    return img_b64


# 回滚操作
def rollback_data(video_path, vid_file_name):
    # 擦除db中没索引完全的数据
    vid_file_name_db = vid_file_name.replace("-INDEX", "")
    print(f"maintainManager: rollback {vid_file_name}")
    db_manager.db_rollback_delete_video_refer_record(vid_file_name_db)

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
        print("maintainManager: INDEX flag exists, perform rollback operation.")
        rollback_data(video_path, vid_file_name)
    else:
        # 为正在索引的视频文件改名添加"-INDEX"
        new_filename = vid_file_name.replace(".", "-INDEX.")
        new_file_path = os.path.join(video_path, new_filename)
        os.rename(file_path, new_file_path)
        file_path = new_file_path

    # - 提取i帧
    extract_iframe(file_path)
    # 裁剪图片
    crop_iframe("cache\\i_frames")

    img1_path_temp = ""
    img2_path_temp = ""
    is_first_process_image_similarity = 1
    # 先清理一波看起来重复的图像
    for img_file_name in os.listdir(iframe_path):
        print("processing IMG - compare:" + img_file_name)
        img = os.path.join(iframe_path, img_file_name)
        print("img=" + img)

        # 填充用于对比的slot队列
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
    dataframe_column_names = [
        "videofile_name",
        "picturefile_name",
        "videofile_time",
        "ocr_text",
        "is_videofile_exist",
        "is_videofile_exist",
        "thumbnail",
    ]
    dataframe_all = pd.DataFrame(columns=dataframe_column_names)

    # todo: os.listdir 应该进行正确的数字排序、以确保是按视频顺序索引的
    for img_file_name in os.listdir(iframe_path):
        print("_____________________")
        print("processing IMG - OCR:" + img_file_name)

        img = os.path.join(iframe_path, img_file_name)
        ocr_result_stringB = ocr_image(img)
        # print(f"ocr_result_stringB:{ocr_result_stringB}")

        is_str_same, _ = compare_strings(ocr_result_stringA, ocr_result_stringB)
        if is_str_same:
            print("[Skip] The content is consistent, not written to the database, skipped.")
        elif len(ocr_result_stringB) < 3:
            print("[Skip] Insufficient content, not written to the database, skipped.")
        else:
            print("Inconsistent content")
            if utils.is_str_contain_list_word(ocr_result_stringB, config.exclude_words):
                print("[Skip] The content contains exclusion list words and is not written to the database.")
            else:
                print("Writing to database.")
                # 使用os.path.splitext()可以把文件名和文件扩展名分割开来，os.path.splitext(file_name)会返回一个元组,元组的第一个元素是文件名,第二个元素是扩展名
                calc_to_sec_vidname = os.path.splitext(vid_file_name)[0]
                calc_to_sec_vidname = calc_to_sec_vidname.replace("-INDEX", "")
                calc_to_sec_picname = round(int(os.path.splitext(img_file_name)[0]) / 2)
                calc_to_sec_data = date_to_seconds(calc_to_sec_vidname) + calc_to_sec_picname
                # 计算图片预览图
                img_thumbnail = resize_imahe_as_base64(img)
                # 清理ocr数据
                ocr_result_write = utils.clean_dirty_text(ocr_result_stringB)
                # 为准备写入数据库dataframe添加记录
                dataframe_all.loc[len(dataframe_all.index)] = [
                    vid_file_name,
                    img_file_name,
                    calc_to_sec_data,
                    ocr_result_write,
                    True,
                    False,
                    img_thumbnail,
                ]
                # db_manager.db_update_data(vid_file_name, img_file_name, calc_to_sec_data,
                #                          ocr_result_write, True, False, img_thumbnail)
                ocr_result_stringA = ocr_result_stringB

    # 将完成的dataframe写入数据库
    db_manager.db_add_dataframe_to_db_process(dataframe_all)

    # 清理文件
    empty_directory(iframe_path)

    print("Add tags to video file")
    new_file_path = file_path.replace("-INDEX", "-OCRED")
    os.rename(file_path, new_file_path)
    print(f"maintainManager: --------- {file_path} Finished! ---------")

    # new_name = vid_file_name.split('.')[0] + "-OCRED." + vid_file_name.split('.')[1]
    # os.rename(file_path, os.path.join(video_path, new_name))


# 处理文件夹内所有视频的主要流程
def ocr_process_videos(video_path, iframe_path):
    print("maintainManager: Processing all video files under path.")

    # 备份最新的数据库
    db_filepath_latest = file_utils.get_db_filepath_by_datetime(datetime.datetime.now())  # 直接获取对应时间的数据库路径
    backup_dbfile(db_filepath_latest)

    for root, dirs, filess in os.walk(video_path):
        for file in filess:
            full_file_path = os.path.join(root, file)
            print("processing VID:" + full_file_path)

            # 检查视频文件是否已被索引
            if not file.endswith(".mp4") or file.endswith("-OCRED.mp4") or file.endswith("-ERROR.mp4"):
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
                # 记录错误日志
                print(
                    "maintainManager: Error occurred while processing :",
                    full_file_path,
                    e,
                )
                video_filename = os.path.basename(full_file_path)
                new_name = video_filename.split(".")[0] + "-ERROR." + video_filename.split(".")[1]
                new_name_dir = os.path.dirname(full_file_path)
                os.rename(full_file_path, os.path.join(new_name_dir, new_name))

                file_utils.check_and_create_folder("cache")
                with open(f"cache\\LOG_ERROR_{new_name}.MD", "w", encoding="utf-8") as f:
                    f.write(str(datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")) + "\n" + str(e))


# 检查视频文件夹中所有文件的日期，对超出储存时限的文件进行删除操作
def remove_outdated_videofiles():
    if config.vid_store_day == 0:
        return None

    today_datetime = datetime.datetime.today()
    days_to_subtract = config.vid_store_day
    start_datetime = datetime.datetime(2000, 1, 1, 0, 0, 1)
    end_datetime = today_datetime - datetime.timedelta(days=days_to_subtract)

    video_filepath_list = file_utils.get_file_path_list(config.record_videos_dir)
    video_filepath_list_outdate = file_utils.get_videofile_path_list_by_time_range(
        video_filepath_list, start_datetime, end_datetime
    )
    print(f"maintainManager: outdated file to remove: {video_filepath_list_outdate}")

    if len(video_filepath_list_outdate) > 0:
        for item in video_filepath_list_outdate:
            print(f"maintainManager: removing {item}")
            send2trash(item)


# 检查视频文件夹中所有文件的日期，对超出储存时限的文件进行压缩操作(todo)
def compress_outdated_videofiles():
    if config.vid_compress_day == 0:
        return None

    today_datetime = datetime.datetime.today()
    days_to_subtract = config.vid_compress_day
    start_datetime = datetime.datetime(2000, 1, 1, 0, 0, 1)
    end_datetime = today_datetime - datetime.timedelta(days=days_to_subtract)

    video_filepath_list = file_utils.get_file_path_list(config.record_videos_dir)
    video_filepath_list_outdate = file_utils.get_videofile_path_list_by_time_range(
        video_filepath_list, start_datetime, end_datetime
    )
    print(f"maintainManager: file to compress {video_filepath_list_outdate}")

    if len(video_filepath_list_outdate) > 0:
        for item in video_filepath_list_outdate:
            if not item.endswith("-COMPRESS-OCRED.mp4") and item.endswith("-OCRED.mp4"):
                print(f"maintainManager: compressing {item}")
                record.compress_video_resolution(item, config.video_compress_rate)
                send2trash(item)
    print("maintainManager: All compress tasks done!")


# 备份数据库
def backup_dbfile(db_filepath, keep_items_num=15, make_new_backup_timegap=datetime.timedelta(hours=8)):
    if db_filepath.endswith("_TEMP_READ.db"):
        return False

    db_backup_filepath = "cache\\db_backup"
    file_utils.check_and_create_folder(db_backup_filepath)
    db_filelist_name = file_utils.get_file_path_list_first_level(db_backup_filepath)
    make_new_backup_state = False

    if len(db_filelist_name) > 0:
        # 获取每个备份数据库文件对应的datatime
        db_date_dict = {}
        for item in db_filelist_name:
            result = utils.extract_datetime_from_db_backup_filename(item)
            db_date_dict[item] = result

        # 按照datatime进行排序，并获取最晚的x项
        sorted_items = sorted(db_date_dict.items(), key=lambda x: x[1])
        latest_file_time_gap = datetime.datetime.now() - sorted_items[-1][1]

        # 如果最晚一项超过了备份阈值，应当创建备份
        if latest_file_time_gap > make_new_backup_timegap:
            make_new_backup_state = True

        # 移除超过x项中较早的项目
        if len(db_filelist_name) > 15:
            lastest_items = sorted_items[-keep_items_num:]
            # 从词典中移除最晚的x项
            for item in lastest_items:
                del db_date_dict[item[0]]
            # 将最晚x项以外的都删除
            for item in db_date_dict:
                item_filepath = os.path.join(db_backup_filepath, item)
                send2trash(item_filepath)
    else:
        # 没有新的备份文件，应当创建备份
        make_new_backup_state = True

    if make_new_backup_state:
        # 创建备份
        db_filepath_backup = (
            db_backup_filepath
            + "\\"
            + os.path.splitext(os.path.basename(db_filepath))[0]
            + "_BACKUP_"
            + datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
            + ".db"
        )
        shutil.copy2(db_filepath, db_filepath_backup)

    # _________________________________________________________________


def maintain_manager_main():
    """
    数据库主维护方式
    """

    # 添加维护标识
    utils.add_maintain_lock_file("make")

    record_videos_dir = config.record_videos_dir
    i_frames_dir = "cache\\i_frames"

    if not os.path.exists(i_frames_dir):
        os.mkdir(i_frames_dir)
    if not os.path.exists(record_videos_dir):
        os.mkdir(record_videos_dir)

    # 初始化一下数据库
    db_manager.db_main_initialize()
    # 对目录下所有视频进行OCR提取处理
    ocr_process_videos(record_videos_dir, i_frames_dir)

    # 移除维护标识
    utils.add_maintain_lock_file("del")
