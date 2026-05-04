import asyncio
import logging
import os
from io import BytesIO

import requests
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command

# ================= НАСТРОЙКИ =================
TOKEN = os.getenv("TOKEN")  # Берём токен из переменных окружения Render

if not TOKEN:
    raise ValueError("TOKEN не найден! Добавь его в Environment Variables на Render.")

bot = Bot(token=TOKEN, parse_mode="HTML")
dp = Dispatcher()

# Простая база лимитов в памяти (на старте 10 генераций в день)
user_limits = {}

async def generate_image(prompt: str, width: int = 1024, height: int = 1024):
    """Генерация изображения через Pollinations.ai (Flux)"""
    try:
        encoded_prompt = requests.utils.quote(prompt)
        url = (
            f"https://gen.pollinations.ai/image/{encoded_prompt}?"
            f"model=flux&width={width}&height={height}&enhance=true&safe=false"
        )
        
        response = requests.get(url, timeout=40)
        
        if response.status_code == 200:
            return BytesIO(response.content)
        else:
            logging.error(f"Pollinations status: {response.status_code}")
            return None
    except Exception as e:
        logging.error(f"Generate error: {e}")
        return None


@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    await message.answer(
        "🎨 <b>AI Image Generator</b>\n\n"
        "Просто напиши, что хочешь увидеть.\n"
        "Примеры:\n"
        "• кот в космосе в стиле киберпанк\n"
        "• красивая девушка в неоновом городе\n"
        "• мем с собакой\n\n"
        "Лимит: 10 изображений в сутки на тестовом режиме."
    )


@dp.message()
async def handle_text(message: types.Message):
    prompt = message.text.strip()
    if len(prompt) < 3:
        await message.answer("❌ Слишком короткий запрос. Напиши подробнее.")
        return

    user_id = message.from_user.id

    # Лимит генераций
    if user_id not in user_limits:
        user_limits[user_id] = 0
    
    if user_limits[user_id] >= 10:
        await message.answer("⏳ Лимит 10 генераций на сегодня исчерпан.\n\nЗавтра лимит обновится.")
        return

    wait_msg = await message.answer("🎨 Генерирую... Это может занять 5–15 секунд.")

    image_bytes = await generate_image(prompt)

    if image_bytes:
        user_limits[user_id] += 1
        try:
            photo = types.BufferedInputFile(image_bytes.getvalue(), filename="generated.jpg")
            await bot.delete_message(wait_msg.chat.id, wait_msg.message_id)
            await message.answer_photo(
                photo=photo,
                caption=f"✅ <b>Готово!</b>\n\nЗапрос: {prompt}"
            )
        except Exception as e:
            logging.error(e)
            await message.answer("✅ Изображение готово, но ошибка отправки.")
    else:
        await bot.delete_message(wait_msg.chat.id, wait_msg.message_id)
        await message.answer("❌ Не удалось сгенерировать изображение. Попробуй другой промпт.")


async def main():
    logging.basicConfig(level=logging.INFO)
    print("🤖 Бот успешно запущен!")
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
