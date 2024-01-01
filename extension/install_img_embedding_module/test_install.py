# Set workspace to Windrecorder dir
import sys
import os
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_parent_dir = os.path.dirname(os.path.dirname(current_dir))
sys.path.append(parent_parent_dir)
os.chdir("..")
os.chdir("..")

from windrecorder.config import config
def set_config_module_install(state: bool):
    config.set_and_save_config("img_embed_module_install", state)

# 检查是否能启用 cuda
try:
    import torch
    if torch.cuda.is_available():
        print('   恭喜！你的设备支持 CUDA 加速。')
        print('   Congratulations! Your device supports CUDA acceleration.')
    else:
        print('   你的设备似乎不支持 CUDA 加速、或安装了 CPU 计算的 pytorch 环境。在索引时可能会存在性能问题。')
        print('   Your device does not seem to support CUDA acceleration, or the pytorch environment for CPU computing is installed. There may be performance issues during indexing.')

except ModuleNotFoundError:
    print('   Pytorch 未能成功安装，若重试后仍然安装失败，请复制以上报错信息前往 GitHub issue 进行反馈。')
    print('   Pytorch failed to install successfully. If the installation still fails after trying again, please copy the above error message and send it to GitHub issue for feedback.')
    set_config_module_install(False)

print()

# 检查 uform 是否被安装
try:
    import uform
    print('   uform 已成功安装！')
    print('   uform has been successfully installed!')
    
    try:
        from windrecorder import img_embed_manager
        print()
        print('   检查是否已下载嵌入模型，若有将跳过。')
        print('   Checking if the embedded model has been downloaded, if so it will be skipped.')

        img_embed_manager.get_model('cpu')
        set_config_module_install(True)
        config.set_and_save_config("enable_img_embed_search", True)
    except Exception as e:
        print(e)
        print('   uform 模型似乎下载失败，请检查网络、添加代理或进行重试。')
        print('   uform model seems to have failed to download, please check the network, add a proxy, or try again.')
        set_config_module_install(False)

except ModuleNotFoundError:
    print('   uform 未成功安装，若重试后仍然安装失败，请复制以上报错信息前往 GitHub issue 进行反馈。')
    print('   uform was not successfully installed. If the installation still fails after retrying, please copy the above error message and send it to GitHub issue for feedback.')
    set_config_module_install(False)
