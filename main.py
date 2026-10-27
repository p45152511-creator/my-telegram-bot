import os
import json
import logging
import threading
from flask import Flask
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes

logging.basicConfig(level=logging.INFO)

# 📌 설정값 (토큰 및 관리자 고유번호)
TOKEN = "8974193543:AAElkOFGzTLey2tnEHfFNXGlWEYIOW2_DPM"
ADMIN_IDS = [8600070245, 8553277647]

# 1. Flask 서버 (Render 수면 방지용)
app = Flask('')

@app.route('/')
def home():
    return "Bot is alive!"

def run_flask():
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port)

# 2. 데이터 저장/로드 로직
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

# /my를 입력하여 숫자 입력 대기 중인 유저 세션 {user_id: True}
pending_users = {}

# 3. 텔레그램 봇 기능 정의
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user_name = update.effective_user.first_name

    if user_id not in user_data:
        user_data[user_id] = {"name": user_name, "count": 0}
        save_data()

    await update.message.reply_text(
        f"안녕하세요, {user_name}님! 👋\n\n"
        f"📌 사용 방법:\n"
        f"1. /my 명령어를 보냅니다.\n"
        f"2. 봇이 대기 상태가 되면 숫자를 보내 인증합니다.\n\n"
        f"📋 명령어:\n"
        f"/my - 내 인증 횟수 확인 및 숫자 입력하기\n"
        f"/list - 전체 인증 횟수 목록 확인\n"
        f"/reset - [관리자전용] 전체 횟수 초기화"
    )

# /my 명령어: 내 횟수 출력 및 숫자 입력 대기 상태 전환
async def my_count(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user_name = update.effective_user.first_name

    if user_id not in user_data:
        user_data[user_id] = {"name": user_name, "count": 0}
        save_data()

    count = user_data[user_id]["count"]
    pending_users[user_id] = True  # 대기 상태 켜기

    await update.message.reply_text(
        f"📊 {user_name}님의 현재 누적 인증: **{count}회**\n\n"
        f"✏️ 추가할 인증 횟수(숫자)를 메시지로 보내주세요!"
    )

# 숫자 메시지 처리 (대기 상태일 때만 인식)
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user_name = update.effective_user.first_name
    text = update.message.text.strip()

    # /my를 누른 대기 상태의 유저가 숫자를 보낸 경우에만 처리
    if pending_users.get(user_id):
        if text.isdigit():
            amount = int(text)
            user_data[user_id]["name"] = user_name
            user_data[user_id]["count"] += amount
            save_data()

            # 대기 상태 해제
            pending_users[user_id] = False

            await update.message.reply_text(
                f"✅ **{amount}회** 인증이 완료되었습니다!\n"
                f"👤 {user_name}님의 총 누적 인증: **{user_data[user_id]['count']}회**"
            )
        else:
            await update.message.reply_text("⚠️ 숫자만 입력해 주세요! (/my를 다시 누르시면 취소됩니다)")

# /list: 전체 참여자 목록 보기
async def list_counts(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not user_data:
        await update.message.reply_text("아직 등록된 인증 기록이 없습니다.")
        return

    msg = "📋 **전체 참여자 인증 현황 목록**\n\n"
    for uid, info in user_data.items():
        name = info.get("name", "알 수 없음")
        count = info.get("count", 0)
        msg += f"• **{name}**: {count}회\n"

    await update.message.reply_text(msg, parse_mode="Markdown")

# /reset 또는 /reset_all: 관리자 초기화
async def reset_all(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in ADMIN_IDS:
        await update.message.reply_text("⚠️ 관리자 권한이 없습니다.")
        return

    for uid in user_data:
        user_data[uid]["count"] = 0
    save_data()
    pending_users.clear()

    await update.message.reply_text("🔄 **모든 사용자의 인증 횟수가 0으로 초기화되었습니다.**")

# 4. 앱 실행
if __name__ == '__main__':
    t_flask = threading.Thread(target=run_flask)
    t_flask.daemon = True
    t_flask.start()

    tg_app = ApplicationBuilder().token(TOKEN).build()

    tg_app.add_handler(CommandHandler("start", start))
    tg_app.add_handler(CommandHandler("my", my_count))
    tg_app.add_handler(CommandHandler("list", list_counts))
    tg_app.add_handler(CommandHandler("reset", reset_all))
    tg_app.add_handler(CommandHandler("reset_all", reset_all))
    tg_app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    tg_app.run_polling()

