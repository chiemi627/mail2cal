#!/bin/bash
# mail2cal インストールスクリプト
# cloneしたディレクトリで実行してください

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

echo "mail2cal をインストールします"
echo "ソースディレクトリ: $SCRIPT_DIR"
echo ""

# 実行権限を付与
chmod +x "$SCRIPT_DIR/mail2cal-service.sh" "$SCRIPT_DIR/mail2cal.sh" "$SCRIPT_DIR/mail2cal-extract.py"

# 設定ファイルがなければサンプルからコピー
if [ ! -f "$SCRIPT_DIR/mail2cal-config.json" ]; then
    cp "$SCRIPT_DIR/mail2cal-config.json.example" "$SCRIPT_DIR/mail2cal-config.json"
    echo "設定ファイルを作成しました: mail2cal-config.json"
    echo "必要に応じて時限表などを編集してください。"
    echo ""
fi

# AppleScriptにこのディレクトリのパスを埋め込んでビルド
APPLESCRIPT_CONTENT="-- mail2cal: クリップボードのメール本文から予定を抽出してカレンダーに登録
-- 使い方: Outlookでメール本文をCmd+A → Cmd+Cした後にこのアプリを起動

set emailText to the clipboard as text

if emailText is \"\" then
	display dialog \"クリップボードが空です。\" & return & return & \"Outlookでメール本文を Cmd+A → Cmd+C でコピーしてから起動してください。\" buttons {\"OK\"} default button \"OK\" with icon caution with title \"mail2cal\"
	return
end if

set scriptPath to \"$SCRIPT_DIR/mail2cal-service.sh\"

try
	do shell script \"export PATH=/usr/local/bin:/usr/bin:/bin:/opt/homebrew/bin:\$PATH; echo \" & quoted form of emailText & \" | \" & quoted form of scriptPath
on error errMsg number errNum
	if errNum is not -128 then
		display dialog \"エラー: \" & errMsg buttons {\"OK\"} default button \"OK\" with icon caution with title \"mail2cal\"
	end if
end try"

mkdir -p ~/Applications
echo "$APPLESCRIPT_CONTENT" | osacompile -o ~/Applications/mail2cal.app

echo "インストール完了!"
echo ""
echo "使い方:"
echo "  1. Outlookでメールを開いて Cmd+A → Cmd+C"
echo "  2. Cmd+Space →「mail2cal」→ Enter"
echo ""
echo "ターミナルからも使えます:"
echo "  $SCRIPT_DIR/mail2cal.sh"
