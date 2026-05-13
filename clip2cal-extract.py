#!/usr/bin/env python3
"""テキストから予定情報を正規表現で抽出する"""

import re
import json
import sys
import os
from datetime import datetime, timedelta

TODAY = datetime.now()

WEEKDAY_MAP = {
    "月": 0, "火": 1, "水": 2, "木": 3, "金": 4, "土": 5, "日": 6,
}

def load_config():
    script_dir = os.path.dirname(os.path.abspath(__file__))
    config_path = os.path.join(script_dir, "clip2cal-config.json")
    defaults = {
        "timezone": "Asia/Tokyo",
        "periods": {},
        "default_start_time": "09:00",
        "default_end_time": "10:00",
        "location_keywords": ["号室", "号館", "会議室", "教室", "ホール", "ラウンジ", "センター", "棟"],
    }
    if os.path.exists(config_path):
        with open(config_path) as f:
            user_config = json.load(f)
        defaults.update(user_config)
    period_table = {}
    for k, v in defaults["periods"].items():
        period_table[k] = (v[0], v[1])
    defaults["period_table"] = period_table
    return defaults

CONFIG = load_config()


def parse_date(text):
    dates = []
    used_ranges = []
    has_explicit = False

    def overlaps(start, end):
        return any(start < r[1] and end > r[0] for r in used_ranges)

    for m in re.finditer(r'(\d{4})[年/\-](\d{1,2})[月/\-](\d{1,2})[日]?', text):
        y, mo, d = int(m.group(1)), int(m.group(2)), int(m.group(3))
        try:
            dates.append((datetime(y, mo, d), m.start(), m.end()))
            used_ranges.append((m.start(), m.end()))
            has_explicit = True
        except ValueError:
            pass

    for m in re.finditer(r'(?<!\d[年/\-])(\d{1,2})月(\d{1,2})日', text):
        if overlaps(m.start(), m.end()):
            continue
        mo, d = int(m.group(1)), int(m.group(2))
        try:
            dt = datetime(TODAY.year, mo, d)
            if dt.date() < TODAY.date() - timedelta(days=30):
                dt = datetime(TODAY.year + 1, mo, d)
            dates.append((dt, m.start(), m.end()))
            used_ranges.append((m.start(), m.end()))
            has_explicit = True
        except ValueError:
            pass

    for m in re.finditer(r'(?<![:\d])(\d{1,2})/(\d{1,2})(?![:/\d])', text):
        if overlaps(m.start(), m.end()):
            continue
        mo, d = int(m.group(1)), int(m.group(2))
        if 1 <= mo <= 12 and 1 <= d <= 31:
            try:
                dt = datetime(TODAY.year, mo, d)
                if dt.date() < TODAY.date() - timedelta(days=30):
                    dt = datetime(TODAY.year + 1, mo, d)
                dates.append((dt, m.start(), m.end()))
                used_ranges.append((m.start(), m.end()))
                has_explicit = True
            except ValueError:
                pass

    for m in re.finditer(r'(今週|来週|再来週)の?([月火水木金土日])曜?日?', text):
        week_offset = {"今週": 0, "来週": 1, "再来週": 2}[m.group(1)]
        target_wd = WEEKDAY_MAP[m.group(2)]
        current_wd = TODAY.weekday()
        days_ahead = target_wd - current_wd + 7 * week_offset
        if week_offset == 0 and days_ahead < 0:
            days_ahead += 7
        dt = TODAY + timedelta(days=days_ahead)
        dates.append((dt, m.start(), m.end()))

    if not has_explicit:
        for m in re.finditer(r'(今日|本日|明日|明後日)', text):
            offset = {"今日": 0, "本日": 0, "明日": 1, "明後日": 2}[m.group(1)]
            dt = TODAY + timedelta(days=offset)
            dates.append((dt, m.start(), m.end()))

    return dates


def parse_time(text):
    times = []
    period_table = CONFIG["period_table"]

    if period_table:
        for m in re.finditer(r'(\d)限[〜~\-ー](\d)限', text):
            p1, p2 = m.group(1), m.group(2)
            if p1 in period_table and p2 in period_table:
                start = period_table[p1][0]
                end = period_table[p2][1]
                times.append((start, end, m.start(), m.end(), "period_range"))

        for m in re.finditer(r'(\d)[限]', text):
            pos = m.start()
            if any(t[2] <= pos < t[3] for t in times):
                continue
            p = m.group(1)
            if p in period_table:
                start, end = period_table[p]
                times.append((start, end, m.start(), m.end(), "period"))

    for m in re.finditer(r'(\d{1,2}):(\d{2})\s*[〜~\-ー]\s*(\d{1,2}):(\d{2})', text):
        start = f"{int(m.group(1)):02d}:{m.group(2)}"
        end = f"{int(m.group(3)):02d}:{m.group(4)}"
        times.append((start, end, m.start(), m.end(), "range"))

    for m in re.finditer(r'(\d{1,2})時(\d{1,2})分?\s*[〜~\-ー]\s*(\d{1,2})時(\d{1,2})分?', text):
        start = f"{int(m.group(1)):02d}:{int(m.group(2)):02d}"
        end = f"{int(m.group(3)):02d}:{int(m.group(4)):02d}"
        times.append((start, end, m.start(), m.end(), "range"))

    for m in re.finditer(r'(\d{1,2})時\s*[〜~\-ー]\s*(\d{1,2})時', text):
        start = f"{int(m.group(1)):02d}:00"
        end = f"{int(m.group(2)):02d}:00"
        times.append((start, end, m.start(), m.end(), "range"))

    for m in re.finditer(r'(?<!\d)(\d{1,2}):(\d{2})\s*[〜~\-ー](?!\s*\d)', text):
        pos = m.start()
        if any(t[2] <= pos < t[3] for t in times):
            continue
        h = int(m.group(1))
        start = f"{h:02d}:{m.group(2)}"
        end = f"{h+1:02d}:{m.group(2)}"
        times.append((start, end, m.start(), m.end(), "open_range"))

    for m in re.finditer(r'(?<!\d)(\d{1,2}):(\d{2})(?!\s*[〜~\-ー])', text):
        pos = m.start()
        if any(t[2] <= pos < t[3] for t in times):
            continue
        start = f"{int(m.group(1)):02d}:{m.group(2)}"
        h = int(m.group(1))
        end = f"{h+1:02d}:{m.group(2)}"
        times.append((start, end, m.start(), m.end(), "single"))

    for m in re.finditer(r'(?<!\d)(\d{1,2})時\s*[〜~\-ー](?!\s*\d)', text):
        pos = m.start()
        if any(t[2] <= pos < t[3] for t in times):
            continue
        h = int(m.group(1))
        start = f"{h:02d}:00"
        end = f"{h+1:02d}:00"
        times.append((start, end, m.start(), m.end(), "open_range"))

    for m in re.finditer(r'(?<!\d)(\d{1,2})時(?!\d)(?!\s*[〜~\-ー])', text):
        pos = m.start()
        if any(t[2] <= pos < t[3] for t in times):
            continue
        h = int(m.group(1))
        start = f"{h:02d}:00"
        end = f"{h+1:02d}:00"
        times.append((start, end, m.start(), m.end(), "single"))

    for m in re.finditer(r'午前', text):
        pos = m.start()
        if any(t[2] <= pos < t[3] for t in times):
            continue
        times.append(("09:00", "12:00", m.start(), m.end(), "ampm"))

    for m in re.finditer(r'午後', text):
        pos = m.start()
        if any(t[2] <= pos < t[3] for t in times):
            continue
        times.append(("13:00", "18:00", m.start(), m.end(), "ampm"))

    for m in re.finditer(r'終日', text):
        pos = m.start()
        if any(t[2] <= pos < t[3] for t in times):
            continue
        times.append(("", "", m.start(), m.end(), "allday"))

    return times


def parse_location(text):
    keywords = CONFIG["location_keywords"]
    patterns = [
        r'(?:場所|会場|教室|部屋)[：:\s]\s*(.+?)(?:\n|$|[。、])',
        r'(?:於|at)[：:\s]\s*(.+?)(?:\n|$|[。、])',
    ]
    if keywords:
        kw_pattern = "|".join(re.escape(k) for k in keywords)
        patterns.append(rf'(\S*(?:{kw_pattern})\S*)')
    for pat in patterns:
        m = re.search(pat, text)
        if m:
            return m.group(1).strip()
    return ""


def clean_title(s):
    s = re.sub(r'<[@#!&:][^>]*>', '', s)
    s = re.sub(r'[\x00-\x1f\x7f]', '', s)
    # 日付・時刻パターンを除去
    s = re.sub(r'\d{4}[年/\-]\d{1,2}[月/\-]\d{1,2}日?', '', s)
    s = re.sub(r'\d{1,2}月\d{1,2}日', '', s)
    s = re.sub(r'(?<![:\d])\d{1,2}/\d{1,2}(?![:/\d])', '', s)
    s = re.sub(r'[（(][月火水木金土日][）)]', '', s)
    s = re.sub(r'\d{1,2}:\d{2}\s*[〜~\-ー]\s*\d{1,2}:\d{2}', '', s)
    s = re.sub(r'\d{1,2}:\d{2}\s*[〜~\-ー]?', '', s)
    s = re.sub(r'\d{1,2}時\d{1,2}分?\s*[〜~\-ー]\s*\d{1,2}時\d{1,2}分?', '', s)
    s = re.sub(r'\d{1,2}時\s*[〜~\-ー]?\s*', '', s)
    s = re.sub(r'\d限[〜~\-ー]\d限', '', s)
    s = re.sub(r'\d限', '', s)
    s = re.sub(r'(今週|来週|再来週)の?[月火水木金土日]曜?日?', '', s)
    s = re.sub(r'(今日|本日|明日|明後日)', '', s)
    s = re.sub(r'(午前|午後|終日)', '', s)
    s = re.sub(r'R\d+年度', '', s)
    s = re.sub(r'\d{4}年度', '', s)
    # 残ったゴミを掃除
    s = re.sub(r'^[\s、。,.\-/：:の]+', '', s)
    s = re.sub(r'[\s、。,.\-/：:の]+$', '', s)
    return s.strip()

def parse_title(text):
    patterns = [
        r'(?:件名|Subject|Re:)[：:\s]\s*(.+?)(?:\n|$)',
        r'(?:会議名|タイトル|議題)[：:\s]\s*(.+?)(?:\n|$)',
    ]
    for pat in patterns:
        m = re.search(pat, text)
        if m and clean_title(m.group(1)):
            return clean_title(m.group(1))[:10]

    for line in text.strip().split('\n'):
        cleaned = clean_title(line)
        if cleaned:
            return cleaned[:10]
    return "予定"


def is_deadline(text, date_start, date_end):
    before = text[max(0, date_start - 10):date_start]
    after = text[date_end:date_end + 10]
    deadline_words = r'まで|締切|〆切|期限|必着|厳守'
    return bool(re.search(deadline_words, before + after))


def extract_events(text):
    dates = parse_date(text)
    times = parse_time(text)
    location = parse_location(text)
    title = parse_title(text)
    default_start = CONFIG["default_start_time"]
    default_end = CONFIG["default_end_time"]

    if not dates and not times:
        return {"found": False, "events": []}

    events = []

    if dates and times:
        used_times = set()
        for dt, dstart, dend in dates:
            if is_deadline(text, dstart, dend):
                events.append({
                    "title": f"【締切】{title}",
                    "start_date": dt.strftime("%Y-%m-%d"),
                    "start_time": "",
                    "end_date": dt.strftime("%Y-%m-%d"),
                    "end_time": "",
                    "location": location,
                    "description": text,
                    "all_day": True,
                })
                continue
            best_time = None
            best_dist = float('inf')
            for i, (tstart, tend, tpos_s, tpos_e, ttype) in enumerate(times):
                if i in used_times:
                    continue
                dist = abs(tpos_s - dend)
                if dist < best_dist:
                    best_dist = dist
                    best_time = (i, tstart, tend)
            if best_time:
                used_times.add(best_time[0])
                bt_type = times[best_time[0]][4]
                if bt_type == "allday":
                    events.append({
                        "title": title,
                        "start_date": dt.strftime("%Y-%m-%d"),
                        "start_time": "",
                        "end_date": dt.strftime("%Y-%m-%d"),
                        "end_time": "",
                        "location": location,
                        "description": text,
                        "all_day": True,
                    })
                else:
                    events.append({
                        "title": title,
                        "start_date": dt.strftime("%Y-%m-%d"),
                        "start_time": best_time[1],
                        "end_date": dt.strftime("%Y-%m-%d"),
                        "end_time": best_time[2],
                        "location": location,
                        "description": text,
                    })
            else:
                events.append({
                    "title": title,
                    "start_date": dt.strftime("%Y-%m-%d"),
                    "start_time": default_start,
                    "end_date": dt.strftime("%Y-%m-%d"),
                    "end_time": default_end,
                    "location": location,
                    "description": text,
                })
    elif dates:
        for dt, dstart, dend in dates:
            deadline = is_deadline(text, dstart, dend)
            events.append({
                "title": f"【締切】{title}" if deadline else title,
                "start_date": dt.strftime("%Y-%m-%d"),
                "start_time": "" if deadline else default_start,
                "end_date": dt.strftime("%Y-%m-%d"),
                "end_time": "" if deadline else default_end,
                "location": location,
                "description": text,
                "all_day": deadline,
            })
    elif times:
        for tstart, tend, _, _, _ in times:
            events.append({
                "title": title,
                "start_date": TODAY.strftime("%Y-%m-%d"),
                "start_time": tstart,
                "end_date": TODAY.strftime("%Y-%m-%d"),
                "end_time": tend,
                "location": location,
                "description": text,
            })

    return {"found": len(events) > 0, "events": events}


if __name__ == "__main__":
    text = sys.stdin.read()
    result = extract_events(text)
    print(json.dumps(result, ensure_ascii=False))
