import asyncio
import logging
import os
from dotenv import load_dotenv

load_dotenv()

# قراءة مباشرة من Environment (بدون config)
BOT_TOKEN = os.getenv("BOT_TOKEN")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
MODEL = os.getenv("MODEL", "llama3-8b-8192")

if not BOT_TOKEN:
    print("❌ BOT_TOKEN غير موجود!")
    exit(1)
if not GROQ_API_KEY:
    print("❌ GROQ_API_KEY غير موجود!")
    exit(1)

from aiogram import Bot, Dispatcher, types
from aiogram.filters import CommandStart
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
dp = Dispatcher()

# Groq Client (sync لتجنب proxies)
groq_client = None
try:
    from groq import Groq
    groq_client = Groq(api_key=GROQ_API_KEY)
    logger.info("✅ Groq متصل بنجاح")
except Exception as e:
    logger.error(f"❌ Groq فشل: {e}")

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
        return f"⚠️ خطأ في Groq:\n{e}"

# ----------- HANDLERS -----------

@dp.message(CommandStart())
async def start_handler(message: types.Message):
    status = "✅ مفعل" if groq_client else "❌ غير مفعل"
    await message.answer(
        f"👋 مرحباً! بوت AdWriter مع Groq {status}.\n\n"
        "اكتب فكرتك الإعلانية (مثل: عبايات نساء سعودي فاخرة)."
    )

@dp.message()
async def ad_writer(message: types.Message):
    user_prompt = message.text

    await message.answer("⏳ جاري كتابة الإعلان…")

    ai_response = await asyncio.to_thread(generate_ad, user_prompt)

    await message.answer(ai_response)

# ----------- START BOT -----------
async def main():
    logger.info("🚀 بدء تشغيل البوت")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
