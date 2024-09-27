import logging
import sys
import asyncio
import time
from aiogram import Bot, Dispatcher, types, F
from aiogram.enums import ParseMode
from aiogram.filters import CommandStart, Command
from aiogram.types import Message, InlineKeyboardButton, FSInputFile
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.fsm.context import FSMContext
from aiogram.fsm.storage.memory import MemoryStorage
from data import config
from menucommands.set_bot_commands import set_default_commands
from baza.sqlite import Database
from filters.admin import IsBotAdminFilter
from filters.check_sub_channel import IsCheckSubChannels
from states.reklama import Adverts
from keyboard_buttons import admin_keyboard
from moviepy.editor import VideoFileClip
import os
import aiohttp
import logging
from aiogram.types import CallbackQuery, ContentType
from filters.admin import IsBotAdminFilter,AdminStates
from aiogram.fsm.state import State, StatesGroup
from buttons import savol_button
# Konfiguratsiya
ADMINS = config.ADMINS
TOKEN = config.BOT_TOKEN
CHANNELS = config.CHANNELS
MAX_VIDEO_SIZE_MB = 50  # Maksimal video hajmi (MB)
MAX_VIDEO_DURATION = 420  # Maksimal video davomiyligi (soniya)

logging.basicConfig(level=logging.INFO)
dp = Dispatcher(storage=MemoryStorage())

@dp.message(F.content_type == 'video')
async def handle_video(message: types.Message):
    video = message.video
    file_size_mb = video.file_size / (1024 * 1024)  # MB

    if file_size_mb > MAX_VIDEO_SIZE_MB:
        await message.reply("⚠️ Video faylning hajmi juda katta. Iltimos, kichikroq video yuboring.")
        return

    # Ensure the downloads directory exists
    if not os.path.exists('downloads'):
        os.makedirs('downloads')

    # Get the file path
    file = await bot.get_file(video.file_id)
    file_path = file.file_path
    video_url = f"https://api.telegram.org/file/bot{TOKEN}/{file_path}"

    # Download the video file
    async with aiohttp.ClientSession() as session:
        async with session.get(video_url) as response:
            if response.status == 200:
                video_path = f"downloads/{video.file_id}.mp4"
                with open(video_path, 'wb') as f:
                    f.write(await response.read())
            else:
                await message.reply("❌ Video faylini yuklab olishda xatolik yuz berdi.")
                return

    # Check video duration and trim if necessary
    video_clip = VideoFileClip(video_path)
    if video_clip.duration > MAX_VIDEO_DURATION:
        # Trim the video to MAX_VIDEO_DURATION
        trimmed_video_path = f"downloads/{video.file_id}_trimmed.mp4"
        trimmed_video_clip = video_clip.subclip(0, MAX_VIDEO_DURATION)
        trimmed_video_clip.write_videofile(trimmed_video_path, codec="libx264")
        video_clip.close()
        video_path = trimmed_video_path
    else:
        video_clip.close()

    # Add delay for processing
    initial_message = await message.reply("📥 Video yuklandi! Konvertatsiya jarayonini kuting...")

    
    # Delete the initial message
    await initial_message.delete()

    # Convert video to audio using moviepy
    audio_path = f"downloads/{video.file_id}.mp3"
    
    try:
        video_clip = VideoFileClip(video_path)
        video_clip.audio.write_audiofile(audio_path)
        video_clip.close()
    except Exception as e:
        logging.error(f"Error converting video to audio: {e}")
        await message.reply("❌ Audio konvertatsiyasida xatolik yuz berdi. Iltimos, boshqa video yuboring.")
        return

    # Send the audio file back to the user
    audio = FSInputFile(audio_path)
    await message.reply_audio(audio=audio, caption="🎵 Mana, video audiyo formatda!")

    # Clean up files
    try:
        os.remove(video_path)
        os.remove(audio_path)
    except Exception as e:
        logging.error(f"Error cleaning up files: {e}")




@dp.message(CommandStart())
async def start_command(message: Message):
    full_name = message.from_user.full_name
    telegram_id = message.from_user.id
    try:
        db.add_user(full_name=full_name, telegram_id=telegram_id)  # Add user to the database
        await message.answer(
            text="""<b>Salom! 🎉</b> 

<b>Men Video to Audio botiman.</b> Sizga quyidagi funksiyalarni taqdim etaman:

<b>/help</b> - Bot qanday ishlashini tushuntiruvchi yordam. 🤔
<b>/about</b> - Bot haqidagi ma'lumot va yaratuvchilar haqida. 🛠️

<b>Qanday foydalanish kerak:</b>
Video yuboring va men uni ovozli xabarga aylantiraman. 🎥➡️🎤

<b>Agar qo'shimcha savollar yoki yordam kerak bo'lsa:</b>
<b>⚙️ Savollar yoki takliflar uchun</b> <b>⚙️ Savol yoki takliflar</b> tugmasini bosing va admin bilan bog'laning.

<b>Bot SifatDev IT Akademiyasi tomonidan yaratilgan.</b> 🌟

<b>Botni ishlatganingiz uchun rahmat!</b> 🎉""",
            parse_mode="html",
        reply_markup=savol_button)
    except Exception as e:
        await message.answer(
            text="""<b>Salom! 🎉</b> 

<b>Men Video to Audio botiman.</b> Sizga quyidagi funksiyalarni taqdim etaman:

<b>/help</b> - Bot qanday ishlashini tushuntiruvchi yordam. 🤔
<b>/about</b> - Bot haqidagi ma'lumot va yaratuvchilar haqida. 🛠️

<b>Qanday foydalanish kerak:</b>
Video yuboring va men uni ovozli xabarga aylantiraman. 🎥➡️🎤

<b>Agar qo'shimcha savollar yoki yordam kerak bo'lsa:</b>
<b>⚙️ Savollar yoki takliflar uchun</b> <b>⚙️ Savol yoki takliflar</b> tugmasini bosing va admin bilan bog'laning.

<b>Bot SifatDev IT Akademiyasi tomonidan yaratilgan.</b> 🌟

<b>Botni ishlatganingiz uchun rahmat!</b> 🎉""",
            parse_mode="html",
       reply_markup=savol_button )

@dp.message(IsCheckSubChannels())
async def kanalga_obuna(message: Message):
    text = ""
    inline_channel = InlineKeyboardBuilder()
    for index, channel in enumerate(CHANNELS):
        ChatInviteLink = await bot.create_chat_invite_link(channel)
        inline_channel.add(InlineKeyboardButton(text=f"{index+1}-kanal", url=ChatInviteLink.invite_link))
    inline_channel.adjust(1, repeat=True)
    button = inline_channel.as_markup()
    await message.answer(f"{text} kanallarga a'zo bo'ling", reply_markup=button)


@dp.message(Command("help"))
async def help_commands(message: Message):
    await message.answer("""<b>👋 Salom!</b> Men Video to Audio botiman.. Sizga quyidagi funksiyalarni taqdim etaman:

<b>1. /start</b> - Botni ishga tushiradi va siz bilan salomlashadi. 🤖
<b>2. /help</b> - Botning qanday ishlashini tushuntiruvchi yordam. 📚
<b>3. /about</b> - Bot yaratuvchilari va bot haqidagi to'liq ma'lumotlar. 🛠️

<b>📌 Qanday foydalanish kerak:</b>
- Video yuboring va men uni ovozli faylga aylantiraman. 🎥➡️🎤

<b>Agar qo'shimcha yordam kerak bo'lsa:</b>
- <b>⚙️ Savollar yoki takliflar uchun</b> savol yoki takliflar tugmasini bosing va admin bilan bog'laning.

<b>Bot SifatDev IT Akademiyasiga tegishli. 🌟</b>

<b>Botdan foydalanganingizdan xursandmiz</b>""", parse_mode="html")

@dp.message(Command("about"))
async def about_commands(message: Message):
    await message.answer("""<b>📢 /about - Bot Haqida Ma'lumot</b>

<b>👋 Salom! Men Video to Audio botiman.</b>

<b>Bot Haqida:</b>
- <b>Maqsad:</b> Video to Audio bot sizning matnlaringizni ovozli xabarlarga aylantiradi. Har qanday matnni yuboring va men uni sizga ovozli xabar sifatida qaytaraman.
- <b>Texnologiyalar:</b> Bot Python dasturlash tili yordamida yaratildi va <b>aiogram</b> kutubxonasi, <b>gTTS</b> (Google Text-to-Speech) kabi texnologiyalarni ishlatadi.
- <b>Qanday Ishlaydi:</b> Siz matn yuborganingizda, bot uni ovozga aylantiradi va ovozli xabar sifatida yuboradi.

<b>Rahmat va botni ishlatganingiz uchun rahmat!</b> 🎉""", parse_mode='html')
    
@dp.message(Command("admin"), IsBotAdminFilter(ADMINS))
async def is_admin(message: Message):
    await message.answer(text="Admin menu", reply_markup=admin_keyboard.admin_button)

@dp.message(F.text == "Foydalanuvchilar soni", IsBotAdminFilter(ADMINS))
async def users_count(message: types.Message):
    counts = db.count_users()
    if counts:  # Make sure the query was successful
        text = f"Botimizda {counts[0]} ta foydalanuvchi bor"
    else:
        text = "Foydalanuvchilar sonini olishda xatolik yuz berdi"
    await message.answer(text=text, parse_mode=ParseMode.HTML)

@dp.message(F.text == "Reklama yuborish", IsBotAdminFilter(ADMINS))
async def advert_dp(message: types.Message, state: FSMContext):
    await state.set_state(Adverts.adverts)
    await message.answer(text="Reklama yuborishingiz mumkin!", parse_mode=ParseMode.HTML)

@dp.message(Adverts.adverts)
async def send_advert(message: types.Message, state: FSMContext):
    message_id = message.message_id
    from_chat_id = message.from_user.id
    users = db.all_users_id()  # Get all user IDs from the database

    count = 0
    for user in users:
        try:
            await bot.copy_message(chat_id=user[0], from_chat_id=from_chat_id, message_id=message_id)
            count += 1
        except Exception as e:
            logging.exception(f"Foydalanuvchiga reklama yuborishda xatolik: {user[0]}", exc_info=e)
        time.sleep(0.01)  # Delay to avoid spamming the server too quickly

    await message.answer(f"Reklama {count} ta foydalanuvchiga yuborildi", parse_mode=ParseMode.HTML)
    await state.clear()


# Define the states for admin functionality
class AdminStates(StatesGroup):
    waiting_for_admin_message = State()
    waiting_for_reply_message = State()


class AdminStates(StatesGroup):
    waiting_for_admin_message = State()
    waiting_for_reply_message = State()


# Initialize logger
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Define admin states
class AdminStates(StatesGroup):
    waiting_for_admin_message = State()
    waiting_for_reply_message = State()

# Function to create inline keyboard for reply
def create_inline_keyboard(user_id):
    keyboard_builder = InlineKeyboardBuilder()
    keyboard_builder.button(
        text="Javob berish",
        callback_data=f"reply:{user_id}"
    )


    return keyboard_builder.as_markup()

@dp.message(lambda message: message.text == '✉️ Savollar va takliflar')
async def handle_savol_takliflar(message: Message, state: FSMContext):
    # Foydalanuvchiga admin uchun xabar yuborish uchun taklif qiluvchi matn
    await message.answer(
        "<b>📩 Sizning fikr va savollaringiz biz uchun muhim!</b>\n\n"
        "Iltimos, admin uchun xabar yuboring. Sizning savolingiz yoki taklifingiz "
        "tez orada ko'rib chiqiladi va sizga javob beriladi.\n\n"
        "<i>Matn, rasm, audio yoki boshqa turdagi fayllarni yuborishingiz mumkin.</i>",
        parse_mode='html'
    )
    await state.set_state(AdminStates.waiting_for_admin_message)

# Handle different content types for the message sent to admin
@dp.message(AdminStates.waiting_for_admin_message, F.content_type.in_([
    ContentType.TEXT, ContentType.AUDIO, ContentType.VOICE, ContentType.VIDEO,
    ContentType.PHOTO, ContentType.ANIMATION, ContentType.STICKER, 
    ContentType.LOCATION, ContentType.DOCUMENT, ContentType.CONTACT,
    ContentType.VIDEO_NOTE
]))
async def handle_admin_message(message: types.Message, state: FSMContext):
    user_id = message.from_user.id
    username = message.from_user.username
    first_name = message.from_user.first_name
    last_name = message.from_user.last_name or ""

    # Foydalanuvchini aniqlash (foydalanuvchi nomi yoki ismi/familiyasi)
    user_identifier = f"@{username}" if username else f"{first_name} {last_name}".strip()

    video_note = message.video_note
    inline_keyboard = create_inline_keyboard(user_id)

    for admin_id in ADMINS:
        try:
            if video_note:
                await bot.send_video_note(
                    admin_id,
                    video_note.file_id,
                    reply_markup=inline_keyboard
                )
            elif message.text:
                await bot.send_message(
                    admin_id,
                    f"👤 Foydalanuvchi: {user_identifier}\n✉️ Xabar:\n{message.text}",
                    reply_markup=inline_keyboard
                )
            elif message.audio:
                await bot.send_audio(
                    admin_id,
                    message.audio.file_id,
                    caption=f"👤 Foydalanuvchi: {user_identifier}\n🎧 Audio xabar",
                    reply_markup=inline_keyboard
                )
            elif message.voice:
                await bot.send_voice(
                    admin_id,
                    message.voice.file_id,
                    caption=f"👤 Foydalanuvchi: {user_identifier}\n🎤 Voice xabar",
                    reply_markup=inline_keyboard
                )
            elif message.video:
                await bot.send_video(
                    admin_id,
                    message.video.file_id,
                    caption=f"👤 Foydalanuvchi: {user_identifier}\n🎬 Video xabar",
                    reply_markup=inline_keyboard
                )
            elif message.photo:
                await bot.send_photo(
                    admin_id,
                    message.photo[-1].file_id,
                    caption=f"👤 Foydalanuvchi: {user_identifier}\n🖼️ Rasm xabar",
                    reply_markup=inline_keyboard
                )
            elif message.animation:
                await bot.send_animation(
                    admin_id,
                    message.animation.file_id,
                    caption=f"👤 Foydalanuvchi: {user_identifier}\n🎞️ GIF xabar",
                    reply_markup=inline_keyboard
                )
            elif message.sticker:
                await bot.send_sticker(
                    admin_id,
                    message.sticker.file_id,
                    reply_markup=inline_keyboard
                )
            elif message.location:
                await bot.send_location(
                    admin_id,
                    latitude=message.location.latitude,
                    longitude=message.location.longitude,
                    reply_markup=inline_keyboard
                )
            elif message.document:
                await bot.send_document(
                    admin_id,
                    message.document.file_id,
                    caption=f"👤 Foydalanuvchi: {user_identifier}\n📄 Hujjat xabar",
                    reply_markup=inline_keyboard
                )
            elif message.contact:
                await bot.send_contact(
                    admin_id,
                    phone_number=message.contact.phone_number,
                    first_name=message.contact.first_name,
                    last_name=message.contact.last_name or "",
                    reply_markup=inline_keyboard
                )
        except Exception as e:
            logging.error(f"⚠️ Error sending message to admin {admin_id}: {e}")

    await state.clear()
    await bot.send_message(user_id, "✅ Admin sizga javob berishi mumkin.")

# Callback query handler for the reply button
@dp.callback_query(lambda c: c.data.startswith('reply:'))
async def process_reply_callback(callback_query: CallbackQuery, state: FSMContext):
    user_id = int(callback_query.data.split(":")[1])
    await callback_query.message.answer("📝 Javobingizni yozing. Sizning javobingiz foydalanuvchiga yuboriladi.")
    await state.update_data(reply_user_id=user_id)
    await state.set_state(AdminStates.waiting_for_reply_message)
    await callback_query.answer()

# Handle admin reply and send it back to the user
@dp.message(AdminStates.waiting_for_reply_message)
async def handle_admin_reply(message: Message, state: FSMContext):
    data = await state.get_data()
    original_user_id = data.get('reply_user_id')

    if original_user_id:
        try:
            if message.text:
                await bot.send_message(original_user_id, f"📩 Admin javobi:\n{message.text}")
            elif message.voice:
                await bot.send_voice(original_user_id, message.voice.file_id)
            elif message.video_note:
                await bot.send_video_note(original_user_id, message.video_note.file_id)
            elif message.audio:
                await bot.send_audio(original_user_id, message.audio.file_id)
            elif message.sticker:
                await bot.send_sticker(original_user_id, message.sticker.file_id)
            elif message.video:
                await bot.send_video(original_user_id, message.video.file_id)

            await bot.send_message(ADMINS[0], "✅ Foydalanuvchiga habaringiz yuborildi!")
            await state.clear()  # Clear state after sending the reply
        except Exception as e:
            logger.error(f"⚠️ Error sending reply to user {original_user_id}: {e}")
            await message.reply("❌ Xatolik: Javob yuborishda xato yuz berdi.")
    else:
        await message.reply("⚠️ Xatolik: Javob yuborish uchun foydalanuvchi ID topilmadi.")


# Bot ishdan to'xtaganda barcha adminlarni xabardor qilish
@dp.shutdown()
async def off_startup_notify(bot: Bot):
    for admin in ADMINS:
        try:
            await bot.send_message(
                chat_id=int(admin),
                text="<b>⛔️ Bot ishdan to'xtadi!</b>\n\n"
                     "Bot faoliyati to'xtatildi. Agar bu rejalashtirilmagan bo'lsa, "
                     "iltimos, darhol tekshiring va botni qayta ishga tushiring.",
                parse_mode='html'
            )
        except Exception as err:
            logging.exception(f"Admin {admin} uchun xabar yuborishda xatolik yuz berdi: {err}")

def setup_middlewares(dispatcher: Dispatcher, bot: Bot) -> None:
    from middlewares.throttling import ThrottlingMiddleware
    dispatcher.message.middleware(ThrottlingMiddleware(slow_mode_delay=0.5))

async def main() -> None:
    global bot, db
    bot = Bot(TOKEN)
    db = Database(path_to_db="main.db")
    await set_default_commands(bot)
    setup_middlewares(dispatcher=dp, bot=bot)
    await dp.start_polling(bot)

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, stream=sys.stdout)
    asyncio.run(main())
