import json
import os
import sqlite3
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import numpy as np
import pytest


@pytest.fixture
def capture(db, monkeypatch):
    from windrecorder import record

    monkeypatch.setattr(record, "db_manager", db)
    return record


def cached_capture(workspace, timestamps=("2024-01-01_12-00-00",)):
    from windrecorder.utils import dtstr_to_seconds

    folder = workspace / "cache_screenshot/2024-01-01_12-00-00"
    folder.mkdir(parents=True, exist_ok=True)
    rows = [
        dict(
            vid_file_name="2024-01-01_12-00-00.mp4",
            img_file_name=f"{value}.png",
            videofile_time=dtstr_to_seconds(value),
            ocr_text="important text",
            win_title="editor",
            thumbnail="image",
        )
        for value in timestamps
    ]
    (folder / "tmp_db.json").write_text(json.dumps({"data": rows}), encoding="utf-8")
    return folder


def test_small_capture_survives_and_retry_without_marker_is_idempotent(capture, db, workspace):
    folder = cached_capture(workspace)
    assert capture.submit_data_to_sqlite_db_process(str(folder))
    assert db.db_num_records() == 1
    (folder / "-SUBMIT").rmdir()
    assert capture.submit_data_to_sqlite_db_process(str(folder))
    assert db.db_num_records() == 1
    assert (folder / "tmp_db.json").exists()


def test_concurrent_capture_retries_insert_once(capture, db, workspace):
    folder = cached_capture(workspace)
    with ThreadPoolExecutor(max_workers=2) as pool:
        assert all(pool.map(capture.submit_data_to_sqlite_db_process, [str(folder)] * 2))
    assert db.db_num_records() == 1


def test_partial_cross_month_commit_can_retry_without_duplicates(capture, db, workspace, monkeypatch):
    folder = cached_capture(workspace, ("2024-01-31_23-59-59", "2024-02-01_00-00-00"))
    original = db.db_add_dataframe_to_db

    def fail_second(path, frame, **kwargs):
        if "2024-02" in str(path):
            raise sqlite3.OperationalError("database is locked")
        return original(path, frame, **kwargs)

    with monkeypatch.context() as patch:
        patch.setattr(db, "db_add_dataframe_to_db", fail_second)
        assert not capture.submit_data_to_sqlite_db_process(str(folder))
    assert (folder / "tmp_db.json").exists()
    assert not (folder / "-SUBMIT").exists()
    assert capture.submit_data_to_sqlite_db_process(str(folder))
    assert db.db_num_records() == 2


def test_maintenance_leaves_active_or_unsubmitted_cache_alone(capture, workspace, monkeypatch):
    folder = cached_capture(workspace)
    (folder / ".capture.lock").write_text(str(os.getpid()), encoding="utf-8")

    def forbidden(*args):
        pytest.fail("Maintenance must not touch an active recording")

    with monkeypatch.context() as patch:
        patch.setattr(capture, "submit_data_to_sqlite_db_process", forbidden)
        patch.setattr(capture, "convert_screenshots_dir_into_video_process", forbidden)
        capture.index_cache_screenshots_dir_process()
        capture.clean_cache_screenshots_dir_process()
    (folder / ".capture.lock").unlink()
    (folder / "tmp_db.json").write_text('{"incomplete":', encoding="utf-8")
    capture.index_cache_screenshots_dir_process()
    capture.clean_cache_screenshots_dir_process()
    assert folder.exists()
    assert (folder / "tmp_db.json").read_text(encoding="utf-8") == '{"incomplete":'


def test_low_texture_and_changed_resolution_are_safe_to_compare():
    from windrecorder.ocr_manager import compare_image_similarity_np

    black = np.zeros((120, 120, 3), dtype="uint8")
    assert compare_image_similarity_np(black, black) == 1
    assert compare_image_similarity_np(black, black + 255) == 0
    assert compare_image_similarity_np(black, np.zeros((90, 120, 3), dtype="uint8")) == 0


def test_frame_comparison_retries_unaccepted_frame_and_reuses_previous_features(monkeypatch):
    from windrecorder.capture import FrameChangeDetector

    first = np.random.default_rng(42).integers(0, 256, (200, 200, 3), dtype="uint8")
    second = np.roll(first, 3, axis=0)
    detector = FrameChangeDetector()
    feature_calls = []
    features = detector._features

    def count_features(gray):
        feature_calls.append(gray)
        return features(gray)

    monkeypatch.setattr(detector, "_features", count_features)
    assert detector.compare(first) == 0
    assert detector.compare(first) == 0  # OCR failed: caller did not accept it.
    detector.accept()
    assert detector.compare(first) == 1
    assert len(feature_calls) == 0  # Identical frames need no ORB extraction.
    assert 0 <= detector.compare(second) <= 1
    assert len(feature_calls) == 2
    detector.accept()
    assert detector.compare(second) == 1
    assert 0 <= detector.compare(np.roll(first, 6, axis=0)) <= 1
    assert len(feature_calls) == 3  # Only the new frame needs extraction.


def test_maintenance_lock_is_exclusive_and_released_after_failure(capture, workspace, monkeypatch):
    from windrecorder.capture import cache_maintenance_lock

    folder = cached_capture(workspace)
    calls = []
    monkeypatch.setattr(capture, "_convert_screenshots_dir_into_video_process", lambda path: calls.append(path))
    monkeypatch.setattr(capture, "_clean_cache_screenshots_dir_process", lambda: calls.append("clean"))
    with pytest.raises(RuntimeError), cache_maintenance_lock(folder.parent) as acquired:
        assert acquired
        capture.convert_screenshots_dir_into_video_process(str(folder))
        capture.clean_cache_screenshots_dir_process()
        assert calls == []
        raise RuntimeError("interrupted maintenance")
    capture.convert_screenshots_dir_into_video_process(str(folder))
    capture.clean_cache_screenshots_dir_process()
    assert calls == [str(folder), "clean"]


def test_recording_retries_failed_ocr_and_stops_using_elapsed_time(capture, db, monkeypatch):
    import datetime
    from types import SimpleNamespace

    from mss.screenshot import ScreenShot

    elapsed = [0.0]

    def sleep(seconds):
        elapsed[0] += seconds

    class Clock(datetime.datetime):
        @classmethod
        def now(cls):
            return datetime.datetime(2024, 1, 1, 12) + datetime.timedelta(seconds=elapsed[0])

    monkeypatch.setattr(capture, "time", SimpleNamespace(monotonic=lambda: elapsed[0], sleep=sleep))
    monkeypatch.setattr(capture, "datetime", SimpleNamespace(datetime=Clock))
    monkeypatch.setattr(capture, "get_current_wintitle", lambda: "test editor")
    monkeypatch.setattr(capture.utils, "is_screen_locked", lambda: False)
    monkeypatch.setattr(capture.utils, "is_system_awake", lambda: True)
    frame = ScreenShot(bytearray(32 * 32 * 4), {"left": 0, "top": 0, "width": 32, "height": 32})
    monkeypatch.setattr(capture, "get_screenshot_single_display", lambda _: frame)
    for name, value in dict(
        record_seconds=5,
        screenshot_interval_second=1,
        exclude_words=[],
        record_deep_linking=False,
        record_screenshot_method_capture_foreground_window_only=False,
        multi_display_record_strategy="single",
        screenshot_compare_similarity=0.9,
    ).items():
        monkeypatch.setattr(capture.config, name, value)
    calls = []

    def ocr(path):
        assert (Path(path).parent / ".capture.lock").exists()
        calls.append(path)
        elapsed[0] += 4
        if len(calls) == 1:
            raise RuntimeError("transient OCR failure")
        return "Recovered important text"

    monkeypatch.setattr(capture, "ocr_image", ocr)
    folder = Path(capture.record_screen_via_screenshot_process())
    assert len(calls) == 2
    assert elapsed[0] == 10
    assert not (folder / ".capture.lock").exists()
    assert (folder / "-SUBMIT").exists()
    assert len(json.loads((folder / "tmp_db_json_all_files.json").read_text(encoding="utf-8"))["data"]) == 2
    assert db.db_num_records() == 1


def test_wechat_ocr_immediate_callback_and_timeout_do_not_reuse_old_result(monkeypatch):
    import threading
    from types import SimpleNamespace

    from windrecorder import ocr_manager

    monkeypatch.setattr(ocr_manager, "wx_ocr_complete_event", threading.Event(), raising=False)
    monkeypatch.setattr(ocr_manager, "WECHAT_OCR_TIMEOUT_SECONDS", 0.01)
    manager = SimpleNamespace(
        DoOCRTask=lambda path: ocr_manager.wx_ocr_result_callback(path, {"ocrResult": [{"text": "fresh result"}]})
    )
    monkeypatch.setattr(ocr_manager, "wx_ocr_manager", manager, raising=False)
    assert ocr_manager.ocr_image_wechatocr("first.png") == "fresh result"
    # A synchronous callback must remain signalled until the request consumes it.
    manager.DoOCRTask = lambda path: ocr_manager.wx_ocr_result_callback("first.png", {"ocrResult": [{"text": "stale"}]})
    with pytest.raises(TimeoutError):
        ocr_manager.ocr_image_wechatocr("second.png")
    assert ocr_manager.wx_ocr_pending_path is None


def test_corrupt_conversion_metadata_does_not_discard_capture(capture, workspace):
    folder = cached_capture(workspace)
    assert capture.submit_data_to_sqlite_db_process(str(folder))
    (folder / "tmp_db_json_all_files.json").write_text("{}", encoding="utf-8")
    assert capture.convert_screenshots_dir_into_video_process(str(folder)) == str(folder)
    capture.clean_cache_screenshots_dir_process()
    assert folder.exists()


def test_conversion_requires_submission_and_completed_output(capture, workspace, monkeypatch):
    folder = cached_capture(workspace)
    calls = []

    def encode(path):
        calls.append(path)
        return "intermediate.mp4", False

    monkeypatch.setattr(capture, "make_screenshots_into_video_via_dir_path", encode)
    monkeypatch.setattr(capture, "compress_video_resolution", lambda *a, **kw: "missing.mp4")
    assert capture.convert_screenshots_dir_into_video_process(str(folder)) == str(folder)
    assert calls == []
    assert capture.submit_data_to_sqlite_db_process(str(folder))
    assert capture.convert_screenshots_dir_into_video_process(str(folder)) == str(folder)
    assert calls == [str(folder)]
    assert folder.exists()
    video_folder = Path(capture.config.record_videos_dir_ud)
    video_folder.mkdir(parents=True, exist_ok=True)
    (video_folder / f"{folder.name}-SCREENSHOTS-OCRED-NOTCOMPRESS.mp4").write_bytes(b"x" * 2048)
    (video_folder / f"{folder.name}-SCREENSHOTS-OCRED.mp4").write_bytes(b"x")
    capture.clean_cache_screenshots_dir_process()
    assert folder.exists()  # Failed/intermediate output cannot authorize deleting old images.


def test_video_holds_frames_until_next_capture_and_releases_failed_encoder(capture, workspace, monkeypatch):
    from PIL import Image

    folder = cached_capture(workspace)
    metadata = []
    for second, color in [(0, "red"), (3, "blue")]:
        path = folder / f"2024-01-01_12-00-0{second}.png"
        Image.new("RGB", (32, 32), color=color).save(path)
        metadata.append(dict(img_file_name=str(path), vid_file_name="2024-01-01_12-00-00.mp4"))
    (folder / "tmp_db_json_all_files.json").write_text(json.dumps({"data": metadata}), encoding="utf-8")
    monkeypatch.setattr(capture, "MINIMUM_NUMBER_OF_IMAGES_REQUIRED_FOR_A_VIDEO", 2)

    class Writer:
        opened = True
        released = False
        frames = []

        def isOpened(self):
            return self.opened

        def write(self, frame):
            self.frames.append(tuple(frame[0, 0]))

        def release(self):
            self.released = True

    writer = Writer()
    monkeypatch.setattr(capture.cv2, "VideoWriter", lambda *args: writer)
    output, discard = capture.make_screenshots_into_video_via_dir_path(str(folder))
    assert output and not discard
    assert writer.frames == [(0, 0, 255)] * 3 + [(255, 0, 0)] * 2
    assert writer.released
    writer.opened = False
    writer.released = False
    assert capture.make_screenshots_into_video_via_dir_path(str(folder)) == (None, False)
    assert writer.released
