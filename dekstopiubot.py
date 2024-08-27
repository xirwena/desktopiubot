from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes
import firebase_admin
from firebase_admin import credentials, firestore
from dotenv import load_dotenv
import os

# .env dosyasını yükle
load_dotenv()

# Token'ı ve Admin ID'sini çevresel değişkenlerden al
TOKEN = os.getenv("TELEGRAM_TOKEN")
ADMIN_USER_ID = int(os.getenv("ADMIN_USER_ID"))

# Firebase'i başlat
cred = credentials.Certificate("serviceAccountKey.json")  # Bu dosya yolunu kendi yolunuza göre güncelleyin
firebase_admin.initialize_app(cred)
db = firestore.client()

# Başlangıç menüsü
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    keyboard = [
        [InlineKeyboardButton("🟡 Oyunlarını Gör", callback_data='show_games')],
        [InlineKeyboardButton("⚪ Admin Oyunları", callback_data='show_admin_games')],
        [InlineKeyboardButton("🟢 Kendi Oyununu Ekle", callback_data='add_your_own_game')],
        [InlineKeyboardButton("🔴 Oyununu Sil", callback_data='delete_game')],
        [InlineKeyboardButton("📜 Komutlar", callback_data='show_commands')],  # Yeni Komutlar Butonu
        [InlineKeyboardButton("🟣 Yakında", url="https://ornek.com")],
    ]

    reply_markup = InlineKeyboardMarkup(keyboard)

    if update.message:
        await update.message.reply_text(
            '🎉 Bot\'a Hoşgeldiniz!\n\n'
            '🔘 Botun Özellikleri\n\n'
            '🟡 Kendi oyunlarınızı ekleyebilir ve admin tarafından eklenen oyunları görebilirsiniz.',
            reply_markup=reply_markup
        )
    elif update.callback_query:
        await update.callback_query.message.edit_text(
            '🎉 Bot\'a Hoşgeldiniz!\n\n'
            '🔘 Botun Özellikleri\n\n'
            '🟡 Kendi oyunlarınızı ekleyebilir ve admin tarafından eklenen oyunları görebilirsiniz.',
            reply_markup=reply_markup
        )

# İkili sütun şeklinde oyunları göstermek için düzenlenmiş menü
async def show_games(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.callback_query.from_user.id
    games_ref = db.collection('users').document(str(user_id)).collection('games')
    games = games_ref.stream()

    keyboard = []
    row = []
    for idx, game in enumerate(games):
        game_data = game.to_dict()
        row.append(InlineKeyboardButton(game_data['name'], url=game_data['url']))
        if (idx + 1) % 2 == 0:
            keyboard.append(row)
            row = []
    if row:
        keyboard.append(row)

    keyboard.append([InlineKeyboardButton("⬅️ Ana Menüye Dön", callback_data='main_menu')])

    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.callback_query.message.edit_text(
        'Eklediğiniz Oyunlar:',
        reply_markup=reply_markup
    )

# Admin tarafından eklenen oyunları ikili sütun şeklinde gösteren menü
async def show_admin_games(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    games_ref = db.collection('admin_games')
    games = games_ref.stream()

    keyboard = []
    row = []
    for idx, game in enumerate(games):
        game_data = game.to_dict()
        row.append(InlineKeyboardButton(game_data['name'], url=game_data['url']))
        if (idx + 1) % 2 == 0:
            keyboard.append(row)
            row = []
    if row:
        keyboard.append(row)

    keyboard.append([InlineKeyboardButton("⬅️ Ana Menüye Dön", callback_data='main_menu')])

    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.callback_query.message.edit_text(
        'Admin Tarafından Eklenen Oyunlar:',
        reply_markup=reply_markup
    )

# Kullanıcıların oyun eklemesi için /oyunekle komutu
async def add_game(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if len(context.args) < 2:
        await update.message.reply_text("Lütfen şu formatı kullanın: /oyunekle 'oyunismi' 'oyunlinki'")
        return
    
    user_id = update.message.from_user.id
    name = " ".join(context.args[:-1])  # Oyun adı birden fazla kelime olabilir
    url = context.args[-1].strip()  # URL'nin başında veya sonunda gereksiz boşlukları temizle

    # URL'nin geçerli olup olmadığını kontrol et
    if not url.startswith("http://") and not url.startswith("https://"):
        await update.message.reply_text("Geçersiz URL. Lütfen URL'yi 'http://' veya 'https://' ile başlatın.")
        return
    
    # Firestore veritabanına oyun ekleyin, her kullanıcı için ayrı bir belge oluşturulur
    db.collection('users').document(str(user_id)).collection('games').add({
        'name': name,
        'url': url
    })
    
    keyboard = [[InlineKeyboardButton("⬅️ Ana Menüye Dön", callback_data='main_menu')]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(f"✅ '{name}' başarıyla eklendi!", reply_markup=reply_markup)

# Kullanıcıların oyun silmesi için /oyunsil komutu
async def delete_game_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if len(context.args) < 1:
        await update.message.reply_text("Lütfen şu formatı kullanın: /oyunsil 'oyunismi'")
        return
    
    user_id = update.message.from_user.id
    name = " ".join(context.args)  # Oyun adı birden fazla kelime olabilir
    
    games_ref = db.collection('users').document(str(user_id)).collection('games')
    games = games_ref.where('name', '==', name).stream()
    
    found = False
    for game in games:
        game.reference.delete()
        found = True
    
    keyboard = [[InlineKeyboardButton("⬅️ Ana Menüye Dön", callback_data='main_menu')]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    if found:
        await update.message.reply_text(f"🗑️ '{name}' başarıyla silindi!", reply_markup=reply_markup)
    else:
        await update.message.reply_text(f"❌ '{name}' isimli oyun bulunamadı.", reply_markup=reply_markup)

# Admin tarafından oyun ekleme ve silme
async def manage_admin_game(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.message.from_user.id
    if user_id != ADMIN_USER_ID:
        await update.message.reply_text("Bu komutu kullanma yetkiniz yok.")
        return
    
    if len(context.args) < 2:
        await update.message.reply_text("Lütfen şu formatı kullanın: /adminkomut 'ekle/sil' 'oyunismi'")
        return

    action = context.args[0].lower()
    name = " ".join(context.args[1:])  # Oyun adı birden fazla kelime olabilir
    
    keyboard = [[InlineKeyboardButton("⬅️ Ana Menüye Dön", callback_data='main_menu')]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    if action == 'ekle':
        if len(context.args) < 3:
            await update.message.reply_text("Lütfen oyun linkini de belirtin.", reply_markup=reply_markup)
            return
        url = context.args[-1]
        db.collection('admin_games').add({'name': name, 'url': url})
        await update.message.reply_text(f"✅ '{name}' başarıyla admin oyunlarına eklendi!", reply_markup=reply_markup)
    
    elif action == 'sil':
        games_ref = db.collection('admin_games')
        games = games_ref.where('name', '==', name).stream()
        
        found = False
        for game in games:
            game.reference.delete()
            found = True
        
        if found:
            await update.message.reply_text(f"🗑️ '{name}' başarıyla silindi!", reply_markup=reply_markup)
        else:
            await update.message.reply_text(f"❌ '{name}' isimli oyun bulunamadı.", reply_markup=reply_markup)
    else:
        await update.message.reply_text("Geçersiz komut. Lütfen 'ekle' veya 'sil' komutunu kullanın.", reply_markup=reply_markup)

# Kullanıcılara oyun ekleme sürecini anlatan mesaj
async def add_your_own_game(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    message = (
        "🎮 Kendi Oyununu Ekleme Rehberi 🎮\n\n"
        "Botumuza kendi oyunlarınızı ekleyerek menüde görünmesini sağlayabilirsiniz. "
        "Oyun eklemek için aşağıdaki adımları izleyin:\n\n"
        "1. Oyun ismi ve oyun linkini belirleyin.\n"
        "2. /oyunekle komutunu şu formatta kullanın:\n\n"
        "`/oyunekle \"Oyun İsmi\" \"Oyun Linki\"`\n\n"
        "Örneğin:\n"
        "`/oyunekle \"Hamster Kombat\" \"https://hamsterkombat.com\"`\n\n"
        "Bu işlemi yaptıktan sonra, oyunlar menüsünde oyununuzu görebilirsiniz!"
    )
    
    keyboard = [[InlineKeyboardButton("⬅️ Ana Menüye Dön", callback_data='main_menu')]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    if update.callback_query:
        await update.callback_query.message.edit_text(message, parse_mode='Markdown', reply_markup=reply_markup)
    else:
        await update.message.reply_text(message, parse_mode='Markdown', reply_markup=reply_markup)

# Kullanıcılara oyun silme sürecini anlatan mesaj
async def delete_game(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    message = (
        "🗑️ Oyun Silme Rehberi 🗑️\n\n"
        "Eklediğiniz bir oyunu silmek için aşağıdaki adımları izleyin:\n\n"
        "1. Silmek istediğiniz oyunun adını belirleyin.\n"
        "2. /oyunsil komutunu şu formatta kullanın:\n\n"
        "`/oyunsil \"Oyun İsmi\"`\n\n"
        "Örneğin:\n"
        "`/oyunsil \"Hamster Kombat\"`\n\n"
        "Bu işlemi yaptıktan sonra, oyunlar menüsünde bu oyun kaldırılacaktır."
    )
    
    keyboard = [[InlineKeyboardButton("⬅️ Ana Menüye Dön", callback_data='main_menu')]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    if update.callback_query:
        await update.callback_query.message.edit_text(message, parse_mode='Markdown', reply_markup=reply_markup)
    else:
        await update.message.reply_text(message, parse_mode='Markdown', reply_markup=reply_markup)

# Komutlar menüsü
async def show_commands(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    message = (
        "📜 Komutlar Listesi 📜\n\n"
        "1. **/start** - Botu başlatır ve ana menüyü gösterir.\n"
        "2. **/oyunekle** `Oyun İsmi` `Oyun Linki` - Yeni bir oyun ekler.\n"
        "   Örnek: `/oyunekle \"Hamster Kombat\" \"https://hamsterkombat.com\"`\n"
        "3. **/oyunsil** `Oyun İsmi` - Bir oyunu siler.\n"
        "   Örnek: `/oyunsil \"Hamster Kombat\"`\n"
        "4. **/adminkomut** `ekle/sil` `Oyun İsmi` `Oyun Linki` - Admin oyunları yönetir.\n"
        "   Örnek: `/adminkomut ekle \"Super Game\" \"https://supergame.com\"`\n"
    )

    keyboard = [[InlineKeyboardButton("⬅️ Ana Menüye Dön", callback_data='main_menu')]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    if update.callback_query:
        await update.callback_query.message.edit_text(message, parse_mode='Markdown', reply_markup=reply_markup)
    else:
        await update.message.reply_text(message, parse_mode='Markdown', reply_markup=reply_markup)

# Callback query handler
async def button(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()

    if query.data == 'main_menu':
        await start(update, context)
    elif query.data == 'show_games':
        await show_games(update, context)
    elif query.data == 'show_admin_games':
        await show_admin_games(update, context)
    elif query.data == 'add_your_own_game':
        await add_your_own_game(update, context)
    elif query.data == 'delete_game':
        await delete_game(update, context)
    elif query.data == 'show_commands':
        await show_commands(update, context)

def main() -> None:
    application = Application.builder().token(TOKEN).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("oyunekle", add_game))
    application.add_handler(CommandHandler("oyunsil", delete_game_command))
    application.add_handler(CommandHandler("adminkomut", manage_admin_game))  # Admin komutları için
    application.add_handler(CallbackQueryHandler(button))

    application.run_polling()

if __name__ == '__main__':
    main()
