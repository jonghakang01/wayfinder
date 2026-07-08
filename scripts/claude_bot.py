#!/usr/bin/env python3
"""
Jonghabot — Telegram bot supporting Claude and Gemini with session memory.
Commands:
  /start        — welcome
  /status       — server health
  /model        — show current model
  /model claude — switch to Claude (Haiku)
  /model gemini — switch to Gemini
  /clear        — clear conversation history
"""
import asyncio, json, os, subprocess, logging, time
from telegram import Update
from telegram.ext import Application, MessageHandler, CommandHandler, filters, ContextTypes
import anthropic

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger(__name__)

TELEGRAM_TOKEN    = os.environ["TELEGRAM_TOKEN"]
AUTHORIZED_ID     = int(os.environ["AUTHORIZED_CHAT_ID"])
ANTHROPIC_KEY     = os.environ.get("ANTHROPIC_API_KEY", "")
GEMINI_KEY        = os.environ.get("GEMINI_API_KEY", "")

SYSTEM = """You are Jonghabot, a personal AI assistant for jongha.kang — accessible via Telegram anytime.

You can:
1. Have general conversations, answer questions, give advice.
2. Manage the Wayfinder web app on server 134.209.62.57:
   - Check status: curl http://localhost:8765/health
   - Restart: systemctl restart wayfinder
   - Deploy: git -C /root/webapp pull && systemctl restart wayfinder
   - Logs: journalctl -u wayfinder -n 30

Use the bash tool only when the user asks to do something on the server.
Respond in Korean. Be warm and concise."""

TOOLS_ANTHROPIC = [{
    "name": "bash",
    "description": "Run a shell command on the production server.",
    "input_schema": {
        "type": "object",
        "properties": {"command": {"type": "string"}},
        "required": ["command"]
    }
}]

# Per-user state: {"model": "claude"|"gemini", "history": [...]}
user_state: dict = {}

def get_state(uid: int) -> dict:
    if uid not in user_state:
        user_state[uid] = {"model": "claude", "history": []}
    return user_state[uid]


def run_bash(command: str) -> str:
    try:
        result = subprocess.run(command, shell=True, capture_output=True, text=True, timeout=30)
        out = (result.stdout + result.stderr).strip()
        return out[:2000] if out else "(no output)"
    except subprocess.TimeoutExpired:
        return "Error: timed out (30s)"
    except Exception as e:
        return f"Error: {e}"


def chat_claude(history: list, user_message: str) -> str:
    messages = history + [{"role": "user", "content": user_message}]
    client = anthropic.Anthropic(api_key=ANTHROPIC_KEY)
    for _ in range(20):
        response = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=1024,
            system=SYSTEM,
            tools=TOOLS_ANTHROPIC,
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
                    log.info("bash: %s → %s", block.input["command"][:60], result[:60])
                    tool_results.append({
                        "type": "tool_result",
                        "tool_use_id": block.id,
                        "content": result
                    })
            messages.append({"role": "user", "content": tool_results})
        else:
            break
    return "처리 중 오류가 발생했습니다."


def chat_gemini(history: list, user_message: str) -> str:
    try:
        import google.generativeai as genai
        genai.configure(api_key=GEMINI_KEY)
        tool_def = {"function_declarations": [{
            "name": "bash",
            "description": "Run a shell command on the production server.",
            "parameters": {
                "type": "object",
                "properties": {"command": {"type": "string"}},
                "required": ["command"]
            }
        }]}
        model = genai.GenerativeModel(
            model_name="gemini-1.5-flash",
            system_instruction=SYSTEM,
            tools=[tool_def]
        )
        # Convert neutral history to Gemini format
        gemini_history = []
        for msg in history:
            role = "user" if msg["role"] == "user" else "model"
            content = msg["content"]
            if isinstance(content, str):
                gemini_history.append({"role": role, "parts": [{"text": content}]})
        chat = model.start_chat(history=gemini_history)
        response = chat.send_message(user_message)
        for _ in range(20):
            fn_call = None
            for part in response.parts:
                if hasattr(part, "function_call") and part.function_call.name:
                    fn_call = part.function_call
                    break
            if not fn_call:
                return response.text or "(응답 없음)"
            result = run_bash(fn_call.args["command"])
            log.info("bash(gemini): %s → %s", fn_call.args["command"][:60], result[:60])
            import google.generativeai.protos as protos
            response = chat.send_message(protos.Content(parts=[
                protos.Part(function_response=protos.FunctionResponse(
                    name=fn_call.name, response={"result": result}
                ))
            ]))
        return response.text or "처리 중 오류"
    except Exception as e:
        return f"Gemini 오류: {e}"


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != AUTHORIZED_ID:
        return
    state = get_state(AUTHORIZED_ID)
    user_text = update.message.text

    # Bridge: @cc/​/cc prefixed messages go to the local Claude CLI (쭌) via queue.
    # Local bridge-watcher polls this file over SSH and replies via Telegram API.
    stripped = (user_text or "").strip()
    if stripped.lower().startswith(("@cc", "/cc")):
        os.makedirs("/root/bridge", exist_ok=True)
        with open("/root/bridge/queue.jsonl", "a") as f:
            f.write(json.dumps({
                "chat_id": update.message.chat_id,
                "text": stripped,
                "ts": time.time(),
            }, ensure_ascii=False) + "\n")
        await update.message.reply_text("🔗 Delivered to Claude CLI. Reply will arrive shortly.")
        return

    await update.message.chat.send_action("typing")
    try:
        if state["model"] == "gemini" and GEMINI_KEY:
            reply = await asyncio.to_thread(chat_gemini, state["history"], user_text)
        elif ANTHROPIC_KEY:
            reply = await asyncio.to_thread(chat_claude, state["history"], user_text)
        else:
            reply = "API 키가 설정되지 않았습니다."
        # Update history (simple text only)
        state["history"].append({"role": "user", "content": user_text})
        state["history"].append({"role": "assistant", "content": reply})
        # Keep last 20 turns to avoid token limit
        if len(state["history"]) > 40:
            state["history"] = state["history"][-40:]
    except Exception as e:
        reply = f"오류: {e}"
    await update.message.reply_text(reply)


async def cmd_model(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != AUTHORIZED_ID:
        return
    state = get_state(AUTHORIZED_ID)
    args = context.args
    if not args:
        model = state["model"]
        claude_ok = "✅" if ANTHROPIC_KEY else "❌ (키 없음)"
        gemini_ok = "✅" if GEMINI_KEY else "❌ (키 없음)"
        await update.message.reply_text(
            f"현재 모델: *{model}*\n\nClaude: {claude_ok}\nGemini: {gemini_ok}\n\n"
            f"/model claude — Claude로 전환\n/model gemini — Gemini로 전환",
            parse_mode="Markdown"
        )
        return
    target = args[0].lower()
    if target == "claude":
        if not ANTHROPIC_KEY:
            await update.message.reply_text("Claude API 키가 없습니다.")
            return
        state["model"] = "claude"
        await update.message.reply_text("✅ Claude (Haiku)로 전환했습니다. 대화 기록은 유지됩니다.")
    elif target == "gemini":
        if not GEMINI_KEY:
            await update.message.reply_text("Gemini API 키가 없습니다. /setgemini [키] 로 설정하세요.")
            return
        state["model"] = "gemini"
        await update.message.reply_text("✅ Gemini로 전환했습니다. 대화 기록은 유지됩니다.")
    else:
        await update.message.reply_text("사용법: /model claude 또는 /model gemini")


async def cmd_clear(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != AUTHORIZED_ID:
        return
    get_state(AUTHORIZED_ID)["history"] = []
    await update.message.reply_text("🗑️ 대화 기록을 초기화했습니다.")


async def cmd_status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != AUTHORIZED_ID:
        return
    status = run_bash("systemctl is-active wayfinder && curl -s http://localhost:8765/health")
    await update.message.reply_text(f"서버 상태:\n{status}")


async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != AUTHORIZED_ID:
        return
    state = get_state(AUTHORIZED_ID)
    await update.message.reply_text(
        f"안녕하세요! Jonghabot입니다. 현재 모델: *{state['model']}*\n\n"
        "/status — 서버 상태\n"
        "/model — 모델 확인/전환\n"
        "/clear — 대화 초기화\n"
        "그 외 — Claude/Gemini와 자유 대화",
        parse_mode="Markdown"
    )


def main():
    app = Application.builder().token(TELEGRAM_TOKEN).build()
    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("status", cmd_status))
    app.add_handler(CommandHandler("model", cmd_model))
    app.add_handler(CommandHandler("clear", cmd_clear))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    log.info("Jonghabot starting (Claude=%s, Gemini=%s)...",
             bool(ANTHROPIC_KEY), bool(GEMINI_KEY))
    app.run_polling(drop_pending_updates=True)


if __name__ == "__main__":
    main()
