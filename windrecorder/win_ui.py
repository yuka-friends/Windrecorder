import ctypes


# 系统弹窗函数
def show_popup(message, title, popup_type):
    """
    调用 Windows 弹窗
    """
    MessageBox = ctypes.windll.user32.MessageBoxW  # 定义Windows API函数签名
    popup_type_preset = {
        "no_icon": 0x00,
        "error": 0x10,
        "question": 0x20,
        "warning": 0x30,
        "infomation": 0x40,
    }
    MessageBox(None, message, title, popup_type_preset[popup_type])
