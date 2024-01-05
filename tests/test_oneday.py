import unittest
import os
import datetime

from windrecorder.oneday import OneDay
from windrecorder import file_utils
from windrecorder.config import config

class TestOneday(unittest.TestCase):
    def test_init(self):
        pass

    def test_find_closest_video_by_filesys(self):
        # 创建测试所需文件
        vid_filename_dataset = [
            "2020-01-02_11-09-18-OCRED.mp4",
            "2020-01-02_12-44-59.mp4",
            "2020-01-03_11-17-02-OCRED-COMPRESS.mp4",
            "2020-01-03_11-54-37-OCRED-IMGEMB.mp4",
            "2020-01-04_15-45-49-INDEX.mp4"
            ]
        for vid_filename in vid_filename_dataset:
            vid_filepath = file_utils.convert_vid_filename_as_vid_filepath(vid_filename)
            os.makedirs(os.path.dirname(vid_filepath), exist_ok=True)
            with open(vid_filepath, 'w') as file:
                pass
        
        out_of_bound_filepath = os.path.join(config.record_videos_dir, "2020-01-04_12-19-01.mp4")
        with open(out_of_bound_filepath, 'w') as file:
            pass

        res_out_of_time_range = OneDay().find_closest_video_by_filesys(datetime.datetime(2021,1,3,11,18,55))
        self.assertEqual(res_out_of_time_range, (False, None))
        res_in_time_range = OneDay().find_closest_video_by_filesys(datetime.datetime(2020,1,3,11,18,55))
        self.assertEqual(res_in_time_range, (True, "2020-01-03_11-17-02-OCRED-COMPRESS.mp4"))
        res_out_of_bound_not_in_correct_dir = OneDay().find_closest_video_by_filesys(datetime.datetime(2020,1,4,12,19,1))
        self.assertEqual(res_out_of_bound_not_in_correct_dir, (False, None))

        # 删除测试临时文件
        for vid_filename in vid_filename_dataset:
            vid_filepath = file_utils.convert_vid_filename_as_vid_filepath(vid_filename)
            os.remove(vid_filepath)
        os.remove(out_of_bound_filepath)
        os.rmdir(os.path.dirname(vid_filepath))