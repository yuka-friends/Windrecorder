"""SQL shared by the application and the side-effect-free agent query API."""

import re


def keyword_conditions(query, exclude="", *, variants=None, title_column="win_title"):
    conditions, params = [], []
    for keyword in query.split():
        words = variants(keyword) if variants else [re.sub(r"(?<=\w)-(?=\w)", " ", keyword)]
        group = []
        for word in words:
            group.append(f"(ocr_text LIKE ? OR {title_column} LIKE ?)")
            params.extend([f"%{word}%", f"%{word}%"])
        conditions.append("(" + " OR ".join(group) + ")")
    if not conditions:
        conditions.append("ocr_text LIKE ?")
        params.append("%")
    for keyword in exclude.split():
        keyword = re.sub(r"(?<=\w)-(?=\w)", " ", keyword)
        conditions.append("ocr_text NOT LIKE ?")
        params.append(f"%{keyword}%")
    return conditions, params


def record_counts(conn, start_seconds, end_seconds, frequency):
    formats = {"hour": "%Y-%m-%d %H:00:00", "day": "%Y-%m-%d 00:00:00", "month": "%Y-%m-01 00:00:00"}
    return conn.execute(
        "SELECT strftime(?, videofile_time, 'unixepoch'), COUNT(*) FROM video_text "
        "WHERE videofile_time >= ? AND videofile_time < ? GROUP BY 1",
        (formats[frequency], start_seconds, end_seconds),
    ).fetchall()
