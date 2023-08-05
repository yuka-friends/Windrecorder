import cv2
import numpy as np
import os
from chineseocr_lite_onnx.model import OcrHandle 
from utils import empty_directory
import base64
import subprocess
import tempfile
import dbManager
import json

with open('config.json') as f:
    config = json.load(f)
print("config.json:")
print(config)
# ocr_short_side = int(config["ocr_short_size"])



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
            print("frame_cnt:"+str(frame_cnt))
            cv2.imwrite('i_frames/%d.jpg' % frame_cnt, frame)
        
        frame_cnt += 1

    cap.release()


# OCR 分流器
def ocr_image(img_input):
    with open('config.json') as f:
        config = json.load(f)
    ocr_engine = config["ocr_engine"]
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
    results = ocr_handle.text_predict(img,short_size=768)
    # results = ocr_handle.text_predict(img,short_size=ocr_short_side)
    # text_predict()方法需要传入图像和短边大小,它会处理图像,执行DBNET文本检测和CRNN文本识别,并返回结果列表。
    ocr_sentence_result = ""

    # 每个结果包含[文本框坐标, 识别文字, 置信度分数]。
    for box,text,score in results:
        # print(box,text,score)
        ocr_sentence_result = ocr_sentence_result + "," + text

    print("ocr_sentence_result:")
    print(ocr_sentence_result)
    return ocr_sentence_result


# OCR文本-MS自带方式
def ocr_image_ms(img_input):
    print("——OCR文本.MS")
    # 调用Windows.Media.Ocr.Cli.exe,参数为图片路径
    command = ['Windows.Media.Ocr.Cli.exe', img_input]
    
    # 在临时文件中捕获输出
    with tempfile.TemporaryFile() as tempf:
        # proc = subprocess.Popen(command, stdout=tempf)
        proc = subprocess.Popen(command, stdout=subprocess.PIPE)

        text = proc.stdout.read().decode('gbk')
        text = str(text.encode('utf-8').decode('utf-8'))
    
    return text


# 计算两次结果的重合率
def compare_strings(a, b, threshold=70):
    print("——计算两次结果的重合率")
    print(f"a:{a}")
    print(f"b:{b}")
    # 计算两个字符串的重合率
    overlap = len(set(a) & set(b)) / len(set(a) | set(b)) * 100
    print("overlap:"+str(overlap))
    
    # 判断重合率是否超过阈值
    if overlap >= threshold:
        print("重合率超过阈值")
        return True
    else:
        print("重合率没有超过阈值")
        return False


# 计算两张图片的重合率
def compare_image_similarity(img_path1, img_path2, threshold=0.7):
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
        os.remove(img_path2)
        return True
    else:
        print(f"Images are different with score {score}")
        return False


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


# 处理视频的流程
def ocr_process_videos(video_path,iframe_path,db_filepath):
    print("——处理视频的流程")
    vid_file_names = os.listdir(video_path) 
    print("video file listdir:")
    print(vid_file_names)

    for vid_file_name in vid_file_names:
        print("processing VID:"+vid_file_name)
        # 清理文件
        empty_directory(iframe_path)

        if not vid_file_name.endswith('.mp4') or vid_file_name.endswith("-OCRED.mp4"):
            continue

        file_path = os.path.join(video_path,vid_file_name)
        # 处理流程
        # - 提取i帧
        extract_iframe(file_path)

        img1_path_temp = ""
        img2_path_temp = ""
        is_first_process_image_similarity = 1
        # 先清理一波看起来重复的图像
        for img_file_name in os.listdir(iframe_path):
            print("processing IMG - compare:"+ img_file_name)
            img = os.path.join(iframe_path, img_file_name)
            print("img="+img)

            if is_first_process_image_similarity ==1 :
                img1_path_temp = img
                is_first_process_image_similarity = 2
            elif is_first_process_image_similarity ==2 :
                img2_path_temp = img
                is_first_process_image_similarity = 3
            else:
                is_img_same = compare_image_similarity(img1_path_temp,img2_path_temp)
                if is_img_same:
                    img1_path_temp = img1_path_temp
                    img2_path_temp = img
                else :
                    img1_path_temp = img2_path_temp
                    img2_path_temp = img


        # - OCR所有i帧图像
        ocr_result_stringA = ""
        ocr_result_stringB = ""
        for img_file_name in os.listdir(iframe_path):
            print("processing IMG - OCR:"+ img_file_name)

            img = os.path.join(iframe_path, img_file_name) 
            ocr_result_stringB = ocr_image(img)
            print(f"ocr_result_stringB:{ocr_result_stringB}")

            is_str_same = compare_strings(ocr_result_stringA,ocr_result_stringB)
            if is_str_same:
                print("内容一致，不写入数据库，跳过")
            else:
                print("内容不一致，写入数据库")
                # 使用os.path.splitext()可以把文件名和文件扩展名分割开来，os.path.splitext(file_name)会返回一个元组,元组的第一个元素是文件名,第二个元素是扩展名
                calc_to_sec_vidname = os.path.splitext(vid_file_name)[0]
                calc_to_sec_picname = round(int(os.path.splitext(img_file_name)[0]) / 2)
                calc_to_sec_data = dbManager.date_to_seconds(calc_to_sec_vidname) + calc_to_sec_picname
                # 计算图片预览图
                img_thumbnail = resize_imahe_as_base64(img)
                dbManager.db_update_data(db_filepath,vid_file_name,img_file_name,calc_to_sec_data, ocr_result_stringB,True,False,img_thumbnail)
                dbManager.db_print_all_data(db_filepath)
                ocr_result_stringA = ocr_result_stringB

        # 清理文件
        empty_directory(iframe_path)

        print("重命名标记")
        new_name = vid_file_name.split('.')[0] + "-OCRED." + vid_file_name.split('.')[1]
        os.rename(file_path,os.path.join(video_path, new_name))   



#_________________________________________________________________
def maintain_manager_main():
    with open('config.json') as f:
        config = json.load(f)
    print("config.json:")
    print(config)

    db_path = config["db_path"]
    db_filename = config["db_filename"]
    db_filepath = db_path +"/"+ db_filename
    record_videos_dir = config["record_videos_dir"]
    i_frames_dir = 'i_frames'

    if not os.path.exists(i_frames_dir):
        os.mkdir(i_frames_dir)
    if not os.path.exists(record_videos_dir):
        os.mkdir(record_videos_dir)

    # 初始化一下数据库
    dbManager.db_main_initialize()
    ocr_process_videos(record_videos_dir,i_frames_dir,db_filepath)

    # 打印结果
    # dbManager.db_print_all_data(db_filepath)


