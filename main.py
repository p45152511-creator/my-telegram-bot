import os
import json
import logging
import threading
from flask import Flask
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes

logging.basicConfig(level=logging.INFO)

# ==================================================
# 📌 설정값 (토큰 및 관리자 고유번호 직접 입력)
# ==================================================
TOKEN = "8974193543:AAElkOFGzTLey2tnEHfFNXGlWEYIOW2_DPM"
ADMIN_IDS = [8600070245, 8553277647]

# --------------------------------------------------
# 1. Flask 서버 (Render 무료 서버 수면 방지용)
# --------------------------------------------------
app = Flask('')

@app.route('/')
def home():
    return "Bot is alive!"

def run_flask():
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port)

# --------------------------------------------------
# 2. 데이터 저장/로드 로직 (JSON 파일 저장)
# --------------------------------------------------
DATA_FILE = "user_counts.json"

def load_data():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            return {int(k): v for k, v in data.items()}
    return {}

def save_data():
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(user_data, f, ensure_ascii=False, indent=4)

user_data = load_data()

# --------------------------------------------------
# 3. 텔레그램 봇 기능 정의
# --------------------------------------------------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user_name = update.effective_user.first_name

    if user_id not in user_data:
        user_data[user_id] = {"name": user_name, "count": 0}
        save_data()

    await update.message.reply_text(
        f"안녕하세요, {user_name}님! 👋\n\n"
        f"인증할 횟수(숫자)를 메시지로 보내주시면 누적 기록됩니다.\n\n"
        f"📌 명령어:\n/my - 내 인증 횟수 확인"
    )

async def add_count(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user_name = update.effective_user.first_name
    text = update.message.text.strip()

    if text.isdigit():
        amount = int(text)
        if user_id not in user_data:
            user_data[user_id] = {"name": user_name, "count": 0}

        user_data[user_id]["name"] = user_name
        user_data[user_id]["count"] += amount
        save_data()

        await update.message.reply_text(
            f"✅ **{amount}회** 인증 완료!\n"
            f"👤 {user_name}님의 총 누적 인증: **{user_data[user_id]['count']}회**"
        )
    else:
        await update.message.reply_text("숫자만 입력해 주세요! (예: 1, 2)")

async def my_count(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    count = user_data.get(user_id, {}).get("count", 0)
    await update.message.reply_text(f"📊 현재 누적 인증 횟수: **{count}회**")

async def reset_all(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in ADMIN_IDS:
        await update.message.reply_text("⚠️ 관리자 권한이 없습니다.")
        return
    for uid in user_data:
        user_data[uid]["count"] = 0
    save_data()
    await update.message.reply_text("🔄 **모든 사용자의 카운터가 초기화되었습니다.**")

# --------------------------------------------------
# 4. 앱 실행
# --------------------------------------------------
if __name__ == '__main__':
    t_flask = threading.Thread(target=run_flask)
    t_flask.daemon = True
    t_flask.start()

    tg_app = ApplicationBuilder().token(TOKEN).build()

    tg_app.add_handler(CommandHandler("start", start))
    tg_app.add_handler(CommandHandler("my", my_count))
    tg_app.add_handler(CommandHandler("reset_all", reset_all))
    tg_app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, add_count))

    tg_app.run_polling()
