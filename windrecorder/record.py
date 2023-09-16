import subprocess
import os
import shutil

from pyshortcuts import make_shortcut


# 检测是否正在录屏
def is_recording():
    try:
        with open("LOCK_FILE_RECORD.MD", encoding='utf-8') as f:
            check_pid = int(f.read())

        check_result = subprocess.run(['tasklist'], stdout=subprocess.PIPE, text=True)
        check_output = check_result.stdout
        check_result = subprocess.run(['findstr', str(check_pid)], input=check_output, stdout=subprocess.PIPE, text=True)
        check_output = check_result.stdout
        global state_is_recording
        if "python" in check_output:
            state_is_recording = True
            print(f"state_is_recording:{state_is_recording}")
            return True
        else:
            state_is_recording = False
            print(f"state_is_recording:{state_is_recording}")
            return False
    except:
        print("录屏服务文件锁不存在")

    # 试图使用据说可以自动更新的组件来强制刷新状态
    # (https://towardsdatascience.com/creating-dynamic-dashboards-with-streamlit-747b98a68ab5)
    # placeholder.text(
    #     f"state_is_recording:{state_is_recording}")


# 用另外的线程虽然能持续检测到服务有没有运行，但是byd streamlit就是没法自动更新，state只能在主线程访问；
# 用了这个（https://github.com/streamlit/streamlit/issues/1326）讨论中的临时措施
# 虽然可以自动更新了，但还是无法动态更新页面
# 目的：让它可以自动检测服务是否在运行，并且在页面中更新显示状态
# timer_repeat_check_recording = RepeatingTimer(5, repeat_check_recording)
# add_script_run_ctx(timer_repeat_check_recording)
# timer_repeat_check_recording.start()


# 检查开机启动项中是否已存在某快捷方式
def is_file_already_in_startup(filename):
    startup_folder = os.path.join(os.getenv('APPDATA'), 'Microsoft', 'Windows', 'Start Menu', 'Programs', 'Startup')
    shortcut_path = os.path.join(startup_folder, filename)
    if os.path.exists(shortcut_path):
        return True
    else:
        return False


# 将录屏服务设置为开机启动
def create_startup_shortcut(is_create = True):
    startup_folder = os.path.join(os.getenv('APPDATA'), 'Microsoft', 'Windows', 'Start Menu', 'Programs', 'Startup')
    shortcut_path = os.path.join(startup_folder, 'start_record.bat.lnk')

    if is_create == True:
        # 创建快捷方式
        if not os.path.exists(shortcut_path):
            current_dir = os.getcwd()
            bat_path = os.path.join(current_dir, 'start_record.bat')
            make_shortcut(bat_path,folder=startup_folder)
            print('快捷方式已创建并添加到开机启动项')

    else:
        # 移除快捷方式
        if os.path.exists(shortcut_path):
            print('快捷方式已存在')
            os.remove(shortcut_path)
            print('删除快捷方式')



