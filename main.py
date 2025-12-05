import asyncio
import logging
import os
import sys
import json
from typing import Dict, List, Optional
from datetime import datetime

from aiogram import Bot, Dispatcher, F, Router
from aiogram.filters import Command, CommandStart
from aiogram.types import (
    Message, 
    CallbackQuery,
    InlineKeyboardMarkup, 
    InlineKeyboardButton,
    ReplyKeyboardMarkup,
    KeyboardButton
)
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from groq import AsyncGroq
from dotenv import load_dotenv

load_dotenv()

# ==================== CONFIGURATION ====================
BOT_TOKEN = os.getenv("BOT_TOKEN")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")

if not BOT_TOKEN:
    print("❌ خطأ: BOT_TOKEN غير موجود!")
    sys.exit(1)

# ==================== INITIALIZATION ====================
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Initialize bot
bot = Bot(
    token=BOT_TOKEN,
    default=DefaultBotProperties(parse_mode=ParseMode.HTML)
)

# Initialize FSM storage
storage = MemoryStorage()
dp = Dispatcher(storage=storage)

# Initialize Groq client
groq_client = None
if GROQ_API_KEY and GROQ_API_KEY.strip():
    try:
        groq_client = AsyncGroq(api_key=GROQ_API_KEY)
        logger.info("✅ Groq client initialized successfully")
    except Exception as e:
        logger.error(f"❌ Failed to initialize Groq: {e}")
        groq_client = None
else:
    logger.warning("⚠️ Groq API key not found. AI features disabled.")

# ==================== STATES ====================
class AdCreation(StatesGroup):
    waiting_for_product = State()
    waiting_for_audience = State()
    waiting_for_dialect = State()
    waiting_for_content_type = State()
    waiting_for_tone = State()
    waiting_for_length = State()

# ==================== TEMPLATES & OPTIONS ====================
# الخيارات التي ستظهر للمستخدم
CONTENT_TYPES = {
    "ads": "📢 إعلانات مبيعات",
    "social": "📱 منشورات السوشيال ميديا",
    "captions": "🏷️ كابشنات للصور",
    "email": "✉️ نصوص بريد إلكتروني",
    "blog": "📝 مقالات مدونات",
    "video": "🎬 نصوص فيديوهات"
}

DIALECTS = {
    "saudi": "🇸🇦 سعودي",
    "egyptian": "🇪🇬 مصري", 
    "emirati": "🇦🇪 إماراتي",
    "classic": "📚 فصحى",
    "gulf": "🏝️ خليجي عام"
}

TONES = {
    "enthusiastic": "🔥 حماسي",
    "professional": "💼 رسمي",
    "friendly": "😊 ودي",
    "persuasive": "🎯 إقناعي",
    "luxury": "💎 فاخر",
    "funny": "😂 مرح"
}

LENGTHS = {
    "short": "📏 قصير (1-2 جمل)",
    "medium": "📝 متوسط (3-5 جمل)",
    "long": "📄 طويل (6+ جمل)"
}

# ==================== HELPER FUNCTIONS ====================
def create_main_menu():
    """إنشاء القائمة الرئيسية"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🚀 إنشاء محتوى جديد", callback_data="create_new")],
        [InlineKeyboardButton(text="⚡ إنشاء سريع", callback_data="quick_create")],
        [InlineKeyboardButton(text="📚 القوالب الجاهزة", callback_data="templates")],
        [
            InlineKeyboardButton(text="⚙️ الإعدادات", callback_data="settings"),
            InlineKeyboardButton(text="ℹ️ المساعدة", callback_data="help")
        ],
        [InlineKeyboardButton(text="💎 ترقية للحساب المميز", callback_data="upgrade")]
    ])

def create_content_type_keyboard():
    """لوحة اختيار نوع المحتوى"""
    buttons = []
    row = []
    for key, value in CONTENT_TYPES.items():
        row.append(InlineKeyboardButton(text=value, callback_data=f"type_{key}"))
        if len(row) == 2:
            buttons.append(row)
            row = []
    if row:
        buttons.append(row)
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def create_dialect_keyboard():
    """لوحة اختيار اللهجة"""
    buttons = []
    row = []
    for key, value in DIALECTS.items():
        row.append(InlineKeyboardButton(text=value, callback_data=f"dialect_{key}"))
        if len(row) == 2:
            buttons.append(row)
            row = []
    if row:
        buttons.append(row)
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def create_tone_keyboard():
    """لوحة اختيار النبرة"""
    buttons = []
    row = []
    for key, value in TONES.items():
        row.append(InlineKeyboardButton(text=value, callback_data=f"tone_{key}"))
        if len(row) == 2:
            buttons.append(row)
            row = []
    if row:
        buttons.append(row)
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def create_length_keyboard():
    """لوحة اختيار الطول"""
    buttons = []
    for key, value in LENGTHS.items():
        buttons.append([InlineKeyboardButton(text=value, callback_data=f"length_{key}")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)

async def generate_with_groq(prompt: str) -> Optional[str]:
    """توليد المحتوى باستخدام Groq API"""
    if not groq_client:
        return None
    
    try:
        # اختر نموذج من Groq (كلها مجانية)
        available_models = [
            "llama-3.3-70b-versatile",  # الأفضل للنصوص العربية
            "llama-3.2-90b-vision",     # قوي جداً
            "mixtral-8x7b-32768",       # سريع وجيد
            "gemma2-9b-it"              # خفيف وسريع
        ]
        
        response = await groq_client.chat.completions.create(
            model=available_models[0],  # نستخدم النموذج الأول
            messages=[
                {
                    "role": "system", 
                    "content": "أنت كاتب محتوى عربي محترف، تجيد جميع اللهجات العربية وتكتب نصوصاً تسويقية مؤثرة."
                },
                {"role": "user", "content": prompt}
            ],
            temperature=0.8,
            max_tokens=2000,
            timeout=30
        )
        
        return response.choices[0].message.content
    except Exception as e:
        logger.error(f"Groq API error: {e}")
        return None

# ==================== COMMAND HANDLERS ====================
@dp.message(CommandStart())
async def start_command(message: Message, state: FSMContext):
    """معالجة أمر /start"""
    await state.clear()
    
    welcome_text = f"""
<b>🚀 أهلاً {message.from_user.first_name}!</b>

✨ <b>AdWriter Pro</b> - المنصة الذكية لكتابة المحتوى العربي

🎯 <b>المميزات:</b>
• كتابة محتوى بـ ٥ لهجات عربية
• ٦ أنواع مختلفة من المحتوى
• ٦ نبرات كتابة مختلفة
• نتائج فورية باستخدام الذكاء الاصطناعي
• واجهة تفاعلية سهلة

📊 <b>الحالة:</b> {'✅ متصل بـ Groq AI' if groq_client else '⚠️ وضع بدون ذكاء اصطناعي'}

👇 <b>اختر من القائمة:</b>
    """
    
    await message.answer(
        welcome_text,
        reply_markup=create_main_menu(),
        parse_mode=ParseMode.HTML
    )

@dp.callback_query(F.data == "create_new")
async def create_new_handler(callback: CallbackQuery, state: FSMContext):
    """بدء عملية إنشاء محتوى جديدة"""
    await state.clear()
    await state.set_state(AdCreation.waiting_for_product)
    
    await callback.message.answer(
        "🎯 <b>الخطوة 1 من 5</b>\n\n"
        "📝 <b>اكتب المنتج أو الخدمة:</b>\n\n"
        "<i>مثال:</i>\n"
        "• عطور رجالية فاخرة\n"
        "• دورة برمجة Python\n"
        "• مطعم برجر مميز\n"
        "• عبايات سوداء",
        parse_mode=ParseMode.HTML
    )
    await callback.answer()

@dp.callback_query(F.data == "quick_create")
async def quick_create_handler(callback: CallbackQuery, state: FSMContext):
    """إنشاء سريع"""
    await state.clear()
    
    quick_options = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="📱 إعلان انستقرام", callback_data="quick_instagram"),
            InlineKeyboardButton(text="✉️ بريد إلكتروني", callback_data="quick_email")
        ],
        [
            InlineKeyboardButton(text="🏷️ كابشن صورة", callback_data="quick_caption"),
            InlineKeyboardButton(text="🎬 نص فيديو", callback_data="quick_video")
        ],
        [InlineKeyboardButton(text="↩️ رجوع", callback_data="back_to_main")]
    ])
    
    await callback.message.answer(
        "⚡ <b>اختر نوع المحتوى السريع:</b>",
        reply_markup=quick_options,
        parse_mode=ParseMode.HTML
    )
    await callback.answer()

@dp.callback_query(F.data.startswith("quick_"))
async def handle_quick_create(callback: CallbackQuery, state: FSMContext):
    """معالجة الإنشاء السريع"""
    quick_type = callback.data.replace("quick_", "")
    
    type_names = {
        "instagram": "إعلان انستقرام",
        "email": "بريد إلكتروني",
        "caption": "كابشن صورة",
        "video": "نص فيديو"
    }
    
    await state.update_data(
        content_type=quick_type,
        dialect="saudi",
        tone="enthusiastic",
        length="medium"
    )
    await state.set_state(AdCreation.waiting_for_product)
    
    await callback.message.answer(
        f"⚡ <b>إنشاء سريع: {type_names.get(quick_type, 'محتوى')}</b>\n\n"
        "📝 <b>اكتب المنتج أو الخدمة:</b>\n\n"
        "<i>مثال: عطور رجالية</i>",
        parse_mode=ParseMode.HTML
    )
    await callback.answer()

# ==================== STATE HANDLERS ====================
@dp.message(AdCreation.waiting_for_product)
async def process_product(message: Message, state: FSMContext):
    """معالجة المنتج"""
    await state.update_data(product=message.text)
    await state.set_state(AdCreation.waiting_for_audience)
    
    await message.answer(
        "✅ <b>تم حفظ المنتج</b>\n\n"
        "🎯 <b>الخطوة 2 من 5</b>\n\n"
        "👥 <b>حدد الجمهور المستهدف:</b>\n\n"
        "<i>مثال:</i>\n"
        "• رجال أعمال\n"
        "• سيدات ٢٥-٤٠ سنة\n"
        "• شباب طلاب الجامعة\n"
        "• الأمهات العاملات",
        parse_mode=ParseMode.HTML
    )

@dp.message(AdCreation.waiting_for_audience)
async def process_audience(message: Message, state: FSMContext):
    """معالجة الجمهور"""
    await state.update_data(audience=message.text)
    await state.set_state(AdCreation.waiting_for_content_type)
    
    await message.answer(
        "✅ <b>تم حفظ الجمهور</b>\n\n"
        "🎯 <b>الخطوة 3 من 5</b>\n\n"
        "📋 <b>اختر نوع المحتوى:</b>",
        reply_markup=create_content_type_keyboard(),
        parse_mode=ParseMode.HTML
    )

@dp.callback_query(F.data.startswith("type_"), AdCreation.waiting_for_content_type)
async def process_content_type(callback: CallbackQuery, state: FSMContext):
    """معالجة نوع المحتوى"""
    content_type = callback.data.replace("type_", "")
    await state.update_data(content_type=content_type)
    await state.set_state(AdCreation.waiting_for_dialect)
    
    content_name = CONTENT_TYPES.get(content_type, "محتوى")
    
    await callback.message.answer(
        f"✅ <b>تم اختيار: {content_name}</b>\n\n"
        "🎯 <b>الخطوة 4 من 5</b>\n\n"
        "🗣️ <b>اختر اللهجة:</b>",
        reply_markup=create_dialect_keyboard(),
        parse_mode=ParseMode.HTML
    )
    await callback.answer()

@dp.callback_query(F.data.startswith("dialect_"), AdCreation.waiting_for_dialect)
async def process_dialect(callback: CallbackQuery, state: FSMContext):
    """معالجة اللهجة"""
    dialect = callback.data.replace("dialect_", "")
    await state.update_data(dialect=dialect)
    await state.set_state(AdCreation.waiting_for_tone)
    
    dialect_name = DIALECTS.get(dialect, "عامية")
    
    await callback.message.answer(
        f"✅ <b>تم اختيار: {dialect_name}</b>\n\n"
        "🎯 <b>الخطوة 5 من 5</b>\n\n"
        "🎨 <b>اختر نبرة النص:</b>",
        reply_markup=create_tone_keyboard(),
        parse_mode=ParseMode.HTML
    )
    await callback.answer()

@dp.callback_query(F.data.startswith("tone_"), AdCreation.waiting_for_tone)
async def process_tone(callback: CallbackQuery, state: FSMContext):
    """معالجة النبرة"""
    tone = callback.data.replace("tone_", "")
    await state.update_data(tone=tone)
    
    # طلب الطول
    tone_name = TONES.get(tone, "محايد")
    
    await callback.message.answer(
        f"✅ <b>تم اختيار: {tone_name}</b>\n\n"
        "📏 <b>اختر طول النص:</b>",
        reply_markup=create_length_keyboard(),
        parse_mode=ParseMode.HTML
    )
    await callback.answer()

@dp.callback_query(F.data.startswith("length_"))
async def process_length_and_generate(callback: CallbackQuery, state: FSMContext):
    """معالجة الطول وتوليد المحتوى"""
    length = callback.data.replace("length_", "")
    await state.update_data(length=length)
    
    # جمع جميع البيانات
    data = await state.get_data()
    product = data.get('product', '')
    audience = data.get('audience', '')
    content_type = data.get('content_type', 'ads')
    dialect = data.get('dialect', 'saudi')
    tone = data.get('tone', 'enthusiastic')
    length_type = data.get('length', 'medium')
    
    # إعلام المستخدم بالبدء
    processing_msg = await callback.message.answer(
        "⏳ <b>جاري توليد المحتوى...</b>\n\n"
        f"📦 المنتج: {product}\n"
        f"👥 الجمهور: {audience}\n"
        f"📋 النوع: {CONTENT_TYPES.get(content_type, 'إعلان')}\n"
        f"🗣️ اللهجة: {DIALECTS.get(dialect, 'سعودي')}\n"
        f"🎨 النبرة: {TONES.get(tone, 'حماسي')}\n"
        f"📏 الطول: {LENGTHS.get(length_type, 'متوسط')}",
        parse_mode=ParseMode.HTML
    )
    
    try:
        # إنشاء الـ Prompt بناءً على الخيارات
        prompt = create_prompt(product, audience, content_type, dialect, tone, length_type)
        
        # توليد المحتوى
        generated_content = None
        if groq_client:
            generated_content = await generate_with_groq(prompt)
        
        # إرسال النتائج
        if generated_content:
            result_text = f"""
✅ <b>تم إنشاء المحتوى بنجاح!</b>

📊 <b>التفاصيل:</b>
• المنتج: {product}
• الجمهور: {audience}
• النوع: {CONTENT_TYPES.get(content_type, 'محتوى')}
• اللهجة: {DIALECTS.get(dialect, 'عامية')}
• النبرة: {TONES.get(tone, 'محايد')}
• الطول: {LENGTHS.get(length_type, 'متوسط')}

{'═' * 30}

{generated_content}

{'═' * 30}

📱 <i>انسخ النص واستخدمه مباشرة</i>

🔄 <b>لإنشاء محتوى جديد:</b>
/start
            """
        else:
            # استخدام قوالب ثابتة إذا فشل التوليد
            result_text = generate_static_content(product, audience, content_type, dialect, tone, length_type)
        
        # تقسيم النص إذا كان طويلاً
        if len(result_text) > 4000:
            parts = [result_text[i:i+4000] for i in range(0, len(result_text), 4000)]
            for part in parts:
                await callback.message.answer(part, parse_mode=ParseMode.HTML)
        else:
            await callback.message.answer(result_text, parse_mode=ParseMode.HTML)
        
        # حذف رسالة الانتظار
        await processing_msg.delete()
        
        # عرض خيارات إضافية
        options_kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🔄 إنشاء محتوى جديد", callback_data="create_new")],
            [InlineKeyboardButton(text="⚡ إنشاء سريع", callback_data="quick_create")],
            [InlineKeyboardButton(text="📊 تحليل النص", callback_data="analyze")],
            [InlineKeyboardButton(text="💾 حفظ القالب", callback_data="save_template")]
        ])
        
        await callback.message.answer(
            "✨ <b>ماذا تريد أن تفعل الآن؟</b>",
            reply_markup=options_kb,
            parse_mode=ParseMode.HTML
        )
        
    except Exception as e:
        logger.error(f"Error generating content: {e}")
        await callback.message.answer(
            f"❌ <b>حدث خطأ أثناء التوليد:</b>\n\n<code>{str(e)[:200]}</code>\n\n"
            "🔧 جرب مرة أخرى أو اختر خيارات مختلفة.",
            parse_mode=ParseMode.HTML
        )
    
    await state.clear()
    await callback.answer()

def create_prompt(product: str, audience: str, content_type: str, dialect: str, tone: str, length: str) -> str:
    """إنشاء prompt للتوليد"""
    
    # تحديد نوع المحتوى
    content_type_map = {
        "ads": "إعلان مبيعات",
        "social": "منشور للسوشيال ميديا",
        "captions": "كابشن للصورة",
        "email": "بريد إلكتروني تسويقي",
        "blog": "مقالة مدونة",
        "video": "نص فيديو"
    }
    
    # تحديد اللهجة
    dialect_map = {
        "saudi": "اللهجة السعودية الأصيلة",
        "egyptian": "اللهجة المصرية الشعبية",
        "emirati": "اللهجة الإماراتية الفخمة",
        "classic": "اللغة العربية الفصحى",
        "gulf": "اللهجة الخليجية العامة"
    }
    
    # تحديد النبرة
    tone_map = {
        "enthusiastic": "نبرة حماسية ومحفزة",
        "professional": "نبرة احترافية ورسمية",
        "friendly": "نبرة ودية ومرحة",
        "persuasive": "نبرة إقناعية ومؤثرة",
        "luxury": "نبرة فاخرة ومتميزة",
        "funny": "نبرة فكاهية ومرحة"
    }
    
    # تحديد الطول
    length_map = {
        "short": "مختصر جداً (1-2 جمل فقط)",
        "medium": "متوسط الطول (3-5 جمل)",
        "long": "مفصل (6 جمل أو أكثر)"
    }
    
    prompt = f"""
أكتب {content_type_map.get(content_type, 'محتوى')} عن "{product}" موجه لـ "{audience}".

المتطلبات:
1. اللهجة: {dialect_map.get(dialect, 'سعودي')}
2. النبرة: {tone_map.get(tone, 'حماسي')}
3. الطول: {length_map.get(length, 'متوسط')}
4. أضف إيموجي مناسب
5. أضف هاشتاقات ذات صلة
6. أكتب 3 نسخ مختلفة من المحتوى

ابدأ الكتابة مباشرة دون أي مقدمات.
"""
    
    return prompt

def generate_static_content(product: str, audience: str, content_type: str, dialect: str, tone: str, length: str) -> str:
    """توليد محتوى ثابت إذا فشل التوليد بالذكاء الاصطناعي"""
    
    templates = {
        "ads": [
            f"🔥 {product} الجديد وصل!\n\n🎯 مثالي لـ {audience}\n\n✨ مميزات فريدة\n🛒 اطلب الآن\n#{product.replace(' ', '_')}",
            f"🎁 عرض خاص على {product}\n\n👥 مخصص لـ {audience}\n\n⭐ جودة عالية\n💯 ضمان رضا\n🛒 اضغط للطلب\n#{product.replace(' ', '_')}",
            f"🚀 {product} الأفضل في السوق\n\n🎯 صنع خصيصاً لـ {audience}\n\n🏆 منتج حصري\n⚡ شحن سريع\n🛒 توفر محدود\n#{product.replace(' ', '_')}"
        ],
        "social": [
            f"📱 {product} يستحق التجربة!\n\n👥 يناسب {audience}\n\n❤️ احكموا بأنفسكم\n👇 جربوه وأخبروني\n#{product.replace(' ', '_')}",
            f"🌟 اكتشف {product}\n\n🎯 مصمم لـ {audience}\n\n💬 شاركونا آرائكم\n📸 صوروا المنتج\n#{product.replace(' ', '_')}",
            f"✨ {product} غير حياتي!\n\n👥 أنصح به لـ {audience}\n\n💎 جودة لا تقارن\n🔥 فرصة لا تعوض\n#{product.replace(' ', '_')}"
        ]
    }
    
    content = templates.get(content_type, templates["ads"])
    
    result = f"""
✅ <b>المحتوى المولد:</b>

<b>1.</b> {content[0]}

<b>2.</b> {content[1]}

<b>3.</b> {content[2]}

📊 <b>التفاصيل:</b>
• المنتج: {product}
• الجمهور: {audience}
• النوع: {CONTENT_TYPES.get(content_type, 'إعلان')}
• اللهجة: {DIALECTS.get(dialect, 'سعودي')}
• النبرة: {TONES.get(tone, 'حماسي')}

💡 <i>لنتائج أفضل، أضف مفتاح Groq API</i>
"""
    
    return result

# ==================== ADDITIONAL HANDLERS ====================
@dp.callback_query(F.data == "templates")
async def templates_handler(callback: CallbackQuery):
    """عرض القوالب الجاهزة"""
    
    templates_kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🛍️ إعلان منتج", callback_data="template_product")],
        [InlineKeyboardButton(text="🎓 إعلان دورة", callback_data="template_course")],
        [InlineKeyboardButton(text="🍽️ إعلان مطعم", callback_data="template_restaurant")],
        [InlineKeyboardButton(text="👗 إعلان أزياء", callback_data="template_fashion")],
        [InlineKeyboardButton(text="📱 إعلان تطبيق", callback_data="template_app")],
        [InlineKeyboardButton(text="↩️ رجوع", callback_data="back_to_main")]
    ])
    
    await callback.message.answer(
        "📚 <b>اختر من القوالب الجاهزة:</b>",
        reply_markup=templates_kb,
        parse_mode=ParseMode.HTML
    )
    await callback.answer()

@dp.callback_query(F.data == "back_to_main")
async def back_to_main_handler(callback: CallbackQuery, state: FSMContext):
    """العودة للقائمة الرئيسية"""
    await state.clear()
    await callback.message.answer(
        "🏠 <b>القائمة الرئيسية</b>",
      
