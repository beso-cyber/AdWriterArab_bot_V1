import logging
import os
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties
from aiogram import F
from dotenv import load_dotenv
from groq import Groq

# ====================== LOAD ENV ======================
load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = os.getenv("ADMIN_ID")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")

# ====================== LOGGING ======================
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ====================== GROQ INIT ======================
groq_client = None
if GROQ_API_KEY:
    try:
        groq_client = Groq(api_key=GROQ_API_KEY)
        logger.info("Groq Client initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize Groq: {e}")
else:
    logger.warning("GROQ_API_KEY not found!")

# ====================== AI FUNCTION ======================
def generate_with_groq(prompt: str) -> str | None:
    """Generate text using Groq API"""
    if not groq_client:
        return None

    try:
        response = groq_client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {"role": "system", "content": "أنت كاتب محتوى محترف."},
                {"role": "user", "content": prompt},
            ],
            max_tokens=2000,
            temperature=0.8,
        )
        return response.choices[0].message.content

    except Exception as e:
        logger.error(f"Groq error: {e}")
        return None


# ====================== BOT SETUP ======================
bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
dp = Dispatcher()


# ====================== COMMANDS ======================
@dp.message(Command("start"))
async def start_cmd(msg: types.Message):
    await msg.answer("مرحباً! 👋\nأرسل لي أي نص وسأعيد صياغته بالذكاء الاصطناعي ✨")


@dp.message(F.text)
async def process_text(msg: types.Message):
    prompt = msg.text

    await msg.answer("⏳ جاري المعالجة...")

    result = generate_with_groq(prompt)

    if not result:
        await msg.answer("❌ حدث خطأ أثناء الاتصال بالذكاء الاصطناعي.")
    else:
        await msg.answer(f"✔️ تمت المعالجة:\n\n{result}")


# ====================== RUN ======================
async def main():
    logger.info("Bot started...")
    await dp.start_polling(bot)


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
