"""No recording/model downloads: exercise native imports and bundled OCR assets."""

import importlib
from pathlib import Path

import pytest


@pytest.mark.parametrize(
    "module",
    [
        "cv2",
        "numpy",
        "pandas",
        "onnxruntime",
        "faiss",
        "pyclipper",
        "shapely",
        "win32api",
        "pythoncom",
        "tkinter",
        "uiautomation",
        "streamlit",
        "windrecorder.record",
        "windrecorder.ocr_manager",
    ],
)
def test_runtime_import(module):
    importlib.import_module(module)


def test_faiss_roundtrip_retains_explicit_sqlite_ids(tmp_path):
    import faiss
    import numpy as np

    index = faiss.IndexIDMap(faiss.IndexFlatL2(2))
    index.add_with_ids(np.array([[1, 0], [0, 1]], dtype="float32"), np.array([7, 42], dtype="int64"))
    path = str(tmp_path / "legacy.index")
    faiss.write_index(index, path)
    loaded = faiss.read_index(path)
    _, ids = loaded.search(np.array([[0, 1]], dtype="float32"), 1)
    assert ids.tolist() == [[42]]


def test_index_written_by_legacy_faiss_174_is_readable():
    import faiss
    import numpy as np

    fixture = Path(__file__).parent / "fixtures/faiss-1.7.4.index"
    index = faiss.read_index(str(fixture))
    assert faiss.vector_to_array(index.id_map).tolist() == [7, 42]
    _, ids = index.search(np.array([[0, 1]], dtype="float32"), 1)
    assert ids.tolist() == [[42]]


def test_bundled_ocr_models_run_on_reference_image():
    from PIL import Image

    from ocr_lib.chineseocr_lite_onnx.model import OcrHandle

    asset = Path(__file__).resolve().parents[1] / "__assets__/OCR_test_1080_en-US.png"
    with Image.open(asset) as image:
        results = OcrHandle().text_predict(image, 768)
    assert len(results) > 0
    assert all(isinstance(row[1], str) and row[1].strip() for row in results)


@pytest.mark.parametrize("module", ["rapidocr_onnxruntime", "wechat_ocr", "uform.onnx_encoders", "uform.numpy_processors"])
def test_optional_extension_imports(module):
    pytest.importorskip(module.split(".")[0])
    importlib.import_module(module)


def test_streamlit_password_gate_renders_without_desktop_capture(monkeypatch):
    import hashlib

    from streamlit.testing.v1 import AppTest

    from windrecorder.config import config

    monkeypatch.setattr(config, "webui_access_password_md5", hashlib.md5(b"test-only").hexdigest())
    # Cold scientific-library/font imports take longer under coverage on Windows CI.
    app = AppTest.from_file(str(Path(__file__).resolve().parents[1] / "webui.py"), default_timeout=90).run()
    assert not app.exception
    assert len(app.text_input) == 1
    assert "Password" in app.text_input[0].label
