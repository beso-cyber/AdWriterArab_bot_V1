import asyncio
import logging
import os
from dotenv import load_dotenv

load_dotenv()

try:
    from config import BOT_TOKEN, GROQ_API_KEY, MODEL
except ImportError:
    # fallback لو config مش موجود
    BOT_TOKEN = os.getenv("BOT_TOKEN")
    GROQ_API_KEY = os.getenv("GROQ_API_KEY")
    MODEL = os.getenv("MODEL", "llama3-8b-8192")

from aiogram import Bot, Dispatcher, types
from aiogram.filters import CommandStart
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode

# Telegram Bot
bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
dp = Dispatcher()

# Groq Client
groq_client = None
try:
    from groq import Groq
    groq_client = Groq(api_key=GROQ_API_KEY)
    logging.info("✅ Groq client initialized")
except Exception as e:
    logging.error(f"❌ Groq initialization failed: {e}")

# ----------- AI Function -----------
def generate_ad(prompt: str) -> str:
    if not groq_client:
        return "⚠️ Groq غير مفعل – حط الكي في Environment Variables"
    
    try:
        response = groq_client.chat.completions.create(
            model=MODEL,
            messages=[
                {
                    "role": "system",
                    "content": "You are an advertising assistant. Write creative Arabic marketing copy."
                },
                {"role": "user", "content": prompt}
            ],
            max_tokens=500,
            temperature=0.7,
        )

        return response.choices[0].message.content

    except Exception as e:
        return f"⚠️ خطأ أثناء الاتصال بنموذج الذكاء الصناعي:\n{e}"

# ----------- HANDLERS -----------

@dp.message(CommandStart())
async def start_handler(message: types.Message):
    status = "✅ مفعل" if groq_client else "❌ غير مفعل"
    await message.answer(
        f"👋 مرحباً! بوت AdWriter مع Groq {status}.\n\n"
        "اكتب فكرتك الإعلانية وسأقوم بإنشاء إعلان احترافي لك.\n\n"
        "مثال: عبايات نساء سعودي فاخرة"
    )

@dp.message()
async def ad_writer(message: types.Message):
    user_prompt = message.text

    await message.answer("⏳ جاري كتابة الإعلان…")

    # استخدم to_thread عشان generate_ad sync
    ai_response = await asyncio.to_thread(generate_ad, user_prompt)

    await message.answer(ai_response)

# ----------- START BOT -----------
async def main():
    logging.info("🚀 بدء تشغيل البوت")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
