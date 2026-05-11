#!/bin/bash
# clip2cal.sh — クリップボードのテキストから予定を抽出してカレンダーに登録する（ターミナル版）
# 使い方: 予定を含むテキストをコピー(Cmd+C)してから実行

set -euo pipefail

# 1. クリップボードからテキストを取得
INPUT_TEXT=$(pbpaste)

if [ -z "$INPUT_TEXT" ]; then
    echo "エラー: クリップボードが空です。"
    echo "予定を含むテキストをコピーしてから再実行してください。"
    exit 1
fi

echo "=== クリップボードの内容（先頭5行） ==="
echo "$INPUT_TEXT" | head -5
echo "..."
echo ""

# 2. 正規表現で予定情報を抽出
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

echo "予定を抽出中..."
JSON=$(echo "$INPUT_TEXT" | python3 "$SCRIPT_DIR/clip2cal-extract.py")

FOUND=$(echo "$JSON" | python3 -c "import sys,json; print(json.load(sys.stdin).get('found', False))")

if [ "$FOUND" != "True" ]; then
    echo "予定情報が見つかりませんでした。"
    exit 0
fi

# 3. 抽出した予定を表示して確認
echo ""
echo "=== 抽出された予定 ==="
echo "$JSON" | python3 -c "
import sys, json
data = json.load(sys.stdin)
for i, ev in enumerate(data['events'], 1):
    print(f\"  [{i}] {ev['title']}\")
    print(f\"      日時: {ev['start_date']} {ev['start_time']} 〜 {ev['end_date']} {ev['end_time']}\")
    if ev.get('location'):
        print(f\"      場所: {ev['location']}\")
    print()
"

echo -n "カレンダーに登録しますか？ (y/n): "
read -r CONFIRM
if [ "$CONFIRM" != "y" ] && [ "$CONFIRM" != "Y" ]; then
    echo "キャンセルしました。"
    exit 0
fi

# 4. .icsファイルを生成してカレンダーアプリで開く
ICS_DIR=$(mktemp -d)

echo "$JSON" | python3 -c "
import sys, json, os, subprocess, uuid

config_path = os.path.join('$SCRIPT_DIR', 'clip2cal-config.json')
tz = 'Asia/Tokyo'
calendar_app = ''
if os.path.exists(config_path):
    with open(config_path) as cf:
        cfg = json.load(cf)
        tz = cfg.get('timezone', tz)
        calendar_app = cfg.get('calendar_app', '')

data = json.load(sys.stdin)
ics_dir = '$ICS_DIR'

for i, ev in enumerate(data['events']):
    sd = ev['start_date'].replace('-', '')
    st = ev['start_time'].replace(':', '')
    ed = ev['end_date'].replace('-', '')
    et = ev['end_time'].replace(':', '')
    uid = str(uuid.uuid4())

    title = ev['title'].replace(',', '\\\\,').replace(';', '\\\\;')
    location = ev.get('location', '').replace(',', '\\\\,').replace(';', '\\\\;')
    description = ev.get('description', '').replace(',', '\\\\,').replace(';', '\\\\;').replace(chr(10), '\\\\n')

    ics = f'''BEGIN:VCALENDAR
VERSION:2.0
PRODID:-//clip2cal//EN
BEGIN:VEVENT
UID:{uid}
DTSTART;TZID={tz}:{sd}T{st}00
DTEND;TZID={tz}:{ed}T{et}00
SUMMARY:{title}
LOCATION:{location}
DESCRIPTION:{description}
END:VEVENT
END:VCALENDAR'''

    path = os.path.join(ics_dir, f'event_{i}.ics')
    with open(path, 'w') as f:
        f.write(ics)

    if calendar_app:
        subprocess.run(['open', '-a', calendar_app, path])
    else:
        subprocess.run(['open', path])
    print(f'  → カレンダーアプリでインポートダイアログを開きました: {ev[\"title\"]}')
"

echo ""
echo ".icsファイルが開かれます。カレンダーアプリで「保存」を押して登録してください。"
echo "一時ファイル: $ICS_DIR"
