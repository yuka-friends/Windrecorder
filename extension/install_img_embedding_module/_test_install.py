# Set workspace to Windrecorder dir
import os
import sys

current_dir = os.path.dirname(os.path.abspath(__file__))
parent_parent_dir = os.path.dirname(os.path.dirname(current_dir))
sys.path.append(parent_parent_dir)
os.chdir("..")
os.chdir("..")

from windrecorder.config import config  # noqa: E402


def set_config_module_install(state: bool):
    config.set_and_save_config("img_embed_module_install", state)


# 检查 uform 是否被安装
try:
    from uform import Modality, get_model  # noqa: F401

    print("   uform 已成功安装！")
    print("   uform has been successfully installed!")

    print()
    print("   检查是否已下载嵌入模型，若有将跳过。")
    print("   Checking if the embedded model has been downloaded, if so it will be skipped.")
    try:
        from windrecorder import img_embed_manager

        img_embed_manager.get_model_and_processor()
        set_config_module_install(True)
        config.set_and_save_config("enable_img_embed_search", True)
        config.set_and_save_config("enable_synonyms_recommend", True)

    except Exception as e:
        print(e)
        print("   uform 模型似乎下载/获取失败，请检查网络、添加代理或进行重试。")
        print("   uform model seems to have failed to download, please check the network, add a proxy, or try again.")
        set_config_module_install(False)

except ModuleNotFoundError:
    print("   uform 未成功安装，若重试后仍然安装失败，请复制以上报错信息前往 GitHub issue 进行反馈。")
    print(
        "   uform was not successfully installed. If the installation still fails after retrying, please copy the above error message and send it to GitHub issue for feedback."
    )
    set_config_module_install(False)
