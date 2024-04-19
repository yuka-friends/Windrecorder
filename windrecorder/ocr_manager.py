import datetime
import os
import shutil
import subprocess
import time

import cv2
import pandas as pd
import win32file
from PIL import Image, ImageDraw
from send2trash import send2trash
from skimage.metrics import structural_similarity as ssim

import windrecorder.record as record
import windrecorder.utils as utils
from windrecorder import file_utils, record_wintitle
from windrecorder.config import config
from windrecorder.const import CACHE_DIR_OCR_IMG_PREPROCESSOR
from windrecorder.db_manager import db_manager
from windrecorder.exceptions import LockExistsException
from windrecorder.lock import FileLock
from windrecorder.logger import get_logger
from windrecorder.utils import date_to_seconds

logger = get_logger(__name__)

if config.enable_ocr_chineseocr_lite_onnx:
    from ocr_lib.chineseocr_lite_onnx.model import OcrHandle

# ocr_short_side = int(config.ocr_short_size)


# 使用 win32file 的判断实现，检查文件是否被占用
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
def extract_iframe(video_file, iframe_path, iframe_interval=4000):
    logger.info(f"extracting video i-frame: {video_file}")
    if "av1" not in config.record_encoder.lower():
        cap = cv2.VideoCapture(video_file)
        fps = cap.get(cv2.CAP_PROP_FPS)

        frame_step = int(fps * iframe_interval / 1000)
        frame_cnt = 0
        while cap.isOpened():
            ret, frame = cap.read()
            if not ret:
                break

            if frame_cnt % frame_step == 0:
                logger.debug(f"extract frame cut:{str(frame_cnt)}")
                cv2.imwrite(os.path.join(iframe_path, f"{frame_cnt}.jpg"), frame)

            frame_cnt += 1

        cap.release()
    else:
        extract_iframe_by_ffmpeg(video_file, iframe_path)


def extract_iframe_by_ffmpeg(video_file, iframe_path):
    ffmpeg_cmd = [
        config.ffmpeg_path,
        "-i",
        video_file,
        "-vf",
        "select='eq(pict_type\\,I)'",
        "-r",
        "1",
        "-f",
        "image2",
        os.path.join(iframe_path, "%d.jpg"),
    ]
    subprocess.run(" ".join(ffmpeg_cmd), shell=True, check=True)
    logger.debug("extract frame cut:" + " ".join(ffmpeg_cmd))


# 根据config配置裁剪图片
def crop_iframe(directory):
    display_cnt = utils.get_display_count()
    display_info = utils.get_display_info()
    display_all_full_size = display_info[0]
    display_info = display_info[1:]
    ocr_image_crop_URBL = config.ocr_image_crop_URBL
    top_percent = []
    bottom_percent = []
    left_percent = []
    right_percent = []
    if len(ocr_image_crop_URBL) < display_cnt * 4:  # 不足时补齐参数 slot
        for i in range(display_cnt - (len(ocr_image_crop_URBL) // 4)):
            ocr_image_crop_URBL.extend([6, 6, 6, 3])
        config.set_and_save_config("ocr_image_crop_URBL", ocr_image_crop_URBL)
    for i in range(display_cnt):
        top_percent.append(config.ocr_image_crop_URBL[i * 4 + 0] * 0.01)
        bottom_percent.append(config.ocr_image_crop_URBL[i * 4 + 1] * 0.01)
        left_percent.append(config.ocr_image_crop_URBL[i * 4 + 2] * 0.01)
        right_percent.append(config.ocr_image_crop_URBL[i * 4 + 3] * 0.01)

    # 获取目录下所有图片文件
    image_files = [f for f in os.listdir(directory) if f.endswith((".jpg", ".jpeg", ".png"))]

    # 循环处理每个图片文件
    for file_name in image_files:
        # 构建图片文件的完整路径
        file_path = os.path.join(directory, file_name)
        if "_cropped" in file_name:
            continue

        image = Image.open(file_path)
        draw = ImageDraw.Draw(image)

        # 校验图片
        img_width, img_height = image.size
        fallback_condition = False
        display_index = -1
        if not config.record_single_display_index <= len(display_info):  # 当记录的显示器索引不存在于所有显示器中时，当作一个完整显示器使用默认参数处理
            fallback_condition = True
        elif config.multi_display_record_strategy == "single":
            # 当图片分辨率符合其中某个显示器的完整尺寸时，对其单独处理
            for i in display_info:  # 逐个检查显示器，是否与config index吻合
                if (
                    abs(display_info[config.record_single_display_index - 1]["width"] - img_width) < 2
                    and abs(display_info[config.record_single_display_index - 1]["height"] - img_height) < 2
                ):
                    monitors_info_process = [display_info[config.record_single_display_index - 1]]
                    display_index = config.record_single_display_index - 1
                    fallback_condition = False
                    break
                else:
                    fallback_condition = True
        # 当显示器配置为录制所有显示器、但与图片不符时，执行fallback策略：当作一个显示器、使用默认涂黑范围处理
        elif config.multi_display_record_strategy == "all" and (
            abs(display_all_full_size["width"] - img_width) > 10 or abs(display_all_full_size["height"] - img_height) > 10
        ):
            fallback_condition = True

        if fallback_condition:
            logger.info(
                f"video iframe {file_name} not matched with current display configuration({display_info}), fallback to default mask config."
            )
            monitors_info_process = [display_all_full_size]
            top_percent = [0.06]
            bottom_percent = [0.06]
            left_percent = [0.06]
            right_percent = [0.03]
        else:
            monitors_info_process = display_info

        for i, monitor in enumerate(monitors_info_process):
            # 计算裁剪区域的像素值
            try:
                top = top_percent[i]
                bottom = bottom_percent[i]
                left = left_percent[i]
                right = right_percent[i]
            except IndexError:
                top = 0.06
                bottom = 0.06
                left = 0.06
                right = 0.03

            # 如果仅录制单显示器，且通过了校验
            if display_index > 0:
                i = display_index
                left_boundary = 0
                top_boundary = 0
                right_boundary = img_width
                bottom_boundary = img_height
            else:  # 录制所有显示器情况下
                left_boundary = monitor["left"] - display_all_full_size["left"]
                top_boundary = monitor["top"] - display_all_full_size["top"]
                right_boundary = left_boundary + monitor["width"]
                bottom_boundary = top_boundary + monitor["height"]

            # 计算涂黑的区域
            top_black = (
                left_boundary,
                top_boundary,
                right_boundary,
                top_boundary + int(monitor["height"] * top),
            )
            bottom_black = (
                left_boundary,
                bottom_boundary - int(monitor["height"] * bottom),
                right_boundary,
                bottom_boundary,
            )
            left_black = (
                left_boundary,
                top_boundary,
                left_boundary + int(monitor["width"] * left),
                bottom_boundary,
            )
            right_black = (
                right_boundary - int(monitor["width"] * right),
                top_boundary,
                right_boundary,
                bottom_boundary,
            )

            # 在对应区域涂黑
            draw.rectangle(top_black, fill="black")
            draw.rectangle(bottom_black, fill="black")
            draw.rectangle(left_black, fill="black")
            draw.rectangle(right_black, fill="black")

        cropped_file_path = os.path.splitext(file_path)[0] + "_cropped" + os.path.splitext(file_path)[1]
        image.save(cropped_file_path)

        image.close()
    logger.debug(f"saved croped img in {image_files}")


# OCR 输入图片预处理器
def ocr_img_preprocessor(img_input):
    def _save_cache_img(img: Image):
        img_save_name = f"preprocess_{int(time.time()*100000000000)}.jpg"
        try:
            file_utils.ensure_dir(CACHE_DIR_OCR_IMG_PREPROCESSOR)
            save_filepath = os.path.join(CACHE_DIR_OCR_IMG_PREPROCESSOR, img_save_name)
            img.save(save_filepath)
            return save_filepath
        except Exception as e:
            logger.error(f"img({img_input}) pre process fail: {e}, {display_info=}")
            return None

    def _fallback_cropper(img: Image):
        """策略：平均地切开图像，同时确保每部分小于最大输入尺寸"""
        res = []
        img_to_process_width, img_to_process_height = img.size
        divide_factor_width = 1
        divide_factor_height = 1
        for i in range(10):  # 最多切10次，不用while来执行
            if (img_to_process_width / divide_factor_width) < SINGLE_IMG_MAX_LONG_SIDE:
                break
            divide_factor_width += 1
        for i in range(10):
            if (img_to_process_height / divide_factor_height) < SINGLE_IMG_MAX_LONG_SIDE:
                break
            divide_factor_height += 1

        crop_block_width = int(img_to_process_width / divide_factor_width)
        crop_block_height = int(img_to_process_height / divide_factor_height)
        for height_i in range(divide_factor_height):
            for width_i in range(divide_factor_width):
                cropped_img = img.crop(
                    (
                        width_i * crop_block_width,
                        height_i * crop_block_height,
                        width_i * crop_block_width + crop_block_width,
                        height_i * crop_block_height + crop_block_height,
                    )
                )
                saved_res = _save_cache_img(cropped_img)
                if saved_res is None:
                    return False
                else:
                    res.append(saved_res)
        return res

    res = []
    display_info = utils.get_display_info()
    display_all_full_size = display_info[0]
    display_info = display_info[1:]
    SINGLE_IMG_MAX_LONG_SIDE = 4000

    img = Image.open(img_input)
    img_width, img_height = img.size

    if img_width < SINGLE_IMG_MAX_LONG_SIDE and img_height < SINGLE_IMG_MAX_LONG_SIDE:  # 未超出ocr识别范围
        logger.debug("img under single 4k display")
        return [img_input]
    elif len(display_info) > 1 and (
        abs(display_all_full_size["width"] - img_width) < 10 or abs(display_all_full_size["height"] - img_height) < 10
    ):  # 逐个裁剪显示器，若单个显示器有超过最大范围，则对其进行分块裁剪
        logger.debug("img is consistent with the current display info")
        for display in display_info:
            cropped_img = img.crop(
                (display["left"], display["top"], display["left"] + display["width"], display["top"] + display["height"])
            )
            if (cropped_img.size[0] > SINGLE_IMG_MAX_LONG_SIDE) or (cropped_img.size[1] > SINGLE_IMG_MAX_LONG_SIDE):
                fallback_crop_res = _fallback_cropper(cropped_img)
                if fallback_crop_res:
                    res.extend(fallback_crop_res)
                else:
                    return [img_input]
            else:
                saved_res = _save_cache_img(cropped_img)
                if saved_res is not None:
                    res.append(saved_res)
                else:
                    return [img_input]
    else:
        fallback_crop_res = _fallback_cropper(img)
        if fallback_crop_res:
            res.extend(fallback_crop_res)
        else:
            return [img_input]
    return res


# OCR 分流器
def ocr_image(img_input):
    ocr_engine = config.ocr_engine
    logger.debug(f"ocr_engine:{ocr_engine}")
    if ocr_engine == "Windows.Media.Ocr.Cli":
        return ocr_image_ms(img_input)
    elif ocr_engine == "ChineseOCR_lite_onnx":
        if config.enable_ocr_chineseocr_lite_onnx:
            return ocr_image_col(img_input)
        else:
            logger.warning("enable_ocr_chineseocr_lite_onnx is disabled. Fallback to Windows.Media.Ocr.Cli.")
            return ocr_image_ms(img_input)


# OCR文本-chineseOCRlite
def ocr_image_col(img_input):
    logger.debug("OCR text by chineseOCRlite")
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
        # logger.info(box,text,score)
        ocr_sentence_result = ocr_sentence_result + "," + text

    logger.debug("ocr_sentence_result:")
    logger.debug(ocr_sentence_result)
    return ocr_sentence_result


# OCR文本-MS自带方式
def ocr_image_ms(img_input):
    logger.debug("OCR text by Windows.Media.Ocr.Cli")
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
    logger.debug("Calculate the coincidence rate of two results")

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
    logger.debug(f"overlap:{str(overlap)}")

    # 判断重合率是否超过阈值
    if overlap >= threshold:
        logger.debug("The coincidence rate exceeds the threshold.")
        return True, overlap
    else:
        logger.debug("The coincidence rate does not exceed the threshold.")
        return False, overlap


# 计算两张图片的重合率 - 通过本地文件的方式
# FIXME 这个函数太慢了，得优化
def compare_image_similarity(img_path1, img_path2, threshold=0.85):
    logger.debug("Calculate the coincidence rate of two pictures.")
    # 读取所有需要比较的图片
    image_paths = [img_path1, img_path2]
    images = [cv2.imread(path) for path in image_paths]

    # 缩小图像大小
    scale_factor = 0.3
    images = [cv2.resize(img, None, fx=scale_factor, fy=scale_factor) for img in images]

    # 将图片转换为灰度
    images_gray = [cv2.cvtColor(img, cv2.COLOR_BGR2GRAY) for img in images]

    # 计算两张图片的SSIM
    score = ssim(images_gray[0], images_gray[1])

    if score >= threshold:
        logger.debug(f"Images are similar with score {score}, deleting {img_path2}")
        return True
    else:
        logger.debug(f"Images are different with score {score}")
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

    # logger.info("-----debug:descriptors1.dtype, descriptors1.shape",descriptors1.dtype, descriptors1.shape)
    # logger.info("-----debug:descriptors2.dtype, descriptors2.shape",descriptors2.dtype, descriptors2.shape)

    # 初始化一个暴力匹配器
    matcher = cv2.BFMatcher(cv2.NORM_HAMMING, crossCheck=True)

    # 对描述符进行匹配
    matches = matcher.match(descriptors1, descriptors2)

    # 根据匹配结果排序
    matches = sorted(matches, key=lambda x: x.distance)

    # 计算相似度
    similarity = len(matches) / max(len(keypoints1), len(keypoints2))
    logger.debug(f"compare_image_similarity_np:{similarity}")

    return similarity


# 将图片缩小到等比例、宽度为70px的thumbnail，并返回base64
def resize_image_as_base64(img_path):
    img = Image.open(img_path)
    img_b64 = utils.resize_image_as_base64(img)

    return img_b64


# 移除df中指定列包含重复项的行
def remove_duplicates_in_df(df: pd.DataFrame, column: str):
    logger.debug("started.")
    duplicate_rows_to_drop = []
    for i in range(len(df)):
        for j in range(i + 1, len(df)):
            is_duplicate, similarity = compare_strings(df.iloc[i][column], df.iloc[j][column], threshold=94)
            if is_duplicate:
                duplicate_rows_to_drop.append(j)
    logger.debug("done.")
    return df.drop(df.index[duplicate_rows_to_drop])


# 回滚操作
def rollback_data(video_path, vid_file_name):
    # 擦除db中没索引完全的数据
    logger.info(f"rollback {vid_file_name}")
    db_manager.db_rollback_delete_video_refer_record(vid_file_name)


def ocr_core_logic(file_path, vid_file_name, iframe_path):
    # - 提取i帧
    extract_iframe(file_path, iframe_path)
    # 裁剪图片
    crop_iframe(iframe_path)

    display_count = utils.get_display_count()
    # 假设屏幕大小一致，每块屏幕需要 15% 的不同画面，与 30% 的不同文字
    threshold_img_similarity = 1 - 0.15 / display_count
    threshold_str_similarity = 100 - 30 / display_count

    img1_path_temp = ""
    img2_path_temp = ""
    is_first_process_image_similarity = 1
    # 根据时间先后顺序，清理一波看起来重复的图像
    # FIXME 寻找更好的方法可以清理所有重复图像，而不是按时间先后依次比对？
    sotred_file = sorted(os.listdir(iframe_path), key=lambda x: int("".join(filter(str.isdigit, x))))
    for img_file_name in sotred_file:
        if "_cropped" not in img_file_name:
            continue
        logger.debug(f"processing IMG - compare:{img_file_name}")
        img_filepath = os.path.join(iframe_path, img_file_name)
        logger.debug(f"img={img_filepath}")

        # 填充用于对比的slot队列
        if is_first_process_image_similarity == 1:
            img1_path_temp = img_filepath
            is_first_process_image_similarity = 2
        elif is_first_process_image_similarity == 2:
            img2_path_temp = img_filepath
            is_first_process_image_similarity = 3
        else:
            is_img_same = compare_image_similarity(img1_path_temp, img2_path_temp, threshold_img_similarity)
            if is_img_same:
                os.remove(img2_path_temp)
                img1_path_temp = img1_path_temp
                img2_path_temp = img_filepath
            else:
                img1_path_temp = img2_path_temp
                img2_path_temp = img_filepath

    # - OCR所有i帧图像
    ocr_result_stringA = ""
    ocr_result_stringB = ""
    dataframe_column_names = [
        "videofile_name",
        "picturefile_name",
        "videofile_time",
        "ocr_text",
        "is_videofile_exist",
        "is_picturefile_exist",
        "thumbnail",
        "win_title",
    ]
    dataframe_all = pd.DataFrame(columns=dataframe_column_names)

    sotred_file = sorted(os.listdir(iframe_path), key=lambda x: int("".join(filter(str.isdigit, x))))
    for img_file_name in sotred_file:
        if "_cropped" not in img_file_name:
            continue

        logger.debug("_____________________")
        logger.debug(f"processing IMG - OCR:{img_file_name}")

        img_orgin_not_crop_filepath = os.path.join(iframe_path, img_file_name.replace("_cropped", ""))
        img_crop_filepath = os.path.join(iframe_path, img_file_name)
        img_crop_preprocess_list = ocr_img_preprocessor(img_crop_filepath)
        ocr_result_stringB = ""
        for img_filepath in img_crop_preprocess_list:
            ocr_result_stringB += ocr_image(img_filepath)
        logger.debug(f"OCR res:{ocr_result_stringB}")

        is_str_same, _ = compare_strings(ocr_result_stringA, ocr_result_stringB, threshold_str_similarity)
        if is_str_same:
            logger.debug("[Skip] The content is consistent, not written to the database, skipped.")
        elif len(ocr_result_stringB) < 3:
            logger.debug("[Skip] Insufficient content, not written to the database, skipped.")
        else:
            logger.debug("Inconsistent content")
            if utils.is_str_contain_list_word(ocr_result_stringB, config.exclude_words):
                logger.debug("[Skip] The content contains exclusion list words and is not written to the database.")
            else:
                logger.debug("Writing to database.")
                # 使用os.path.splitext()可以把文件名和文件扩展名分割开来，os.path.splitext(file_name)会返回一个元组,元组的第一个元素是文件名,第二个元素是扩展名
                calc_to_sec_vidname = os.path.splitext(vid_file_name)[0]
                calc_to_sec_vidname = calc_to_sec_vidname.replace("-INDEX", "")
                calc_to_sec_picname = round(
                    int(os.path.splitext(img_file_name.replace("_cropped", ""))[0]) / int(config.record_framerate)
                )  # 用fps折算秒数
                calc_to_sec_data = date_to_seconds(calc_to_sec_vidname) + calc_to_sec_picname
                win_title = record_wintitle.get_wintitle_by_timestamp(calc_to_sec_data)
                win_title = record_wintitle.optimize_wintitle_name(win_title)
                # 检查窗口标题是否在跳过词中
                if utils.is_str_contain_list_word(win_title, config.exclude_words):
                    logger.debug(
                        "[Skip] The window title name contains exclusion list words and is not written to the database."
                    )
                    continue
                # 计算图片预览图
                img_thumbnail = resize_image_as_base64(img_orgin_not_crop_filepath)
                # 清理ocr数据
                ocr_result_write = utils.clean_dirty_text(ocr_result_stringB) + " -||- " + str(win_title)
                # 为准备写入数据库dataframe添加记录
                dataframe_all.loc[len(dataframe_all.index)] = [
                    vid_file_name,
                    img_file_name,
                    calc_to_sec_data,
                    ocr_result_write,
                    True,
                    False,
                    img_thumbnail,
                    win_title,
                ]
                ocr_result_stringA = ocr_result_stringB

    # 对dataframe去重
    if config.index_reduce_same_content_at_different_time:
        dataframe_all = remove_duplicates_in_df(dataframe_all, "ocr_text")

    # 将完成的dataframe写入数据库
    db_manager.db_add_dataframe_to_db_process(dataframe_all)
    # 清理缓存
    if os.path.exists(CACHE_DIR_OCR_IMG_PREPROCESSOR):
        file_utils.empty_directory(CACHE_DIR_OCR_IMG_PREPROCESSOR)


# 对某个视频进行处理的过程
def ocr_process_single_video(video_path, vid_file_name, iframe_path, optimize_for_high_framerate_vid=False):
    # with acquire_ocr_lock(vid_file_name):
    iframe_sub_path = os.path.join(iframe_path, os.path.splitext(vid_file_name)[0])
    # 整合完整路径
    file_path = os.path.join(video_path, vid_file_name)

    # 判断文件是否为上次索引未完成的文件
    if "-INDEX" in vid_file_name:
        # 是-执行回滚操作
        logger.info("INDEX flag exists, perform rollback operation.")
        # 这里我们保证 vid_file_name 不包含 -INDEX
        vid_file_name = vid_file_name.replace("-INDEX", "")
        rollback_data(video_path, vid_file_name)
        # 保证进入 ocr_core_logic 前 iframe_sub_path 是空的
        try:
            shutil.rmtree(iframe_sub_path)
        except FileNotFoundError:
            pass
    else:
        # 为正在索引的视频文件改名添加"-INDEX"
        new_filename = vid_file_name.replace(".", "-INDEX.")
        new_file_path = os.path.join(video_path, new_filename)
        os.rename(file_path, new_file_path)
        file_path = new_file_path

    file_utils.ensure_dir(iframe_sub_path)
    try:
        if optimize_for_high_framerate_vid:
            vid_filepath_optimize = convert_temp_optimize_vidfile_for_ocr(file_path)
            if vid_filepath_optimize is None:
                raise FileNotFoundError
            ocr_core_logic(vid_filepath_optimize, vid_file_name, iframe_sub_path)
            try:
                os.remove(vid_filepath_optimize)
            except FileNotFoundError:
                pass
        else:
            ocr_core_logic(file_path, vid_file_name, iframe_sub_path)
    except Exception as e:
        # 记录错误日志
        logger.error(f"Error occurred while processing :{file_path=}, {e=}")
        new_name = vid_file_name.split(".")[0] + "-ERROR." + vid_file_name.split(".")[1]
        new_name_dir = os.path.dirname(file_path)
        os.rename(file_path, os.path.join(new_name_dir, new_name))

        with open(f"cache\\LOG_ERROR_{new_name}.MD", "w", encoding="utf-8") as f:
            f.write(f'{datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")}\n{e}')
    else:
        logger.info("Add tags to video file")
        new_file_path = file_path.replace("-INDEX", "-OCRED")
        os.rename(file_path, new_file_path)
        logger.info(f"--------- {file_path} Finished! ---------")
    finally:
        # 清理文件
        if not config.enable_img_embed_search:
            shutil.rmtree(iframe_sub_path)  # 先不清理文件，留给 img embed 流程继续使用，由它清理
        pass


def convert_temp_optimize_vidfile_for_ocr(vid_filepath):
    """
    将输入视频转为 2fps 的临时视频，以便于 OCR 拆帧识别
    """
    output_temp_vid_filepath = os.path.join(
        os.path.dirname(vid_filepath), f"{os.path.basename(vid_filepath).split('.')[0]}-2FPS.mp4"
    )
    try:
        os.remove(output_temp_vid_filepath)
    except FileNotFoundError:
        pass
    ffmpeg_cmd = [config.ffmpeg_path, "-i", vid_filepath, "-vf", "fps=2", output_temp_vid_filepath]
    try:
        subprocess.run(ffmpeg_cmd, check=True)
        logger.info(f"convert {vid_filepath} into {output_temp_vid_filepath}")
        return output_temp_vid_filepath
    except subprocess.CalledProcessError as ex:
        logger.error(f"convert_temp_optimize_vidfile_for_ocr: {ex.cmd} failed with return code {ex.returncode}")
        return None


# 处理文件夹内所有视频的主要流程
def ocr_process_videos(video_path, iframe_path):
    logger.info("Processing all video files.")

    # 备份最新的数据库
    db_filepath_latest = file_utils.get_db_filepath_by_datetime(datetime.datetime.now())  # 直接获取对应时间的数据库路径
    backup_dbfile(db_filepath_latest)

    for root, dirs, filess in os.walk(video_path):
        for file in filess:
            full_file_path = os.path.join(root, file)
            logger.debug(f"processing VID: {full_file_path}")

            # 检查视频文件是否已被索引
            if not file.endswith(".mp4") or "-OCRED" in file or "-ERROR" in file:
                continue

            # 判断文件是否正在被占用
            if is_file_in_use(full_file_path):
                continue

            try:
                # ocr 该文件。如果使用了超过 2fps 的录制参数，先优化处理视频然后再 ocr
                ocr_process_single_video(
                    root, file, iframe_path, optimize_for_high_framerate_vid=(config.record_framerate > 2)
                )
            except LockExistsException:
                pass


# 检查视频文件夹中所有文件的日期，对超出储存时限的文件进行删除操作
def remove_outdated_videofiles(video_queue_batch=60):
    if config.vid_store_day == 0:
        return None

    video_process_count = 0

    today_datetime = datetime.datetime.today()
    days_to_subtract = config.vid_store_day
    start_datetime = datetime.datetime(2000, 1, 1, 0, 0, 1)
    end_datetime = today_datetime - datetime.timedelta(days=days_to_subtract)

    video_filepath_list = file_utils.get_file_path_list(config.record_videos_dir_ud)
    video_filepath_list_outdate = file_utils.get_videofile_path_list_by_time_range(
        video_filepath_list, start_datetime, end_datetime
    )
    logger.info(f"outdated file to remove: {video_filepath_list_outdate}")

    if len(video_filepath_list_outdate) > 0:
        for item in video_filepath_list_outdate:
            logger.info(f"removing {item}, {video_process_count=}, {video_queue_batch=}")
            send2trash(item)
            video_process_count += 1
            if video_process_count > video_queue_batch:
                break


# 检查视频文件夹中所有文件的日期，对超出储存时限的文件进行压缩操作(todo)
def compress_outdated_videofiles(video_queue_batch=30):
    if config.vid_compress_day == 0:
        return None

    video_process_count = 0

    today_datetime = datetime.datetime.today()
    days_to_subtract = config.vid_compress_day
    start_datetime = datetime.datetime(2000, 1, 1, 0, 0, 1)
    end_datetime = today_datetime - datetime.timedelta(days=days_to_subtract)

    video_filepath_list = file_utils.get_file_path_list(config.record_videos_dir_ud)
    video_filepath_list_outdate = file_utils.get_videofile_path_list_by_time_range(
        video_filepath_list, start_datetime, end_datetime
    )
    logger.info(f"file to compress {video_filepath_list_outdate}")

    if len(video_filepath_list_outdate) > 0:
        for item in video_filepath_list_outdate:
            if "-COMPRESS" not in item and "-OCRED" in item and "-ERROR" not in item:
                logger.info(f"compressing {item}, {video_process_count=}, {video_queue_batch=}")
                try:
                    record.compress_video_resolution(item, config.video_compress_rate)
                    send2trash(item)
                    video_process_count += 1
                except subprocess.CalledProcessError as e:
                    logger.error(f"{item} seems invalid, error: {e}")
                    os.rename(item, item.replace("-OCRED", "-OCRED-ERROR"))
                except Exception as e:
                    logger.error(f"{item} compress fail, error: {e}")
                if video_process_count > video_queue_batch:
                    break
        logger.info("All compress tasks done!")


# 备份数据库
def backup_dbfile(db_filepath, keep_items_num=15, make_new_backup_timegap=datetime.timedelta(hours=8)):
    if "_TEMP_READ" in db_filepath:
        return False

    db_backup_filepath = "cache\\db_backup"
    file_utils.ensure_dir(db_backup_filepath)
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


def acquire_ocr_lock(file_name: str):
    file_utils.ensure_dir(config.maintain_lock_path)
    file_name = file_name.replace(".mp4", ".md")
    return FileLock(os.path.join(config.maintain_lock_path, file_name), datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S"))


def ocr_manager_main():
    """
    数据库主维护方式
    """

    record_videos_dir = config.record_videos_dir_ud
    i_frames_dir = config.iframe_dir

    file_utils.ensure_dir(i_frames_dir)
    file_utils.ensure_dir(record_videos_dir)

    # 对目录下所有视频进行OCR提取处理
    ocr_process_videos(record_videos_dir, i_frames_dir)
