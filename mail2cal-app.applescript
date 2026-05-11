-- mail2cal: クリップボードのメール本文から予定を抽出してカレンダーに登録
-- 使い方: Outlookでメール本文をCmd+A → Cmd+Cした後にこのアプリを起動

set emailText to the clipboard as text

if emailText is "" then
	display dialog "クリップボードが空です。" & return & return & "Outlookでメール本文を Cmd+A → Cmd+C でコピーしてから起動してください。" buttons {"OK"} default button "OK" with icon caution with title "mail2cal"
	return
end if

-- install.sh がビルド時に実際のパスを埋め込みます
set scriptPath to "INSTALL_DIR/mail2cal-service.sh"

try
	do shell script "export PATH=/usr/local/bin:/usr/bin:/bin:/opt/homebrew/bin:$PATH; echo " & quoted form of emailText & " | " & quoted form of scriptPath
on error errMsg number errNum
	if errNum is not -128 then
		display dialog "エラー: " & errMsg buttons {"OK"} default button "OK" with icon caution with title "mail2cal"
	end if
end try
