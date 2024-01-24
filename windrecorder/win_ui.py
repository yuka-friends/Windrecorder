import ctypes

def show_popup(message: str, title: str, popup_type: str):
    """
    调用 Windows 弹窗

    :param message, 弹窗内文本信息
    :param title, 弹窗标题
    :param popup_type, 弹窗类型
    """
    MessageBox = ctypes.windll.user32.MessageBoxW  # 定义Windows API函数签名
    popup_type_preset = {
        "no_icon": 0x00,
        "error": 0x10,
        "question": 0x20,
        "warning": 0x30,
        "information": 0x40,
    }
    MessageBox(None, message, title, popup_type_preset[popup_type])