#!/bin/bash

# ==========================================
# 0. 安全設定與解密
# ==========================================
GIT_USER="iOvermind"
# 確保這裡的路徑跟你「拉過去」的位置一致
ENC_FILE="./tokens/.git-token.enc" 
REPO_PATH="github.com/iOvermind/RICH3_PATCHER"

# 檢查加密檔是否存在
if [ ! -f "$ENC_FILE" ]; then
    echo "❌ 找不到加密金鑰檔 ($ENC_FILE)！"
    echo "請確認你是否已將檔案移至 ./tokens/ 並在 .gitignore 加了例外。"
    exit 1
fi

echo "🔐 請輸入金鑰解鎖密碼:"
read -s DEC_PASSWORD 

# --- 解密核心 ---
GIT_TOKEN=$(echo "$DEC_PASSWORD" | openssl enc -d -aes-256-cbc -salt -pbkdf2 -in "$ENC_FILE" -pass stdin 2>/dev/null)

if [[ $? -ne 0 ]] || [[ -z "$GIT_TOKEN" ]]; then
    echo -e "\n❌ 密碼錯誤或解密失敗！"
    exit 1
fi
echo -e "\n🔓 金鑰解鎖成功！"

# 組合出本次專用的遠端網址，直接鎖定 TYM_OP
AUTH_URL="https://${GIT_USER}:${GIT_TOKEN}@${REPO_PATH}.git"

# ==========================================
# 1. 選單介面
# ==========================================
echo "=================================="
echo "   🚀 Git AES-256 傳輸助手 (TYM_OP 專用)"
echo "   👤 User: $GIT_USER"
echo "=================================="
echo "請選擇功能："
echo "  [1] ⬇️  下載更新 (Pull)"
echo "  [2] ⬆️  上傳備份 (Push)"
echo "=================================="
read -p "請輸入選項 [1/2]: " choice

# ==========================================
# 2. 執行邏輯
# ==========================================
if [ "$choice" == "1" ]; then
    echo "----------------------------------"
    echo "⬇️  正在從 $REPO_PATH 拉取..."
    git pull "$AUTH_URL" main
    echo "✅ 下載完成！"

elif [ "$choice" == "2" ]; then
    echo "----------------------------------"
    echo "📦 正在準備上傳程序..."

    # 檢查是否有 Python 環境才執行 pip freeze
    if [ -f "requirements.txt" ] || [ -d ".venv" ]; then
        echo "🐍 偵測到 Python 環境，更新 requirements.txt..."
        pip freeze > requirements.txt 2>/dev/null
    fi
    
    # 加入所有變更
    git add .

    echo "請輸入 Commit 訊息 (Enter 自動填時戳):"
    read input_msg

    if [ -z "$input_msg" ]; then
        commit_msg="Auto update: $(date '+%Y-%m-%d %H:%M:%S')"
    else
        commit_msg="$input_msg"
    fi

    if git diff --quiet && git diff --staged --quiet; then
        echo "⚠️  沒有偵測到變更，跳過提交..."
    else
        git commit -m "$commit_msg"
    fi

    echo "☁️  正在推送到 $REPO_PATH..."
    # 使用強制推送 (可選)，如果你剛才做了 reset 或清理大檔案，建議先用一般 push
    git push "$AUTH_URL" main
    
    if [ $? -eq 0 ]; then
        echo "✅ 上傳搞定！收工！"
    else
        echo "❌ 上傳失敗！可能是遠端有新內容，請先執行 [1] 下載更新。"
    fi
else
    echo "❌ 選項錯誤。"
    exit 1
fi

# 清理變數
unset GIT_TOKEN
unset AUTH_URL
unset DEC_PASSWORD