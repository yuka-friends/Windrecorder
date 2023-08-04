import streamlit as st
import dbManager
import os
import maintainManager
import time
import json
import utils
import datetime
from collections import OrderedDict

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
lang = config["lang"]

with open("languages.json", encoding='utf-8') as f:
    d_lang = json.load(f)
lang_map = d_lang['lang_map']

# 获取配置中语言选项是第几位；使设置选择项能匹配
def get_language_index(lang,data):
  for i, l in enumerate(data):
    if l == lang:
      return i
  return 1

lang_index = get_language_index(lang,d_lang)



st.set_page_config(
     page_title="Windrecorder",
     page_icon="🦝",
     layout="wide"
)

dbManager.db_main_initialize()


# 将数据库的视频名加上-OCRED标志，使之能正常读取到
def combine_vid_name_withOCR(video_name):
    vidname = os.path.splitext(video_name)[0] + "-OCRED" + os.path.splitext(video_name)[1]
    return vidname


# 定位视频时间码，展示视频
def show_n_locate_video_timestamp(df,num):
    if is_df_result_exist:
        # todo 获取有多少行结果 对num进行合法性判断
        # todo 判断视频需要存在才能播放
        videofile_path = os.path.join(video_path,combine_vid_name_withOCR(df.iloc[num]['videofile_name']))
        print("videofile_path: "+videofile_path)
        vid_timestamp = calc_vid_inside_time(df,num)
        print("vid_timestamp: "+str(vid_timestamp))
    
        st.session_state.vid_vid_timestamp = 0
        st.session_state.vid_vid_timestamp = vid_timestamp
        # st.session_state.vid_vid_timestamp
        # 判断视频文件是否存在
        if os.path.isfile(videofile_path):
            video_file = open(videofile_path, 'rb')
            video_bytes = video_file.read()
            st.video(video_bytes, start_time=st.session_state.vid_vid_timestamp)
        else:
            st.markdown(f"Video File **{videofile_path}** not on disk.")


# 计算视频对应时间戳
def calc_vid_inside_time(df,num):
    fulltime = df.iloc[num]['videofile_time']
    vidfilename = os.path.splitext(df.iloc[num]['videofile_name'])[0]
    vid_timestamp = fulltime - dbManager.date_to_seconds(vidfilename)
    print("fulltime:"+str(fulltime)+"\n vidfilename:"+str(vidfilename)+"\n vid_timestamp:"+str(vid_timestamp))
    return vid_timestamp


# 选择播放视频的行数 的滑杆组件
def choose_search_result_num(df,is_df_result_exist):
    if not is_df_result_exist == 0:
        # shape是一个元组,索引0对应行数,索引1对应列数。
        total_raw = df.shape[0]
        print("total_raw:" + str(total_raw))
        # 使用滑杆选择视频
        select_num = st.slider(d_lang[lang]["def_search_slider"], 0, total_raw - 1,0)
        return select_num
    else:
        return 0


# 数据库的前置索引状态提示
def web_db_state_info_before():
    count, nocred_count = web_db_check_folder_marked_file(video_path)
    if nocred_count>0:
        # st.warning(f' {nocred_count} Video Files need to index. ({count} files total on disk.)',icon='🧭')
        st.warning(d_lang[lang]["tab_setting_db_state1"].format(nocred_count=nocred_count,count=count),icon='🧭')
        return True
    else:
        # st.success(f'No Video Files need to index. ({count} files total on disk.)',icon='✅')
        st.success(d_lang[lang]["tab_setting_db_state2"].format(nocred_count=nocred_count,count=count),icon='✅')
        return False


# 检查 videos 文件夹内有无以"-OCRED"结尾的视频
def web_db_check_folder_marked_file(folder_path):
    count = 0   
    nocred_count = 0   
    for filename in os.listdir(folder_path):
        count += 1
        if not filename.split('.')[0].endswith("-OCRED"):
            nocred_count += 1       
    return count, nocred_count


# 更改语言
def config_set_lang(lang_name):
    INVERTED_LANG_MAP = {v: k for k, v in lang_map.items()}
    lang_code = INVERTED_LANG_MAP.get(lang_name)
    
    if not lang_code:
        print(f"Invalid language name: {lang_name}")
        return

    with open('config.json') as f:
        config = json.load(f)

    config['lang'] = lang_code

    with open('config.json', 'w') as f:
        json.dump(config, f) 
    
    



# footer状态信息
def web_footer_state():
    latest_record_time_int = dbManager.db_latest_record_time(db_filepath)
    latest_record_time_str = dbManager.seconds_to_date(latest_record_time_int)

    latest_db_records = dbManager.db_num_records(db_filepath)

    videos_file_size = round(utils.get_dir_size(video_path)/(1024*1024*1024),3)

    # webUI draw
    st.divider()
    # st.markdown(f'Database latest record time: **{latest_record_time_str}**, Database records: **{latest_db_records}**, Video Files on disk: **{videos_file_size} GB**')
    st.markdown(d_lang[lang]["footer_info"].format(latest_record_time_str=latest_record_time_str,latest_db_records=latest_db_records,videos_file_size=videos_file_size))








# 主界面_________________________________________________________
st.markdown(d_lang[lang]["main_title"])



tab1, tab2, tab3 = st.tabs([d_lang[lang]["tab_name_search"], d_lang[lang]["tab_name_recording"], d_lang[lang]["tab_name_setting"]])

with tab1:

    
    col1,col2 = st.columns([1,2])
    with col1:
        st.markdown(d_lang[lang]["tab_search_title"])

        col1a,col2a = st.columns([3,2])
        with col1a:
            search_content = st.text_input(d_lang[lang]["tab_search_compname"], 'Hello')
        with col2a:
            # 时间搜索范围组件
            latest_record_time_int = dbManager.db_latest_record_time(db_filepath)
            search_date_range_in, search_date_range_out=st.date_input(
                d_lang[lang]["tab_search_daterange"],
                (datetime.datetime(2000, 1, 1) + datetime.timedelta(seconds=latest_record_time_int) - datetime.timedelta(seconds=86400), datetime.datetime.now()),
                format="YYYY-MM-DD"
                )

        # search_cb = st.checkbox('Searching',value=True)


        # if search_cb:

        # 获取数据
        df = dbManager.db_search_data(db_filepath,search_content,search_date_range_in,search_date_range_out)
        df = dbManager.db_refine_search_data(df)
        is_df_result_exist = len(df)

        # 滑杆选择
        result_choose_num = choose_search_result_num(df,is_df_result_exist)

        if len(df) == 0:
            st.write(d_lang[lang]["tab_search_word_no"].format(search_content=search_content))

        else:
            # st.write('Result about '+search_content)
            # 打表
            st.dataframe(
                df,
                column_config={
                    "is_videofile_exist": st.column_config.CheckboxColumn(
                    "is_videofile_exist",
                    help=d_lang[lang]["tab_search_table_help1"],
                    default=False,
                    ),

                    "ocr_text": st.column_config.TextColumn(
                    "ocr_text",
                    help=d_lang[lang]["tab_search_table_help2"],
                    width="large"
                    ),

                    "thumbnail": st.column_config.ImageColumn(
                    "thumbnail", 
                    help=d_lang[lang]["tab_search_table_help3"]
                    )

                },
                height = 700
            )

    with col2:
        # 选择视频
        show_n_locate_video_timestamp(df,result_choose_num)


    
    web_footer_state()



def update_database_clicked():
    st.session_state.update_button_disabled = True

with tab2:
    st.markdown(d_lang[lang]["tab_record_title"])

    col1c,col2c = st.columns([1,3])
    with col1c:
        st.write("WIP")
    
    with col2c:
        st.write("WIP")



with tab3:
    st.markdown(d_lang[lang]["tab_setting_title"])

    col1b,col2b = st.columns([1,3])
    with col1b:
        # 更新数据库
        st.markdown(d_lang[lang]["tab_setting_db_title"])
        need_to_update_db = web_db_state_info_before()
        if st.button(d_lang[lang]["tab_setting_db_btn"], type="primary", key='update_button_key', disabled=st.session_state.get("update_button_disabled", False), on_click=update_database_clicked):
            try:
                with st.spinner(d_lang[lang]["tab_setting_db_tip1"]):
                    timeCost=time.time()
                    # todo 给出预估剩余时间
                    maintainManager.maintain_manager_main()

                    timeCost=time.time() - timeCost
            except Exception as ex:
                st.write(d_lang[lang]["tab_setting_db_tip2"].format(ex=ex))
                # st.write(f'Something went wrong!: {ex}')
            else:
                st.write(d_lang[lang]["tab_setting_db_tip3"].format(timeCost=timeCost))
                # st.write(f'Database Updated! Time cost: {timeCost}s')
            finally:
                st.snow()
                st.session_state.update_button_disabled = False
                st.button(d_lang[lang]["tab_setting_db_btn_gotit"], key=reset_button_key)


        st.divider()

        # 自动化维护选项 WIP
        st.markdown(d_lang[lang]["tab_setting_maintain_title"])
        config_vid_store_day = st.number_input(d_lang[lang]["tab_setting_m_vid_store_time"],min_value=1,value=90)
        config_is_ocr_vc_enable = st.checkbox(d_lang[lang]["tab_setting_m_enable_vd"],value=False)
        

        st.divider()

        # 选择语言
        st.markdown(d_lang[lang]["tab_setting_ui_title"])

        config_search_num = st.number_input(d_lang[lang]["tab_setting_ui_result_num"],min_value=1,max_value=500,value=50)

        lang_choice = OrderedDict((k, ''+v) for k,v in lang_map.items())
        language_option = st.selectbox(
            'Interface Language / 更改显示语言',
            (list(lang_choice.values())),
            index=lang_index)
        config_set_lang(language_option)
        st.button('Update Language / 更改语言',type="secondary")
    


    with col2b:
        st.write("WIP")




