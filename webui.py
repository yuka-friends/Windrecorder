import streamlit as st
import dbManager
import os
import maintainManager
import time
import json

update_button_key = "update_button"
reset_button_key = "setting_reset"


# python -m streamlit run webui.py
with open('config.json') as f:
    config = json.load(f)
print("config.json:")
print(config)

db_path = config["db_path"]
db_filename = config["db_filename"]
db_filepath = db_path +"/"+ db_filename
video_path = config["record_videos_dir"]

st.set_page_config(
     page_title="Wide screen",
     page_icon="🦝",
     layout="wide"
)

dbManager.db_main_initialize()


# 将数据库的视频名加上OCRED标志，使之能正常读取到
def combine_vid_name_withOCR(video_name):
    vidname = os.path.splitext(video_name)[0] + "-OCRED" + os.path.splitext(video_name)[1]
    return vidname


# 定位视频时间码，展示视频
def show_n_locate_video_timestamp(df,num):
    # todo 获取有多少行结果 对num进行合法性判断
    # todo 判断视频需要存在才能播放
    videofile_path = os.path.join(video_path,combine_vid_name_withOCR(df.iloc[num]['videofile_name']))
    print("videofile_path: "+videofile_path)
    vid_timestamp = calc_vid_inside_time(df,num)
    print("vid_timestamp: "+str(vid_timestamp))

    video_file = open(videofile_path, 'rb')
    video_bytes = video_file.read()
    st.video(video_bytes, start_time=vid_timestamp)


# 计算视频对应时间戳
def calc_vid_inside_time(df,num):
    fulltime = df.iloc[num]['videofile_time']
    vidfilename = os.path.splitext(df.iloc[num]['videofile_name'])[0]
    vid_timestamp = fulltime - dbManager.date_to_seconds(vidfilename)
    print("fulltime:"+str(fulltime)+"\n vidfilename:"+str(vidfilename)+"\n vid_timestamp:"+str(vid_timestamp))
    return vid_timestamp


# 选择播放视频的行数
def choose_search_result_num(df):
    # shape是一个元组,索引0对应行数,索引1对应列数。
    total_raw = df.shape[0]
    print("total_raw:" + str(total_raw))
    select_num = st.slider('rewind video', 0, total_raw - 1,0)
    submit_btn = st.button('Locate Video')
    if submit_btn:
        show_n_locate_video_timestamp(df,select_num)


# footer状态信息
def web_footer_state():
    latest_record_time_int = dbManager.db_latest_record_time(db_filepath)
    latest_record_time_str = dbManager.seconds_to_date(latest_record_time_int)

    latest_db_records = dbManager.db_num_records(db_filepath)

    videos_file_size = round(dbManager.file_how_big_videos_dir(video_path)/(1024*1024*1024),3)

    # webUI draw
    st.divider()
    st.markdown(f'Database latest record time: **{latest_record_time_str}**, Database records: **{latest_db_records}**, Video Files on disk: **{videos_file_size} GB**')



# 主界面
st.title('🦝 Windrecorder Dashboard')




tab1, tab2 = st.tabs(["Search", "Setting"])

with tab1:
    st.header("Search")
    
    # todo 指定搜索时间范围
    search_content = st.text_input('Search OCR Keyword', 'Hello')
    search_cb = st.checkbox('Searching')

    # if st.button('Search'):
    if search_cb:

        # 获取数据
        df = dbManager.db_search_data(db_filepath,search_content)
        if len(df) == 0:
            st.write('Nothing with ' + search_content)
        else:
            st.write('Result about '+search_content)
            # 打表
            st.dataframe(df)
            # 选择视频
            choose_search_result_num(df)


        # os.startfile(first_videofile_path)
    # else:
        # st.write('Searching something.')
    
    web_footer_state()



def update_database_clicked():
    st.session_state.update_button_disabled = True


with tab2:
    st.header("Setting")

    if st.button('Update Database', type="primary", key='update_button_key', disabled=st.session_state.get("update_button_disabled", False), on_click=update_database_clicked):
        try:
            with st.spinner("Updating Database... You can see process on terminal. Estimated time:"):
                timeCost=time.time()
                # todo 给出预估剩余时间
                maintainManager.maintain_manager_main()

                timeCost=time.time() - timeCost
        except Exception as ex:
            st.write(f'Something went wrong!: {ex}')
        else:
            st.write(f'Database Updated! Time cost: {timeCost}')
        finally:
            st.session_state.update_button_disabled = False
            st.button('Reset', key=reset_button_key)
