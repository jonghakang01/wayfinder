#!/usr/bin/env python3
"""
Telegram bot that lets the authorized user send commands to Claude,
which can run bash, manage the server, deploy code, etc.
Monitoring alerts are sent directly via Telegram Bot API (no Claude API cost).
"""
import asyncio, os, subprocess, logging
from telegram import Update
from telegram.ext import Application, MessageHandler, CommandHandler, filters, ContextTypes
import anthropic

TELEGRAM_TOKEN = os.environ["TELEGRAM_TOKEN"]
AUTHORIZED_ID  = int(os.environ["AUTHORIZED_CHAT_ID"])
ANTHROPIC_KEY  = os.environ["ANTHROPIC_API_KEY"]

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger(__name__)

client = anthropic.Anthropic(api_key=ANTHROPIC_KEY)

TOOLS = [
    {
        "name": "bash",
        "description": "Run a shell command on the production server and return stdout+stderr.",
        "input_schema": {
            "type": "object",
            "properties": {
                "command": {"type": "string", "description": "The bash command to run"}
            },
            "required": ["command"]
        }
    }
]

SYSTEM = """You are Jonghabot, a personal AI assistant for jongha.kang — accessible via Telegram anytime.

You can do two things:
1. General conversation, questions, advice, ideas — just chat naturally.
2. Server management for the Wayfinder web app (134.209.62.57):
   - App service: systemctl restart/status wayfinder
   - Health check: curl http://localhost:8765/health
   - Repo: /root/webapp (git pull to update, systemctl restart wayfinder to deploy)

Use the bash tool only when the user asks to do something on the server.
Always respond in Korean. Be warm and concise."""


def run_bash(command: str) -> str:
    try:
        result = subprocess.run(
            command, shell=True, capture_output=True, text=True, timeout=30
        )
        out = (result.stdout + result.stderr).strip()
        return out[:2000] if out else "(no output)"
    except subprocess.TimeoutExpired:
        return "Error: command timed out (30s)"
    except Exception as e:
        return f"Error: {e}"


def chat_with_claude(user_message: str) -> str:
    messages = [{"role": "user", "content": user_message}]
    for _ in range(10):  # max tool iterations
        response = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=1024,
            system=SYSTEM,
            tools=TOOLS,
            messages=messages,
        )
        if response.stop_reason == "end_turn":
            text = "".join(b.text for b in response.content if hasattr(b, "text"))
            return text or "(응답 없음)"

        if response.stop_reason == "tool_use":
            messages.append({"role": "assistant", "content": response.content})
            tool_results = []
            for block in response.content:
                if block.type == "tool_use" and block.name == "bash":
                    result = run_bash(block.input["command"])
                    log.info("bash: %s → %s", block.input["command"][:80], result[:80])
                    tool_results.append({
                        "type": "tool_result",
                        "tool_use_id": block.id,
                        "content": result
                    })
            messages.append({"role": "user", "content": tool_results})
        else:
            break
    return "처리 중 오류가 발생했습니다."


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != AUTHORIZED_ID:
        await update.message.reply_text("권한 없음")
        return
    user_text = update.message.text
    await update.message.chat.send_action("typing")
    try:
        reply = await asyncio.to_thread(chat_with_claude, user_text)
    except Exception as e:
        reply = f"오류: {e}"
    await update.message.reply_text(reply)


async def cmd_status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != AUTHORIZED_ID:
        return
    status = run_bash("systemctl is-active wayfinder && curl -s http://localhost:8765/health")
    await update.message.reply_text(f"서버 상태:\n{status}")


async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != AUTHORIZED_ID:
        return
    await update.message.reply_text(
        "안녕하세요! Jonghabot입니다.\n\n"
        "명령어:\n"
        "/status — 서버 상태 확인\n"
        "그 외 메시지 → Claude가 처리합니다."
    )


def main():
    app = Application.builder().token(TELEGRAM_TOKEN).build()
    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("status", cmd_status))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    log.info("Jonghabot starting...")
    app.run_polling(drop_pending_updates=True)


if __name__ == "__main__":
    main()
