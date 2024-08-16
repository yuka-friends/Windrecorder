import datetime
import os

import pandas as pd
import streamlit as st
from openai import OpenAI

from windrecorder import file_utils, utils
from windrecorder.config import config
from windrecorder.const import (
    LLM_FAIL_COPY,
    LLM_SYSTEM_PROMPT_DEFAULT,
    LLM_SYSTEM_PROMPT_EXTRACT_DAY_TAGS,
    LLM_TEMPERATURE_EXTRACT_DAY_TAGS,
)
from windrecorder.logger import get_logger
from windrecorder.record_wintitle import get_wintitle_stat_in_day

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
        user_content=utils.convert_df_to_csv_str(day_activit_df),
        system_prompt=LLM_SYSTEM_PROMPT_EXTRACT_DAY_TAGS,
        temperature=LLM_TEMPERATURE_EXTRACT_DAY_TAGS,
    )
    if success:
        tags_list = tags_plain_text.split(",")
        return True, tags_list, tags_plain_text
    else:
        return False, [], tags_plain_text


def get_cache_data_by_date(date_in: datetime.date):
    cache_path = os.path.join(config.ai_extract_tag_result_dir_ud, str(date_in.year) + ".json")
    if os.path.exists(cache_path):
        cache_data = file_utils.read_json_as_dict_from_path(cache_path)
    else:
        cache_data = {}
    return cache_data


def get_day_tags(date_in: datetime.date):
    dt_str = utils.datetime_to_dateDayStr(date_in)
    if "day_tags_data" not in st.session_state:
        st.session_state["day_tags_data"] = get_cache_data_by_date(date_in)

    if dt_str in st.session_state["day_tags_data"].keys():
        return True, st.session_state["day_tags_data"][dt_str]
    return False, []


def generate_and_save_day_tags(date_in: datetime.date):
    dt_str = utils.datetime_to_dateDayStr(date_in)
    cache_path = os.path.join(config.ai_extract_tag_result_dir_ud, str(date_in.year) + ".json")
    cache_data = get_cache_data_by_date(date_in)
    success, day_tags_lst, plain_text = generate_day_tags_lst(date_in)
    if success:
        cache_data[dt_str] = day_tags_lst[: config.ai_extract_max_tag_num]
        file_utils.save_dict_as_json_to_path(cache_data, cache_path)
        return True, day_tags_lst, plain_text
    else:
        if "no_wintitle_data" in plain_text:
            cache_data[dt_str] = []
            file_utils.save_dict_as_json_to_path(cache_data, cache_path)
        return False, [], plain_text


def component_day_tags(date_in: datetime.date):
    # 渲染每日标签
    def _render_day_tags(tags_lst):
        html_tags_lst = []
        for tag in tags_lst:
            html_tags_lst.append(f"<span class='tag'>{tag}</span>")
        html_tags = "".join(html_tags_lst)
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


def cache_day_tags_in_idle_routine():
    # 缓存最近的 N 天的标签
    from windrecorder.db_manager import db_manager

    dt = datetime.date.today() - datetime.timedelta(days=1)
    earlist_dt = utils.seconds_to_datetime(db_manager.db_first_earliest_record_time())

    batch_count = config.ai_extract_tag_in_idle_batch_size
    day_trackback = 0
    year_process_now = 2999
    year_process_last_time = 1970
    cache_data = {}
    for i in range(600):
        date_in = dt - datetime.timedelta(days=day_trackback)

        if date_in < earlist_dt.date():
            logger.info(f"ai tags caching: reached to earlist datetime {earlist_dt}")
            break

        year_process_now = date_in.year
        if year_process_now != year_process_last_time:
            print(f"get year cache data {year_process_now}")
            year_process_last_time = year_process_now
            cache_data = get_cache_data_by_date(date_in)

        if utils.datetime_to_dateDayStr(date_in) in cache_data.keys():
            day_trackback += 1
            continue

        print(f"generate day {date_in}")
        generate_and_save_day_tags(date_in)
        day_trackback += 1
        batch_count -= 1
        if batch_count < 0:
            break

    for day_back in range(config.ai_extract_tag_in_idle_batch_size):
        date_in = datetime.date.today() - datetime.timedelta(days=day_back)
