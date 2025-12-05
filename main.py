import asyncio
from aiogram import Bot, Dispatcher, types
from aiogram.filters import CommandStart
from config import BOT_TOKEN, GROQ_API_KEY, MODEL
from groq import Groq

# Telegram Bot
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# Groq Client
groq_client = Groq(api_key=GROQ_API_KEY)

# ----------- AI Function -----------
async def generate_ad(prompt: str) -> str:
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

        return response.choices[0].message["content"]

    except Exception as e:
        return f"⚠️ خطأ أثناء الاتصال بنموذج الذكاء الصناعي:\n{e}"

# ----------- HANDLERS -----------

@dp.message(CommandStart())
async def start_handler(message: types.Message):
    await message.answer(
        "👋 مرحباً! اكتب فكرتك الإعلانية وسأقوم بإنشاء إعلان احترافي لك."
    )

@dp.message()
async def ad_writer(message: types.Message):
    user_prompt = message.text

    await message.answer("⏳ جاري كتابة الإعلان…")

    ai_response = await generate_ad(user_prompt)

    await message.answer(ai_response)


# ----------- START BOT -----------
async def main():
    dp.include_router(dp)
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
