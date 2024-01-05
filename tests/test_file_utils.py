import unittest

import os

from windrecorder import file_utils
from windrecorder.config import config

class TestFileUtils(unittest.TestCase):
    def test_init(self):
        pass

    def test_convert_vid_filename_as_vid_filepath(self):
        vid_filename = "2020-01-02_20-12-11-OCRED.mp4"
        vid_filepath_get = file_utils.convert_vid_filename_as_vid_filepath(vid_filename)
        vid_filepath_expection = f"{config.record_videos_dir}\\{vid_filename[:7]}\\{vid_filename}"
        self.assertEqual(vid_filepath_get, vid_filepath_expection)

    def test_check_video_exist_in_videos_dir(self):
        # 创建测试所需文件
        vid_filename_dataset = ["2020-01-02_20-12-11-OCRED.mp4", "2020-01-02_20-12-11.mp4"]
        for vid_filename in vid_filename_dataset:
            vid_filepath = file_utils.convert_vid_filename_as_vid_filepath(vid_filename)
            os.makedirs(os.path.dirname(vid_filepath), exist_ok=True)
            with open(vid_filepath, 'w') as file:
                pass
        
        self.assertEqual(file_utils.check_video_exist_in_videos_dir(vid_filename_dataset[0]), vid_filename_dataset[0])
        self.assertEqual(file_utils.check_video_exist_in_videos_dir(vid_filename_dataset[1]), vid_filename_dataset[1])
        self.assertEqual(file_utils.check_video_exist_in_videos_dir("2020-09-01_21-13-14.mp4"), None)

        # 删除测试临时文件
        for vid_filename in vid_filename_dataset:
            vid_filepath = file_utils.convert_vid_filename_as_vid_filepath(vid_filename)
            os.remove(vid_filepath)
        os.rmdir(os.path.dirname(vid_filepath))
