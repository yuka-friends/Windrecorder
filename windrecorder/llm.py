import calendar
import datetime
import os

import pandas as pd
import streamlit as st
from openai import OpenAI

from windrecorder import file_utils, utils
from windrecorder.config import config
from windrecorder.const import (
    EXTRACT_DAY_TAGS_RETRY_TIMES,
    LLM_FAIL_COPY,
    LLM_SYSTEM_PROMPT_DAY_POEM,
    LLM_SYSTEM_PROMPT_DEFAULT,
    LLM_SYSTEM_PROMPT_EXTRACT_DAY_TAGS,
    LLM_TEMPERATURE_DAY_POEM,
    LLM_TEMPERATURE_EXTRACT_DAY_TAGS,
)
from windrecorder.logger import get_logger
from windrecorder.record_wintitle import get_wintitle_stat_in_day
from windrecorder.utils import get_text as _t

logger = get_logger(__name__)


def request_llm_one_shot(
    user_content,
    system_prompt=LLM_SYSTEM_PROMPT_DEFAULT,
    temperature=0.7,
    api_key=config.open_ai_api_key,
    base_url=config.open_ai_base_url,
    model=config.open_ai_modelname,
):
    try:
        client = OpenAI(
            api_key=api_key,
            base_url=base_url,
        )
        msg = [
            {
                "role": "system",
                "content": system_prompt,
            },
            {"role": "user", "content": user_content},
        ]
        logger.info(msg)
        completion = client.chat.completions.create(
            model=model,
            messages=msg,
            temperature=temperature,
        )
    except Exception as e:
        logger.error(e)
        return False, LLM_FAIL_COPY

    logger.info(completion.choices[0].message.content)
    return True, completion.choices[0].message.content


def remove_sensitive_exclude_words(content: str):
    for word in config.ai_extract_tag_filter_words:
        content = content.replace(word, "")
    return content


def generate_day_tags_lst(date_in: datetime.date):
    # get day wintitle
    dt = datetime.datetime.combine(
        date_in, datetime.time(hour=round(config.day_begin_minutes / 60), minute=config.day_begin_minutes % 60)
    )
    try:
        df_day_activity_optimize_display, _ = get_wintitle_stat_in_day(dt, optimize_for_display=True)
    except KeyError:
        return False, [], "no_wintitle_data"

    # restrict range
    day_activit_df = pd.DataFrame(columns=["content_page_name", "screen_time"])
    for index, row in df_day_activity_optimize_display.iterrows():
        if index > config.ai_extract_tag_wintitle_limit:
            break
        row_insert = {"content_page_name": row["Page"], "screen_time": row["Screen Time"]}
        day_activit_df.loc[len(day_activit_df)] = row_insert

    # generate tags
    success, tags_plain_text = request_llm_one_shot(
        user_content=remove_sensitive_exclude_words(utils.convert_df_to_csv_str(day_activit_df)),
        system_prompt=LLM_SYSTEM_PROMPT_EXTRACT_DAY_TAGS,
        temperature=LLM_TEMPERATURE_EXTRACT_DAY_TAGS,
    )
    if success:
        # praser
        tags_plain_text = tags_plain_text.replace("\n", "")
        tags_plain_text = tags_plain_text.replace("\r", "")
        tags_list = tags_plain_text.split(",")
        return True, tags_list, tags_plain_text
    else:
        return False, [], tags_plain_text


def get_cache_data_by_date(date_in: datetime.date, cache_dir=config.ai_extract_tag_result_dir_ud):
    cache_path = os.path.join(cache_dir, str(date_in.year) + ".json")
    if os.path.exists(cache_path):
        cache_data = file_utils.read_json_as_dict_from_path(cache_path)
        if cache_data is None:
            cache_data = {}
    else:
        cache_data = {}
    return cache_data


def get_day_tags(date_in: datetime.date):
    dt_str = utils.datetime_to_dateDayStr(date_in)
    if "day_tags_data" not in st.session_state:
        st.session_state["day_tags_data"] = get_cache_data_by_date(date_in, cache_dir=config.ai_extract_tag_result_dir_ud)

    if dt_str in st.session_state["day_tags_data"].keys():
        return True, st.session_state["day_tags_data"][dt_str]
    return False, []


def generate_and_save_day_tags(date_in: datetime.date):
    dt_str = utils.datetime_to_dateDayStr(date_in)
    cache_path = os.path.join(config.ai_extract_tag_result_dir_ud, str(date_in.year) + ".json")
    cache_data = get_cache_data_by_date(date_in, cache_dir=config.ai_extract_tag_result_dir_ud)
    success, day_tags_lst, plain_text = generate_day_tags_lst(date_in)
    if success:
        cache_data[dt_str] = day_tags_lst[: config.ai_extract_max_tag_num]
        file_utils.save_dict_as_json_to_path(cache_data, cache_path)
        if config.enable_ai_day_poem:
            success, poem, plain_text = generate_and_save_day_poem(date_in)
        return True, day_tags_lst, plain_text
    else:
        if "no_wintitle_data" in plain_text:
            cache_data[dt_str] = []
        else:
            # add retry mark
            try:
                if dt_str in cache_data.keys():
                    if len(cache_data[dt_str]) > 0:
                        if "retry_times" in cache_data[dt_str][0]:
                            time_count = int(cache_data[dt_str][0].split(":")[1])
                            time_count += 1
                            cache_data[dt_str] = [f"retry_times:{time_count}"]
                else:
                    cache_data[dt_str] = ["retry_times:1"]
                file_utils.save_dict_as_json_to_path(cache_data, cache_path)
            except Exception as e:
                logger.warning(f"caching retry fail: {e}")
        return False, [], plain_text


def component_day_tags(date_in: datetime.date):
    # 渲染每日标签
    def _render_day_tags(tags_lst):
        html_tags_lst = []
        for tag in tags_lst:
            html_tags_lst.append(f"<span class='tag'>{tag}</span>")
        html_tags = "".join(map(str, html_tags_lst))
        html_full = (
            """
    <style>
.tags-container {
width: 100%;
text-align: left;
margin-bottom: 16px;

}

.tag {
display: inline-block;
padding: 6px 12px;
margin: 4px 2px;
background-color: #F5E9E1;
border-radius: 30px;
font-size: 14px;
}
    </style>

<div class="tags-container">
"""
            + html_tags
            + """
</div>
    """
        )
        st.markdown(html_full, unsafe_allow_html=True)

    day_tags_cache_exist, day_tags_lst = get_day_tags(date_in)
    if day_tags_cache_exist:
        component_day_poem(date_in)
        _render_day_tags(day_tags_lst)
    else:
        if st.button(label="✨ Summary Tags"):
            with st.spinner("Generating tags... \nDepending on the LLM service, it may take 5~20 seconds."):
                success, day_tags_lst, plain_text = generate_and_save_day_tags(date_in)
                if success:
                    del st.session_state["day_tags_data"]
                    st.rerun()
                else:
                    st.warning(f"Failed to generate tags: {plain_text}", icon="😥")


def cache_day_tags_in_idle_routine(batch_count=config.ai_extract_tag_in_idle_batch_size):
    # 缓存最近的 N 天的标签
    from windrecorder.db_manager import db_manager

    dt = datetime.date.today() - datetime.timedelta(days=1)
    earlist_dt = utils.seconds_to_datetime(db_manager.db_first_earliest_record_time())

    day_trackback = 0
    year_process_now = 2999
    year_process_last_time = 1970
    cache_data_tags = {}
    cache_data_poem = {}
    for i in range(600):
        date_in = dt - datetime.timedelta(days=day_trackback)
        condition_generate_tags = False
        condition_generate_poem = False

        if date_in < earlist_dt.date():
            logger.info(f"ai tags caching: reached to earlist datetime {earlist_dt}")
            break

        year_process_now = date_in.year
        if year_process_now != year_process_last_time:
            logger.info(f"get year cache data {year_process_now}")
            year_process_last_time = year_process_now
            cache_data_tags = get_cache_data_by_date(date_in, cache_dir=config.ai_extract_tag_result_dir_ud)
            cache_data_poem = get_cache_data_by_date(date_in, cache_dir=config.ai_day_poem_result_dir_ud)

        dt_str = utils.datetime_to_dateDayStr(date_in)
        if dt_str in cache_data_tags.keys():
            if len(cache_data_tags[dt_str]) > 0:
                if "retry_times" in cache_data_tags[dt_str][0]:
                    time_count = int(cache_data_tags[dt_str][0].split(":")[1])
                    if time_count > EXTRACT_DAY_TAGS_RETRY_TIMES:
                        day_trackback += 1
                        continue
                    else:
                        condition_generate_tags = True
                        condition_generate_poem = True
                else:
                    if dt_str in cache_data_poem.keys() or not config.enable_ai_day_poem:
                        day_trackback += 1
                        continue
                    else:
                        condition_generate_poem = True
        else:
            condition_generate_tags = True
            condition_generate_poem = True

        print(f"generate day {date_in}")
        if condition_generate_tags:
            print("   tag...")
            generate_and_save_day_tags(date_in)
        if condition_generate_poem:
            print("   poem...")
            generate_and_save_day_poem(date_in)
        day_trackback += 1
        batch_count -= 1
        if batch_count < 0:
            break


def generate_day_poem_by_tag_lst(date_in: datetime.date, tags_lst: list):
    # generate tags
    success, poem_plain_text = request_llm_one_shot(
        user_content=",".join(tags_lst),
        system_prompt=LLM_SYSTEM_PROMPT_DAY_POEM.format(date_in=str(date_in)),
        temperature=LLM_TEMPERATURE_DAY_POEM,
    )
    if success:
        # praser
        poem_plain_text = poem_plain_text.replace("\n", "")
        poem_plain_text = poem_plain_text.replace("\r", "")
        if "." in poem_plain_text:
            poem = poem_plain_text.split(".")[0] + "."
        if "。" in poem_plain_text:
            poem = poem_plain_text.split("。")[0] + "。"
        return True, poem, poem_plain_text
    else:
        return False, "", poem_plain_text


def get_day_poem(date_in: datetime.date, force_read=False):
    dt_str = utils.datetime_to_dateDayStr(date_in)
    if "day_poem_data" not in st.session_state or force_read:
        st.session_state["day_poem_data"] = get_cache_data_by_date(date_in, cache_dir=config.ai_day_poem_result_dir_ud)

    if dt_str in st.session_state["day_poem_data"].keys():
        return True, st.session_state["day_poem_data"][dt_str]
    return False, ""


def get_month_poem(date_in: datetime.date, force_read=False):
    _, num_days = calendar.monthrange(date_in.year, date_in.month)
    data_lst = []

    for day in range(1, num_days + 1):
        current_date = datetime.date(date_in.year, date_in.month, day)
        day_poem_cache_exist, day_poem = get_day_poem(current_date, force_read=force_read)
        data_lst.append(
            {
                "date": current_date,
                "poem": day_poem,
            }
        )
    return data_lst


def generate_month_poem(date_in: datetime.date):
    progress_text = _t("stat_text_generating_ai_poem")
    progress_bar = st.progress(0.0, text=progress_text)

    if date_in.month == datetime.date.today().month and date_in.year == datetime.date.today().year:
        num_days = datetime.date.today().day
    else:
        _, num_days = calendar.monthrange(date_in.year, date_in.month)
        num_days += 1

    for day in range(1, num_days):
        current_date = datetime.date(date_in.year, date_in.month, day)
        day_poem_cache_exist, day_poem = get_day_poem(current_date)
        if not day_poem_cache_exist:
            generate_and_save_day_poem(current_date)
        progress_bar.progress(day / num_days, text=progress_text)
    progress_bar.empty()


def generate_and_save_day_poem(date_in: datetime.date):
    dt_str = utils.datetime_to_dateDayStr(date_in)
    cache_path_poem = os.path.join(config.ai_day_poem_result_dir_ud, str(date_in.year) + ".json")
    cache_data_tags = get_cache_data_by_date(date_in, cache_dir=config.ai_extract_tag_result_dir_ud)
    cache_data_poem = get_cache_data_by_date(date_in, cache_dir=config.ai_day_poem_result_dir_ud)

    if dt_str in cache_data_tags.keys():
        success, day_poem, plain_text = generate_day_poem_by_tag_lst(date_in, cache_data_tags[dt_str])

    if success:
        cache_data_poem[dt_str] = day_poem
        file_utils.save_dict_as_json_to_path(cache_data_poem, cache_path_poem)
        return True, day_poem, plain_text
    else:
        try:
            if dt_str in cache_data_poem.keys():
                if len(cache_data_poem[dt_str]) > 0:
                    if "retry_times" in cache_data_poem[dt_str]:
                        time_count = int(cache_data_poem[dt_str].split(":")[1])
                        time_count += 1
                        cache_data_poem[dt_str] = f"retry_times:{time_count}"
            else:
                cache_data_poem[dt_str] = "retry_times:1"
            file_utils.save_dict_as_json_to_path(cache_data_poem, cache_path_poem)
        except Exception as e:
            logger.warning(f"caching retry fail: {e}")
        return False, "", plain_text


def component_day_poem(date_in: datetime.date):
    day_poem_cache_exist, day_poem = get_day_poem(date_in)
    if day_poem_cache_exist:
        st.caption(day_poem)


def component_month_poem(month_dt: datetime.datetime):
    # 如果切换了时间或第一次加载，进行更新
    update_condition = False

    if "poem_month_dt_last_time" not in st.session_state:  # diff 当前显示表的日期，用于和控件用户输入对比判断是否更新
        st.session_state.poem_month_dt_last_time = month_dt
        update_condition = True

    if utils.set_full_datetime_to_YYYY_MM(st.session_state.poem_month_dt_last_time) != utils.set_full_datetime_to_YYYY_MM(
        month_dt
    ):
        update_condition = True
        st.session_state.poem_month_dt_last_time = month_dt

    if st.button(_t("stat_btn_generate_update_ai_poem")):
        generate_month_poem(datetime.date(month_dt.year, month_dt.month, 1))
        update_condition = True

    if update_condition:
        st.session_state.poem_month_df = pd.DataFrame(
            get_month_poem(datetime.date(month_dt.year, month_dt.month, 1), force_read=True)
        )

    st.dataframe(
        st.session_state.poem_month_df,
        use_container_width=True,
        hide_index=True,
        column_config={
            "date": st.column_config.DateColumn(format="YYYY-MM-DD", width="small"),
            "poem": st.column_config.TextColumn(width="large"),
        },
        height=500,
    )
