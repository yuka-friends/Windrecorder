# -*- coding: utf-8 -*-
import re

import streamlit as st
import pandas as pd
import datetime
import json
from windrecorder.config import config
from windrecorder.db_manager import db_manager
from windrecorder import llm, utils, file_utils
from windrecorder.ui import components

from windrecorder.utils import get_text as _t
from windrecorder.logger import get_logger

logger = get_logger(__name__)


def parse_natural_query(query: str) -> dict | None:
    """
    Uses LLM to parse the natural language query into structured search parameters.
    """
    if not config.open_ai_api_key or not config.open_ai_base_url:
        st.error(_t("error_openai_api_not_configured"))
        return None

    # Detect language (simple heuristic, could be improved)
    # This is basic, a library like langdetect might be better but adds dependency
    # is_likely_chinese = any('\u4e00' <= char <= '\u9fff' for char in query)
    language_instruction = "Respond in the same language as the User Query."
    prompt = f"""
    Analyze the following user query for searching their screen recordings. Extract the key information and return it as a JSON object.
    The JSON object should have the following keys:
    - "keywords": A list of essential keywords/phrases to search for. Be specific. If the query is very general (like "what did I do?", "show my activity"), leave this empty.
    - "exclude_keywords": A list of keywords/phrases to exclude.
    - "applications": A list of specific application names or window title fragments mentioned (e.g., "WeChat", "Chrome", "Word").
    - "time_description": The user's description of the time frame (e.g., "last week", "yesterday afternoon", "recently"). Keep it as the user described it.
    - "user_intent": Describe the user's goal. Use "summarize activities" for general queries like "what did I do?". Other examples: "find specific chat", "find document", "find last occurrence", "general search".
    - "occurrence": Specify if the user wants the "first", "last", or "any" occurrence of something. Default to "any".

    User Query: "{query}"

    Instructions:
    1.  **Prioritize specific entities mentioned.**
    2.  **Distinguish chat content keywords from application names or contact list entries.** If the user asks about a chat with "Person A", "Person A" is a keyword, and the application (e.g., "WeChat") might also be mentioned.
    3.  **Handle General Queries:** If the query is broad like "What did I do yesterday?", set `keywords` to [] and `user_intent` to "summarize activities".
    4.  **Detect First/Last:** If the query asks for the "first time" or "last time", set the `occurrence` field accordingly.
    5.  **Language:** {language_instruction}

    Return ONLY the JSON object. Example for 'Find my last WeChat chat with Bob about the project yesterday':
    {{
      "keywords": ["Bob", "project"],
      "exclude_keywords": [],
      "applications": ["WeChat"],
      "time_description": "yesterday",
      "user_intent": "find specific chat",
      "occurrence": "last"
    }}
    Example for 'What did I do this morning?':
    {{
      "keywords": [],
      "exclude_keywords": [],
      "applications": [],
      "time_description": "this morning",
      "user_intent": "summarize activities",
      "occurrence": "any"
    }}
    """
    try:
        success, response_text = llm.request_llm_one_shot(
            user_content=query,
            system_prompt=prompt,
            temperature=0.2,
            api_key=config.open_ai_api_key,
            base_url=config.open_ai_base_url,
            model=config.open_ai_modelname,
        )

        if success:
            try:
                response_text = response_text.strip().removeprefix("```json").removesuffix("```")
                parsed_data = json.loads(response_text)
                required_keys = ["keywords", "exclude_keywords", "applications", "time_description", "user_intent", "occurrence"] # Added occurrence
                if all(key in parsed_data for key in required_keys):
                    for key in ["keywords", "exclude_keywords", "applications"]:
                        if not isinstance(parsed_data.get(key), list):
                            parsed_data[key] = []
                    return parsed_data
                else:
                    logger.error(f"LLM response missing required keys: {response_text}")
                    st.error(_t("error_llm_parsing_failed_keys"))
                    return None
            except json.JSONDecodeError as e:
                logger.error(f"Failed to decode LLM JSON response: {e}\nResponse: {response_text}")
                st.error(_t("error_llm_parsing_failed_json"))
                return None
        else:
            logger.error(f"LLM request failed: {response_text}")
            st.error(_t("error_llm_request_failed").format(error=response_text))
            return None
    except Exception as e:
        logger.error(f"Error during LLM query parsing: {e}", exc_info=True)
        st.error(_t("error_unexpected_llm"))
        return None


def estimate_time_range(time_description: str) -> tuple[datetime.datetime, datetime.datetime]:
    """
    Uses LLM to estimate a start and end date based on the description.
    Returns (start_datetime, end_datetime).
    """
    if not time_description or time_description.lower() in ["any time", "all time", "don't know", ""]:
        # Default to a very wide range if no description or a vague one
        start_dt = utils.seconds_to_datetime(db_manager.db_first_earliest_record_time())
        end_dt = datetime.datetime.now()
        logger.info("No specific time description, using full range.")
        return start_dt, end_dt

    if not config.open_ai_api_key or not config.open_ai_base_url:
        st.error(_t("error_openai_api_not_configured"))
        # Fallback to a recent range
        end_dt = datetime.datetime.now()
        start_dt = end_dt - datetime.timedelta(days=30)
        return start_dt, end_dt

    today = datetime.date.today().isoformat()
    prompt = f"""
    Based on the user's time description and today's date ({today}), estimate a likely start date and end date for their search.
    Return the dates as a JSON object with keys "start_date" and "end_date" in "YYYY-MM-DD" format.

    Time Description: "{time_description}"

    Consider relative terms like "yesterday", "last week", "recently", "a few days ago", specific dates/times if mentioned.
    If the description is very vague (e.g., "recently"), estimate a reasonable range (e.g., the last 7-30 days).
    If a specific time is mentioned (e.g., "3 PM"), the date range might just be that single day.

    Return ONLY the JSON object. Example:
    {{
      "start_date": "2025-03-01",
      "end_date": "2025-04-01"
    }}
    """
    try:
        success, response_text = llm.request_llm_one_shot(
            user_content=time_description,
            system_prompt=prompt,
            temperature=0.1, # 对于日期，temperatur低一些即可
            api_key=config.open_ai_api_key,
            base_url=config.open_ai_base_url,
            model=config.open_ai_modelname,
        )

        if success:
            try:
                response_text = response_text.strip().removeprefix("```json").removesuffix("```")
                dates = json.loads(response_text)
                start_dt = datetime.datetime.fromisoformat(dates["start_date"])
                end_dt = datetime.datetime.fromisoformat(dates["end_date"])
                # 确保是完整的一天
                # 可以采用「一天之时」分隔每日的时间点
                end_dt = end_dt.replace(hour=23, minute=59, second=59)
                logger.info(f"LLM estimated time range: {start_dt} to {end_dt}")
                return start_dt, end_dt
            except (json.JSONDecodeError, KeyError, ValueError) as e:
                logger.error(f"Failed to parse LLM date response: {e}\nResponse: {response_text}")
                st.error(_t("error_llm_date_parsing_failed"))
                # Fallback
                end_dt = datetime.datetime.now()
                start_dt = end_dt - datetime.timedelta(days=7) # 无法正确分析日期则默认7天
                return start_dt, end_dt
        else:
            logger.error(f"LLM date estimation failed: {response_text}")
            st.error(_t("error_llm_date_estimation_failed"))
            # Fallback
            end_dt = datetime.datetime.now()
            start_dt = end_dt - datetime.timedelta(days=7)
            return start_dt, end_dt
    except Exception as e:
        logger.error(f"Error during LLM date estimation: {e}", exc_info=True)
        st.error(_t("error_unexpected_llm"))
        # Fallback
        end_dt = datetime.datetime.now()
        start_dt = end_dt - datetime.timedelta(days=7)
        return start_dt, end_dt


def summarize_results(ocr_snippets: list[str], user_intent: str, original_query: str) -> str | None:
    """
    Uses LLM to summarize the found OCR text based on user intent.
    """
    if not ocr_snippets:
        return _t("info_no_content_to_summarize")

    if not config.open_ai_api_key or not config.open_ai_base_url:
        st.error(_t("error_openai_api_not_configured"))
        return None

    # is_likely_chinese = any('\u4e00' <= char <= '\u9fff' for char in original_query)
    language_instruction = "Respond concisely in the same language as the User's Original Query."

    MAX_SUMMARY_CHARS = 10000
    context_text = "\n---\n".join(filter(None, ocr_snippets)) # 过滤none
    if len(context_text) > MAX_SUMMARY_CHARS:
        context_text = context_text[:MAX_SUMMARY_CHARS] + "..."
    elif not context_text.strip():
         return _t("info_no_text_to_summarize") # 处理为空的情况


    prompt = f"""
    Based on the following screen recording text snippets (which may contain OCR errors) and the user's original query and intent, provide a concise summary or answer.

    User's Original Query: "{original_query}"
    User's Intent: "{user_intent}"

    Screen Recording Text Snippets:
    ---
    {context_text}
    ---

    Instructions:
    1.  **Language:** {language_instruction}
    2.  **OCR Awareness:** Be aware that the snippets come from OCR and might contain errors or fragmented text. Do not treat names found in lists (like contact lists) as direct chat participants unless there's clear message content associated.
    3.  **Address Intent:**
        - If intent is "summarize activities": Provide a brief, high-level overview of the main applications used, topics discussed, or tasks performed based *only* on the provided snippets.
        - If intent is "find specific chat/document/info": Extract the relevant parts or confirm its presence/absence *in the snippets*. State clearly if the specific information is not found *in these snippets*.
        - If intent is "find first/last occurrence": Mention the content found that seems relevant to the first/last occurrence based on the snippets provided (the main app logic handles the sorting).
        - For "general search": Briefly describe the content of the snippets related to the query.
    4.  **Directness:** Address the user's original query as directly as possible using *only* the provided text.
    5.  **Conciseness:** Keep the response brief and to the point. Avoid making assumptions beyond the provided text.

    Provide only the summary/answer.
    """

    try:
        success, summary = llm.request_llm_one_shot(
            user_content=f"Original Query: {original_query}\nIntent: {user_intent}\nContext:\n{context_text}",
            system_prompt=prompt,
            temperature=0.5,
            api_key=config.open_ai_api_key,
            base_url=config.open_ai_base_url,
            model=config.open_ai_modelname,
        )
        if success:
            summary = summary.strip()
            # 清洗规则所在处
            return summary
        else:
            logger.error(f"LLM summarization failed: {summary}")
            st.error(_t("error_llm_summarization_failed"))
            return None
    except Exception as e:
        logger.error(f"Error during LLM summarization: {e}", exc_info=True)
        st.error(_t("error_unexpected_llm"))
        return None


# --- Main Page Rendering ---

def render_natural_search_page():
    st.title(f"🧐 {_t('natural_search_title')}")
    st.caption(_t("natural_search_caption"))

    if not config.open_ai_api_key or not config.open_ai_base_url:
        st.warning(_t("warn_openai_api_needed"), icon="🔑")

    query = st.text_input(_t("natural_search_input_label"), placeholder=_t("natural_search_placeholder"), key="natural_query_input")

    if st.button(_t("natural_search_button"), key="natural_search_exec", disabled=(not query or not config.open_ai_api_key)):

        with st.spinner(_t("natural_search_spinner_parsing")):
            parsed_params = parse_natural_query(query)

        if parsed_params:
            st.write("---")
            # with st.expander(_t("natural_search_parsed_details")): # debug用
            #     st.json(parsed_params)

            keywords_list = parsed_params.get("keywords", [])
            keywords_str = " ".join(keywords_list)
            exclude_keywords_str = " ".join(parsed_params.get("exclude_keywords", []))
            applications = parsed_params.get("applications", [])
            time_desc = parsed_params.get("time_description", "")
            user_intent = parsed_params.get("user_intent", "general search")
            occurrence = parsed_params.get("occurrence", "any")

            # --- Time Estimation ---
            with st.spinner(_t("natural_search_spinner_time")):
                start_date, end_date = estimate_time_range(time_desc)
                st.info(f"{_t('natural_search_time_range_info')} **{start_date.strftime('%Y-%m-%d')}** {_t('natural_search_time_range_to')} **{end_date.strftime('%Y-%m-%d')}**")

            # --- Database Search ---
            df_all = pd.DataFrame()
            row_count = 0
            search_keywords = keywords_str
            # 如果是一个summary不是 keyword 则搜索时间范围内的所有内容
            if user_intent == "summarize activities" and not keywords_list:
                search_keywords = "" # Search for empty string to get all records
                logger.info(f"Intent is 'summarize activities' with no keywords. Searching all records in time range.")

            with st.spinner(_t("natural_search_spinner_searching_db")):
                logger.info(f"Performing DB search: Keywords='{search_keywords}', Exclude='{exclude_keywords_str}', Start='{start_date}', End='{end_date}'")
                df_all, row_count, _ = db_manager.db_search_data(
                    keyword_input=search_keywords,
                    date_in=start_date,
                    date_out=end_date,
                    keyword_input_exclude=exclude_keywords_str
                )
                logger.info(f"Initial DB search returned {row_count} rows.")

            # --- Filter Results by Application ---
            df_filtered = df_all
            if applications:
                with st.spinner(_t("natural_search_spinner_filtering")):
                    try:
                        app_filter_pattern = '|'.join(map(re.escape, applications))
                        df_filtered = df_all[df_all['win_title'].fillna('').str.contains(app_filter_pattern, case=False, regex=True)]
                        logger.info(f"Filtered down to {len(df_filtered)} rows based on applications: {applications}")
                        st.info(f"{_t('natural_search_filter_info')} {', '.join(applications)}")
                    except Exception as filter_e:
                         logger.error(f"Error during application filtering: {filter_e}", exc_info=True)
                         st.warning("Could not apply application filter due to an error.")
                         df_filtered = df_all


            # --- Process and Display Results ---
            st.write("---")
            if not df_filtered.empty:
                # --- Handle First/Last Occurrence ---
                df_processed = df_filtered.copy() # Work on a copy
                if occurrence == "first":
                    df_processed = df_processed.sort_values(by='videofile_time', ascending=True)
                    df_display_final = df_processed.head(1)
                    st.info(_t("natural_search_showing_first"))
                    logger.info("Showing first occurrence based on user query.")
                elif occurrence == "last":
                    df_processed = df_processed.sort_values(by='videofile_time', ascending=False)
                    df_display_final = df_processed.head(1)
                    st.info(_t("natural_search_showing_last"))
                    logger.info("Showing last occurrence based on user query.")
                else:
                    # 默认按按最近的一次排序
                    df_processed = df_processed.sort_values(by='videofile_time', ascending=False)
                    df_display_final = df_processed

                df_display_component = db_manager.db_refine_search_data_global(df_display_final)


                # --- Summarization ---
                needs_summary = "summarize" in user_intent.lower() or (user_intent == "general search" and not df_display_final.empty)

                if needs_summary:
                     with st.spinner(_t("natural_search_spinner_summarizing")):
                         # 当用户意图包含"summarize"或是普通搜索且有结果时，会触发汇总功能
                         # 从最终结果中提取前30条记录的OCR文本 该选项应可由用户自由设置
                         ocr_context = df_display_final.head(30)['ocr_text'].tolist()
                         summary = summarize_results(ocr_context, user_intent, query)
                         if summary:
                             st.subheader(_t("natural_search_summary_header"))
                             st.markdown(summary)
                             st.write("---")


                # 展示结果
                st.subheader(_t("natural_search_relevant_moments"))
                if occurrence in ["first", "last"]:
                    st.success(f"🔎 {_t('natural_search_specific_occurrence_found').format(occurrence=occurrence)}")
                    components.video_dataframe(df_display_component, heightIn=200)
                else:
                    st.success(f"🔎 {_t('natural_search_results_found').format(count=len(df_display_final))}")
                    MAX_RESULTS_DISPLAY = 20
                    components.video_dataframe(df_display_component.head(MAX_RESULTS_DISPLAY), heightIn=600)
                    if len(df_display_component) > MAX_RESULTS_DISPLAY:
                        with st.expander(_t("natural_search_show_all_results").format(count=len(df_display_component))):
                             components.video_dataframe(df_display_component, heightIn=800)

            else:
                st.warning(_t("natural_search_no_results"), icon="🤷")
        else:
            # 错误信息由parse_natural_query 提供
            pass

# def add_natural_search_to_ui(pages_dict: dict):
#     pages_dict[_t("natural_search_page_name")] = render_natural_search_page

