"""
📱 Quick QR Fast Bot - Professional QR Code Generator & Scanner
Generate QR codes for text, URLs, WiFi, vCard, and more!
Scan and decode QR codes from images
"""

import os
import io
import re
import json
import logging
import base64
import tempfile
from datetime import datetime
from typing import Dict, List, Optional, Tuple
from urllib.parse import urlparse

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ContextTypes,
    filters
)

# QR Code libraries
try:
    import qrcode
    from qrcode.image.styledpil import StyledPilImage
    from qrcode.image.styles.moduledrawers import RoundedModuleDrawer, SquareModuleDrawer, CircleModuleDrawer
    from qrcode.image.styles.colormasks import SolidFillColorMask
    QR_AVAILABLE = True
except ImportError:
    QR_AVAILABLE = False
    print("⚠️ qrcode not installed. QR generation disabled.")

try:
    from pyzbar.pyzbar import decode
    from PIL import Image
    SCAN_AVAILABLE = True
except ImportError:
    SCAN_AVAILABLE = False
    print("⚠️ pyzbar not installed. QR scanning disabled.")

# ==================== LOGGING ====================

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# ==================== CONFIGURATION ====================

# Try multiple possible token variable names
BOT_TOKEN = (
    os.environ.get("TELEGRAM_TOKEN") or
    os.environ.get("TELEGRAM_BOT_TOKEN") or
    os.environ.get("BOT_TOKEN")
)

# If token is not set, try reading from .env file
if not BOT_TOKEN:
    try:
        from dotenv import load_dotenv
        load_dotenv()
        BOT_TOKEN = (
            os.environ.get("TELEGRAM_TOKEN") or
            os.environ.get("TELEGRAM_BOT_TOKEN") or
            os.environ.get("BOT_TOKEN")
        )
    except:
        pass

# If still no token, show error
if not BOT_TOKEN:
    logger.error("=" * 60)
    logger.error("❌ ERROR: No Telegram Bot Token found!")
    logger.error("=" * 60)
    raise ValueError("❌ No Telegram Bot Token found in environment variables!")

BOT_NAME = "Quick QR Fast Bot"
BOT_USERNAME = "quick_qr_fast_bot"
BOT_VERSION = "1.0.0"

# ==================== USER DATA ====================

user_data: Dict[int, Dict] = {}

def get_user_data(user_id: int) -> Dict:
    """Get or create user data"""
    if user_id not in user_data:
        user_data[user_id] = {
            "history": [],
            "total_generated": 0,
            "total_scanned": 0,
            "settings": {
                "size": 10,
                "color": "#000000",
                "bg_color": "#FFFFFF",
                "module_drawer": "square",
                "border": 4,
            },
            "last_qr": None,
            "last_type": None,
        }
    return user_data[user_id]

# ==================== KEYBOARDS ====================

def get_main_keyboard():
    """Create main menu keyboard"""
    keyboard = [
        [InlineKeyboardButton("📝 Text QR", callback_data="text_qr")],
        [InlineKeyboardButton("🔗 URL QR", callback_data="url_qr")],
        [InlineKeyboardButton("📶 WiFi QR", callback_data="wifi_qr")],
        [InlineKeyboardButton("👤 vCard QR", callback_data="vcard_qr")],
        [InlineKeyboardButton("📍 Geo QR", callback_data="geo_qr")],
        [InlineKeyboardButton("📧 Email QR", callback_data="email_qr")],
        [InlineKeyboardButton("📱 Phone QR", callback_data="phone_qr")],
        [InlineKeyboardButton("🔍 Scan QR", callback_data="scan_qr")],
        [InlineKeyboardButton("⚙️ Settings", callback_data="settings")],
        [InlineKeyboardButton("📊 My Stats", callback_data="stats")],
        [InlineKeyboardButton("❓ Help", callback_data="help")]
    ]
    return InlineKeyboardMarkup(keyboard)

def get_color_keyboard():
    """Create color selection keyboard"""
    keyboard = [
        [InlineKeyboardButton("⚫ Black", callback_data="color_#000000"),
         InlineKeyboardButton("🔴 Red", callback_data="color_#FF0000")],
        [InlineKeyboardButton("🔵 Blue", callback_data="color_#0000FF"),
         InlineKeyboardButton("🟢 Green", callback_data="color_#00FF00")],
        [InlineKeyboardButton("🟡 Yellow", callback_data="color_#FFFF00"),
         InlineKeyboardButton("🟣 Purple", callback_data="color_#800080")],
        [InlineKeyboardButton("🟠 Orange", callback_data="color_#FFA500"),
         InlineKeyboardButton("🩷 Pink", callback_data="color_#FF69B4")],
        [InlineKeyboardButton("🔙 Back", callback_data="back")]
    ]
    return InlineKeyboardMarkup(keyboard)

def get_size_keyboard():
    """Create size selection keyboard"""
    keyboard = [
        [InlineKeyboardButton("🟦 Small", callback_data="size_5"),
         InlineKeyboardButton("🟧 Medium", callback_data="size_10")],
        [InlineKeyboardButton("🟩 Large", callback_data="size_15"),
         InlineKeyboardButton("🟪 XL", callback_data="size_20")],
        [InlineKeyboardButton("🔙 Back", callback_data="back")]
    ]
    return InlineKeyboardMarkup(keyboard)

def get_module_style_keyboard():
    """Create module style selection keyboard"""
    keyboard = [
        [InlineKeyboardButton("⬜ Square", callback_data="style_square")],
        [InlineKeyboardButton("⬤ Circle", callback_data="style_circle")],
        [InlineKeyboardButton("🔲 Rounded", callback_data="style_rounded")],
        [InlineKeyboardButton("🔙 Back", callback_data="back")]
    ]
    return InlineKeyboardMarkup(keyboard)

# ==================== QR CODE FUNCTIONS ====================

def generate_qr_code(
    data: str,
    size: int = 10,
    color: str = "#000000",
    bg_color: str = "#FFFFFF",
    module_style: str = "square",
    border: int = 4
) -> Optional[bytes]:
    """
    Generate a QR code with customization
    Returns: image bytes or None
    """
    if not QR_AVAILABLE:
        return None
    
    try:
        # Create QR code instance
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_H,
            box_size=size,
            border=border,
        )
        qr.add_data(data)
        qr.make(fit=True)
        
        # Select module drawer
        drawer_map = {
            "square": SquareModuleDrawer(),
            "circle": CircleModuleDrawer(),
            "rounded": RoundedModuleDrawer(),
        }
        module_drawer = drawer_map.get(module_style, SquareModuleDrawer())
        
        # Create image
        img = qr.make_image(
            image_factory=StyledPilImage,
            module_drawer=module_drawer,
            color_mask=SolidFillColorMask(
                back_color=bg_color,
                front_color=color
            )
        )
        
        # Save to bytes
        img_bytes = io.BytesIO()
        img.save(img_bytes, format='PNG')
        img_bytes.seek(0)
        return img_bytes.getvalue()
        
    except Exception as e:
        logger.error(f"QR generation error: {e}")
        return None

def scan_qr_code(image_data: bytes) -> List[Dict]:
    """
    Scan QR code from image
    Returns: list of decoded data
    """
    if not SCAN_AVAILABLE:
        return []
    
    try:
        # Open image
        img = Image.open(io.BytesIO(image_data))
        
        # Decode QR code
        decoded_objects = decode(img)
        
        results = []
        for obj in decoded_objects:
            results.append({
                "data": obj.data.decode('utf-8'),
                "type": obj.type,
                "rect": {
                    "x": obj.rect.left,
                    "y": obj.rect.top,
                    "width": obj.rect.width,
                    "height": obj.rect.height
                }
            })
        
        return results
        
    except Exception as e:
        logger.error(f"QR scan error: {e}")
        return []

def detect_qr_type(data: str) -> str:
    """Detect QR type from decoded data"""
    if data.startswith("WIFI:"):
        return "wifi"
    elif data.startswith("BEGIN:VCARD"):
        return "vcard"
    elif data.startswith("geo:"):
        return "geo"
    elif data.startswith("mailto:"):
        return "email"
    elif data.startswith("tel:"):
        return "phone"
    elif data.startswith("http://") or data.startswith("https://"):
        return "url"
    else:
        return "text"

# ==================== COMMAND HANDLERS ====================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /start command"""
    user = update.effective_user
    user_id = str(user.id)
    data = get_user_data(user_id)
    
    welcome = (
        f"📱 **Welcome to {BOT_NAME}!**\n\n"
        f"👋 Hello @{user.username or user.first_name}!\n\n"
        f"Your **fast** QR Code generator and scanner.\n\n"
        f"⚡ **Features:**\n"
        f"• 📝 Generate QR from text\n"
        f"• 🔗 Generate QR from URLs\n"
        f"• 📶 Generate WiFi login QR\n"
        f"• 👤 Generate vCard QR\n"
        f"• 📍 Generate location QR\n"
        f"• 📧 Generate email QR\n"
        f"• 📱 Generate phone QR\n"
        f"• 🔍 Scan QR codes from images\n"
        f"• 🎨 Customize colors & styles\n"
        f"• 📊 Usage statistics\n\n"
        f"📊 **Your Stats:**\n"
        f"• QR generated: {data['total_generated']}\n"
        f"• QR scanned: {data['total_scanned']}\n\n"
        f"⬇️ Use the buttons below to get started!"
    )
    
    await update.message.reply_text(
        welcome,
        parse_mode="Markdown",
        reply_markup=get_main_keyboard()
    )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /help command"""
    help_text = (
        f"📖 **{BOT_NAME} User Guide**\n\n"
        "**📝 Generate QR Codes:**\n"
        "• Text QR - Any text message\n"
        "• URL QR - Website links\n"
        "• WiFi QR - WiFi credentials\n"
        "• vCard QR - Contact cards\n"
        "• Geo QR - Locations\n"
        "• Email QR - Email addresses\n"
        "• Phone QR - Phone numbers\n\n"
        "**🔍 Scan QR Codes:**\n"
        "• Send any image with QR code\n"
        "• I'll decode and show data\n\n"
        "**🎨 Customize:**\n"
        "• Change colors\n"
        "• Change size\n"
        "• Change module style\n\n"
        "**📌 Commands:**\n"
        "/start - Main menu\n"
        "/help - This help\n"
        "/stats - Your statistics"
    )
    
    await update.message.reply_text(
        help_text,
        parse_mode="Markdown",
        reply_markup=get_main_keyboard()
    )

async def stats_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /stats command"""
    user_id = str(update.effective_user.id)
    data = get_user_data(user_id)
    
    stats_text = (
        f"📊 **Your Statistics**\n\n"
        f"📱 QR Generated: {data['total_generated']}\n"
        f"🔍 QR Scanned: {data['total_scanned']}\n"
        f"🎨 Color: {data['settings']['color']}\n"
        f"📐 Size: {data['settings']['size']}\n"
        f"📏 Style: {data['settings']['module_drawer']}\n"
        f"📅 Account active since: {datetime.now().strftime('%Y-%m-%d')}\n\n"
        f"🔢 QR Types:\n"
    )
    
    # Count QR types
    qr_types = {}
    for entry in data.get("history", []):
        qr_type = entry.get("type", "unknown")
        qr_types[qr_type] = qr_types.get(qr_type, 0) + 1
    
    for qr_type, count in qr_types.items():
        stats_text += f"• {qr_type}: {count}\n"
    
    await update.message.reply_text(
        stats_text,
        parse_mode="Markdown",
        reply_markup=get_main_keyboard()
    )

# ==================== CALLBACK HANDLERS ====================

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle inline button presses"""
    query = update.callback_query
    await query.answer()
    
    user_id = str(update.effective_user.id)
    data = get_user_data(user_id)
    action = query.data
    
    # ===== MAIN ACTIONS =====
    
    if action == "text_qr":
        await query.edit_message_text(
            "📝 **Text QR Code**\n\n"
            "Send me any text to convert to QR code!\n\n"
            "Examples:\n"
            "• Hello World\n"
            "• Your message here\n\n"
            "Send /cancel to cancel.",
            parse_mode="Markdown",
            reply_markup=get_main_keyboard()
        )
        context.user_data["qr_type"] = "text"
        context.user_data["action"] = "qr_data"
        
    elif action == "url_qr":
        await query.edit_message_text(
            "🔗 **URL QR Code**\n\n"
            "Send me a URL to convert to QR code!\n\n"
            "Examples:\n"
            "• https://t.me\n"
            "• https://example.com\n\n"
            "Send /cancel to cancel.",
            parse_mode="Markdown",
            reply_markup=get_main_keyboard()
        )
        context.user_data["qr_type"] = "url"
        context.user_data["action"] = "qr_data"
        
    elif action == "wifi_qr":
        await query.edit_message_text(
            "📶 **WiFi QR Code**\n\n"
            "Send me WiFi details in this format:\n"
            "`SSID:YourWiFiName, Password:YourPassword, Security:WPA2`\n\n"
            "Example:\n"
            "`SSID:HomeWiFi, Password:12345678, Security:WPA2`\n\n"
            "Send /cancel to cancel.",
            parse_mode="Markdown",
            reply_markup=get_main_keyboard()
        )
        context.user_data["qr_type"] = "wifi"
        context.user_data["action"] = "qr_data"
        
    elif action == "vcard_qr":
        await query.edit_message_text(
            "👤 **vCard QR Code**\n\n"
            "Send me contact details in this format:\n"
            "`Name:John Doe, Phone:+1234567890, Email:john@example.com, Company:Acme Inc`\n\n"
            "Send /cancel to cancel.",
            parse_mode="Markdown",
            reply_markup=get_main_keyboard()
        )
        context.user_data["qr_type"] = "vcard"
        context.user_data["action"] = "qr_data"
        
    elif action == "geo_qr":
        await query.edit_message_text(
            "📍 **Location QR Code**\n\n"
            "Send me coordinates in this format:\n"
            "`latitude,longitude`\n\n"
            "Example:\n"
            "`40.7128,-74.0060` (New York)\n\n"
            "Send /cancel to cancel.",
            parse_mode="Markdown",
            reply_markup=get_main_keyboard()
        )
        context.user_data["qr_type"] = "geo"
        context.user_data["action"] = "qr_data"
        
    elif action == "email_qr":
        await query.edit_message_text(
            "📧 **Email QR Code**\n\n"
            "Send me an email address:\n"
            "`email@example.com`\n\n"
            "Send /cancel to cancel.",
            parse_mode="Markdown",
            reply_markup=get_main_keyboard()
        )
        context.user_data["qr_type"] = "email"
        context.user_data["action"] = "qr_data"
        
    elif action == "phone_qr":
        await query.edit_message_text(
            "📱 **Phone QR Code**\n\n"
            "Send me a phone number:\n"
            "`+1234567890`\n\n"
            "Send /cancel to cancel.",
            parse_mode="Markdown",
            reply_markup=get_main_keyboard()
        )
        context.user_data["qr_type"] = "phone"
        context.user_data["action"] = "qr_data"
        
    elif action == "scan_qr":
        await query.edit_message_text(
            "🔍 **Scan QR Code**\n\n"
            "Send me an image containing a QR code!\n\n"
            "Supported formats:\n"
            "• JPG\n"
            "• PNG\n"
            "• WEBP\n\n"
            "I'll decode and show you the data.",
            parse_mode="Markdown",
            reply_markup=get_main_keyboard()
        )
        context.user_data["action"] = "scan_qr"
        
    elif action == "settings":
        settings = data.get("settings", {})
        settings_text = (
            f"⚙️ **Settings**\n\n"
            f"🎨 Color: {settings.get('color', '#000000')}\n"
            f"📐 Size: {settings.get('size', 10)}\n"
            f"📏 Style: {settings.get('module_drawer', 'square')}\n"
            f"📦 Border: {settings.get('border', 4)}\n\n"
            "Select what to customize:"
        )
        await query.edit_message_text(
            settings_text,
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🎨 Change Color", callback_data="change_color")],
                [InlineKeyboardButton("📐 Change Size", callback_data="change_size")],
                [InlineKeyboardButton("📏 Change Style", callback_data="change_style")],
                [InlineKeyboardButton("🔄 Reset Settings", callback_data="reset_settings")],
                [InlineKeyboardButton("🔙 Back", callback_data="back")]
            ])
        )
        
    elif action == "stats":
        stats_text = (
            f"📊 **Your Statistics**\n\n"
            f"📱 QR Generated: {data['total_generated']}\n"
            f"🔍 QR Scanned: {data['total_scanned']}\n"
            f"🎨 Color: {data['settings']['color']}\n"
            f"📐 Size: {data['settings']['size']}\n"
            f"📏 Style: {data['settings']['module_drawer']}\n"
            f"📅 Account active since: {datetime.now().strftime('%Y-%m-%d')}"
        )
        await query.edit_message_text(
            stats_text,
            parse_mode="Markdown",
            reply_markup=get_main_keyboard()
        )
        
    elif action == "help":
        await help_command(update, context)
        
    elif action == "back":
        await query.edit_message_text(
            "🏠 **Main Menu**\n\n"
            "What would you like to do?",
            parse_mode="Markdown",
            reply_markup=get_main_keyboard()
        )
        context.user_data["action"] = None
        
    # ===== SETTINGS =====
    
    elif action == "change_color":
        await query.edit_message_text(
            "🎨 **Select QR Color**\n\n"
            "Choose the foreground color for your QR code:",
            parse_mode="Markdown",
            reply_markup=get_color_keyboard()
        )
        
    elif action == "change_size":
        await query.edit_message_text(
            "📐 **Select QR Size**\n\n"
            "Choose the size for your QR code:",
            parse_mode="Markdown",
            reply_markup=get_size_keyboard()
        )
        
    elif action == "change_style":
        await query.edit_message_text(
            "📏 **Select Module Style**\n\n"
            "Choose the style for QR code modules:",
            parse_mode="Markdown",
            reply_markup=get_module_style_keyboard()
        )
        
    elif action == "reset_settings":
        data["settings"] = {
            "size": 10,
            "color": "#000000",
            "bg_color": "#FFFFFF",
            "module_drawer": "square",
            "border": 4,
        }
        await query.edit_message_text(
            "✅ **Settings Reset!**\n\n"
            "All settings have been reset to default.",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🔙 Back", callback_data="back")]
            ])
        )
        
    # ===== COLOR SELECTION =====
    
    elif action.startswith("color_"):
        color = action.replace("color_", "")
        data["settings"]["color"] = color
        await query.edit_message_text(
            f"✅ **Color Updated!**\n\n"
            f"New color: {color}",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🔙 Back", callback_data="settings")]
            ])
        )
        
    # ===== SIZE SELECTION =====
    
    elif action.startswith("size_"):
        size = int(action.replace("size_", ""))
        data["settings"]["size"] = size
        await query.edit_message_text(
            f"✅ **Size Updated!**\n\n"
            f"New size: {size}",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🔙 Back", callback_data="settings")]
            ])
        )
        
    # ===== STYLE SELECTION =====
    
    elif action.startswith("style_"):
        style = action.replace("style_", "")
        data["settings"]["module_drawer"] = style
        await query.edit_message_text(
            f"✅ **Style Updated!**\n\n"
            f"New style: {style}",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🔙 Back", callback_data="settings")]
            ])
        )

# ==================== MESSAGE HANDLERS ====================

async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle text messages for QR generation"""
    user_id = str(update.effective_user.id)
    data = get_user_data(user_id)
    text = update.message.text.strip()
    action = context.user_data.get("action", "")
    qr_type = context.user_data.get("qr_type", "text")
    
    if not text:
        await update.message.reply_text(
            "❌ Please send some text!",
            reply_markup=get_main_keyboard()
        )
        return
    
    # ===== CANCEL =====
    
    if text.lower() == "/cancel":
        context.user_data["action"] = None
        context.user_data["qr_type"] = "text"
        await update.message.reply_text(
            "✅ Cancelled!",
            reply_markup=get_main_keyboard()
        )
        return
    
    # ===== QR DATA =====
    
    if action == "qr_data":
        # Parse data based on type
        formatted_data = text
        
        if qr_type == "wifi":
            # Parse WiFi details
            wifi_match = re.search(r'SSID:([^,]+),?\s*Password:([^,]+),?\s*Security:([^,]+)', text, re.IGNORECASE)
            if wifi_match:
                ssid = wifi_match.group(1).strip()
                password = wifi_match.group(2).strip()
                security = wifi_match.group(3).strip()
                formatted_data = f"WIFI:T:{security};S:{ssid};P:{password};;"
            else:
                await update.message.reply_text(
                    "❌ Invalid WiFi format.\n\n"
                    "Use: `SSID:Name, Password:pass, Security:WPA2`",
                    parse_mode="Markdown"
                )
                return
                
        elif qr_type == "vcard":
            # Parse vCard details
            vcard_match = re.search(r'Name:([^,]+),?\s*Phone:([^,]+),?\s*Email:([^,]+),?\s*Company:([^,]+)', text, re.IGNORECASE)
            if vcard_match:
                name = vcard_match.group(1).strip()
                phone = vcard_match.group(2).strip()
                email = vcard_match.group(3).strip()
                company = vcard_match.group(4).strip()
                formatted_data = f"BEGIN:VCARD\nVERSION:3.0\nFN:{name}\nTEL:{phone}\nEMAIL:{email}\nORG:{company}\nEND:VCARD"
            else:
                await update.message.reply_text(
                    "❌ Invalid vCard format.\n\n"
                    "Use: `Name:John, Phone:123, Email:john@x.com, Company:Acme`",
                    parse_mode="Markdown"
                )
                return
                
        elif qr_type == "geo":
            # Parse coordinates
            geo_match = re.search(r'(-?\d+\.?\d*),\s*(-?\d+\.?\d*)', text)
            if geo_match:
                lat = geo_match.group(1).strip()
                lon = geo_match.group(2).strip()
                formatted_data = f"geo:{lat},{lon}"
            else:
                await update.message.reply_text(
                    "❌ Invalid coordinates.\n\n"
                    "Use: `40.7128,-74.0060`",
                    parse_mode="Markdown"
                )
                return
                
        elif qr_type == "email":
            if '@' in text and '.' in text:
                formatted_data = f"mailto:{text}"
            else:
                await update.message.reply_text(
                    "❌ Invalid email address.\n\n"
                    "Use: `email@example.com`",
                    parse_mode="Markdown"
                )
                return
                
        elif qr_type == "phone":
            if text.startswith('+') or text.isdigit():
                formatted_data = f"tel:{text}"
            else:
                await update.message.reply_text(
                    "❌ Invalid phone number.\n\n"
                    "Use: `+1234567890`",
                    parse_mode="Markdown"
                )
                return
                
        elif qr_type == "url":
            if not text.startswith(('http://', 'https://')):
                text = 'https://' + text
            formatted_data = text
        
        # Generate QR code
        settings = data.get("settings", {})
        size = settings.get("size", 10)
        color = settings.get("color", "#000000")
        bg_color = settings.get("bg_color", "#FFFFFF")
        module_style = settings.get("module_drawer", "square")
        border = settings.get("border", 4)
        
        processing_msg = await update.message.reply_text(
            f"⏳ **Generating QR code...**\n\n"
            f"Type: {qr_type.upper()}",
            parse_mode="Markdown"
        )
        
        img_data = generate_qr_code(
            data=formatted_data,
            size=size,
            color=color,
            bg_color=bg_color,
            module_style=module_style,
            border=border
        )
        
        await processing_msg.delete()
        
        if img_data:
            # Update stats
            data["total_generated"] += 1
            data["history"].append({
                "type": qr_type,
                "data": formatted_data,
                "timestamp": datetime.now().isoformat()
            })
            
            await update.message.reply_photo(
                photo=io.BytesIO(img_data),
                caption=(
                    f"✅ **QR Code Generated!**\n\n"
                    f"📌 Type: {qr_type.upper()}\n"
                    f"📊 Data: {text[:100]}{'...' if len(text) > 100 else ''}\n"
                    f"🎨 Color: {color}\n"
                    f"📐 Size: {size}\n\n"
                    f"🔄 Generate another or use the buttons below!"
                ),
                parse_mode="Markdown",
                reply_markup=get_main_keyboard()
            )
        else:
            await update.message.reply_text(
                "❌ **Failed to generate QR code**\n\n"
                "Please try again with different data.",
                parse_mode="Markdown",
                reply_markup=get_main_keyboard()
            )
        
        context.user_data["action"] = None
        context.user_data["qr_type"] = "text"

# ==================== IMAGE HANDLERS ====================

async def handle_image(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle image messages for QR scanning"""
    user_id = str(update.effective_user.id)
    data = get_user_data(user_id)
    action = context.user_data.get("action", "")
    
    if action != "scan_qr":
        await update.message.reply_text(
            "🔍 **Click 'Scan QR' first!**\n\n"
            "Use the button below to start scanning.",
            parse_mode="Markdown",
            reply_markup=get_main_keyboard()
        )
        return
    
    try:
        # Get the image
        photo = await update.message.photo[-1].get_file()
        image_data = await photo.download_as_bytearray()
        
        processing_msg = await update.message.reply_text(
            "🔍 **Scanning QR code...**\n\n"
            "Please wait...",
            parse_mode="Markdown"
        )
        
        # Scan QR code
        results = scan_qr_code(image_data)
        
        await processing_msg.delete()
        
        if results:
            data["total_scanned"] += 1
            
            for result in results:
                qr_data = result["data"]
                qr_type = detect_qr_type(qr_data)
                
                response = (
                    f"✅ **QR Code Scanned!**\n\n"
                    f"📌 **Data:**\n`{qr_data}`\n\n"
                    f"📊 **Type:** {qr_type.upper()}\n"
                    f"📏 **Position:** ({result['rect']['x']}, {result['rect']['y']})\n"
                    f"📐 **Size:** {result['rect']['width']}x{result['rect']['height']}\n\n"
                    f"💡 You can generate a new QR with this data!"
                )
                
                await update.message.reply_text(
                    response,
                    parse_mode="Markdown",
                    reply_markup=InlineKeyboardMarkup([
                        [InlineKeyboardButton("📝 Generate QR", callback_data="text_qr")],
                        [InlineKeyboardButton("🔙 Back", callback_data="back")]
                    ])
                )
        else:
            await update.message.reply_text(
                "❌ **No QR Code Found**\n\n"
                "Please send a clear image with a QR code.\n\n"
                "Tips:\n"
                "• Make sure QR is visible\n"
                "• Good lighting helps\n"
                "• Try a different angle",
                parse_mode="Markdown",
                reply_markup=get_main_keyboard()
            )
        
        context.user_data["action"] = None
        
    except Exception as e:
        logger.error(f"Scan error: {e}")
        await update.message.reply_text(
            "❌ **Error scanning QR code**\n\n"
            "Please try again with a different image.",
            parse_mode="Markdown",
            reply_markup=get_main_keyboard()
        )

# ==================== MAIN ====================

async def post_init(application):
    """Post initialization"""
    logger.info("=" * 60)
    logger.info(f"📱 {BOT_NAME} Started Successfully!")
    logger.info(f"🤖 Username: @{BOT_USERNAME}")
    logger.info(f"📦 Version: {BOT_VERSION}")
    logger.info(f"✅ QR Generation: {'Enabled' if QR_AVAILABLE else 'Disabled'}")
    logger.info(f"✅ QR Scanning: {'Enabled' if SCAN_AVAILABLE else 'Disabled'}")
    logger.info("=" * 60)
    logger.info("✅ Bot is ready to generate and scan QR codes!")
    logger.info("=" * 60)

def main():
    """Main entry point"""
    logger.info(f"🚀 Starting {BOT_NAME}...")
    logger.info(f"📡 Using token: {BOT_TOKEN[:15]}...{BOT_TOKEN[-5:]}")
    
    if not QR_AVAILABLE:
        logger.warning("⚠️ qrcode not installed! Install with: pip install qrcode[pil]")
    
    if not SCAN_AVAILABLE:
        logger.warning("⚠️ pyzbar not installed! Install with: pip install pyzbar")
    
    application = ApplicationBuilder() \
        .token(BOT_TOKEN) \
        .post_init(post_init) \
        .build()
    
    # Command handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("stats", stats_command))
    
    # Callback handler
    application.add_handler(CallbackQueryHandler(button_handler))
    
    # Message handlers
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
    application.add_handler(MessageHandler(filters.PHOTO, handle_image))
    
    logger.info("✅ Bot is polling for updates...")
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()
