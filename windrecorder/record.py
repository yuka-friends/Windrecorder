import subprocess

def is_recording():
    try:
        with open("lock_file_record", encoding='utf-8') as f:
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
