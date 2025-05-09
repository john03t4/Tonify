import time
import telebot
import os
import json
from telebot import types
from telebot.types import ReplyKeyboardMarkup, KeyboardButton

# --- Load Config ---
CONFIG_FILE = "config.json"
if not os.path.exists(CONFIG_FILE):
    raise FileNotFoundError(f"{CONFIG_FILE} not found. Please create it with your bot token.")

with open(CONFIG_FILE, "r") as f:
    config = json.load(f)

TOKEN = config.get("TOKEN")
if not TOKEN:
    raise ValueError("TOKEN not found in config.json.")

bot = telebot.TeleBot(TOKEN)

# --- Constants ---
ADMIN_IDS = [7694475176]
REFERRAL_REWARD = 0.005
DAILY_BONUS = 0.002
MIN_WITHDRAW = 0.01
MAX_WITHDRAW = 0.1
REQUIRED_CHANNELS = {
    "@moneyflowg18", "@primerefgroup", "@moneyflowo18", "@primerefchannel",
    "@xrefchannelx", "@xrefchannel", "@paymentchannel5"
}
PAYMENT_CHANNEL = "@paymentchannel5"
WITHDRAWAL_OPEN = True

# --- Database File ---
DB_FILE = "users.json"
if not os.path.exists(DB_FILE):
    with open(DB_FILE, "w") as f:
        json.dump({}, f)

# --- Database Functions ---
def load_users():
    if not os.path.exists(DB_FILE):
        return {}
    with open(DB_FILE, "r") as f:
        try:
            data = json.load(f)
            return data
        except json.JSONDecodeError:
            return {}

def save_users(data):
    temp_file = "users_temp.json"
    with open(temp_file, "w") as f:
        json.dump(data, f, indent=4)
    os.replace(temp_file, DB_FILE)

# --- Helper Functions ---
def is_verified(user_id):
    users = load_users()
    return users.get(str(user_id), {}).get("verified", False)

def create_user(user_id):
    users = load_users()
    if str(user_id) not in users:
        users[str(user_id)] = {
            "balance": 0.0,
            "referred": 0,
            "wallet": None,
            "verified": False,
            "last_bonus": 0,
            "referrer": None
        }
        save_users(users)

def check_channels(user_id):
    try:
        for channel in REQUIRED_CHANNELS:
            chat_member = bot.get_chat_member(channel, user_id)
            if chat_member.status not in ['member', 'administrator', 'creator']:
                return False
        return True
    except Exception as e:
        print(f"Error checking channels for {user_id}: {e}")
        return False

def set_verified(user_id):
    users = load_users()
    if str(user_id) in users:
        users[str(user_id)]["verified"] = True
        save_users(users)

def main_menu(user_id):
    markup = ReplyKeyboardMarkup(resize_keyboard=True)
    markup.row(KeyboardButton("🪙 Balance"), KeyboardButton("🤜 Invite"))
    markup.row(KeyboardButton("🏱 Bonus"), KeyboardButton("💸 Withdraw"))
    markup.row(KeyboardButton("📝 Add Wallet"))
    if user_id in ADMIN_IDS:
        markup.row(KeyboardButton("🪠 Admin Panel"))
    return markup

# --- Command Handlers ---
@bot.message_handler(commands=['start'])
def start(message):
    user_id = message.from_user.id
    args = message.text.split()

    create_user(user_id)
    users = load_users()

    if len(args) > 1:
        ref_id = args[1]
        if ref_id != str(user_id) and ref_id in users:
            users[str(user_id)]["referrer"] = ref_id
            save_users(users)

    if is_verified(user_id):
        bot.send_message(user_id, "🏡 Welcome back!", reply_markup=main_menu(user_id))
    else:
        ask_verification(user_id)

def ask_verification(user_id):
    text = "🚪 Please join the channels:\n\n"
    for ch in REQUIRED_CHANNELS:
        text += f"🔹 {ch}\n"
    text += "\n✅ After joining, press /verify"
    bot.send_message(user_id, text)

@bot.message_handler(commands=['verify'])
def verify(message):
    user_id = message.from_user.id
    create_user(user_id)
    users = load_users()

    if is_verified(user_id):
        bot.send_message(user_id, "✅ Already verified!", reply_markup=main_menu(user_id))
        return

    if check_channels(user_id):
        set_verified(user_id)

        # Handle referral reward
        referrer_id = users[str(user_id)].get("referrer")
        if referrer_id and referrer_id in users and users[referrer_id].get("verified", False):
            users[referrer_id]["balance"] += REFERRAL_REWARD
            users[referrer_id]["referred"] += 1
            save_users(users)
            try:
                bot.send_message(int(referrer_id),
                                 f"🎉 Your referral verified!\nYou earned {REFERRAL_REWARD:.4f} TON.")
            except Exception as e:
                print(f"Failed to notify referrer {referrer_id}: {e}")

        bot.send_message(user_id, "🎉 Verification successful!", reply_markup=main_menu(user_id))
    else:
        ask_verification(user_id)

@bot.message_handler(func=lambda message: message.text == "🪙 Balance")
def balance(message):
    user_id = message.from_user.id
    users = load_users()
    user = users.get(str(user_id), {})
    bal = user.get("balance", 0.0)
    wallet = user.get("wallet", "Not Set")
    bot.send_message(user_id, f"💰 Balance: {bal:.4f} TON\n🏦 Wallet: {wallet}")

@bot.message_handler(func=lambda message: message.text == "🤜 Invite")
def invite(message):
    user_id = message.from_user.id
    users = load_users()
    referred = users.get(str(user_id), {}).get("referred", 0)
    link = f"https://t.me/{bot.get_me().username}?start={user_id}"
    bot.send_message(user_id, f"👥 Referred Users: {referred}\n\n🔗 Invite Link:\n{link}")

@bot.message_handler(func=lambda message: message.text == "🏱 Bonus")
def bonus(message):
    user_id = message.from_user.id
    users = load_users()

    # Ensure the user exists in the database
    if str(user_id) not in users:
        create_user(user_id)  # Initialize user if not found

    now = int(time.time())
    last_bonus = users.get(str(user_id), {}).get("last_bonus", 0)

    if now - last_bonus >= 86400:  # 86400 seconds = 24 hours
        users[str(user_id)]["balance"] += DAILY_BONUS
        users[str(user_id)]["last_bonus"] = now
        save_users(users)
        bot.send_message(user_id, f"✅ {DAILY_BONUS} TON bonus claimed!")
    else:
        remaining_time = 86400 - (now - last_bonus)
        hours = remaining_time // 3600
        minutes = (remaining_time % 3600) // 60
        bot.send_message(user_id, f"⏳ You can claim your bonus again in {hours}h {minutes}m.")


@bot.message_handler(func=lambda message: message.text == "📝 Add Wallet")
def add_wallet(message):
    msg = bot.send_message(message.chat.id, "✍️ Send your TON wallet address:")
    bot.register_next_step_handler(msg, save_wallet)

def save_wallet(message):
    user_id = message.from_user.id
    wallet = message.text.strip()
    users = load_users()
    users[str(user_id)]["wallet"] = wallet
    save_users(users)
    bot.send_message(user_id, f"✅ Wallet saved: {wallet}")

# Withdraw Handler
@bot.message_handler(func=lambda message: message.text == "💸 Withdraw")
def withdraw(message):
    user_id = message.from_user.id

    if not WITHDRAWAL_OPEN:
        bot.send_message(user_id, "⚠️ Withdrawals are closed.")
        return

    users = load_users()
    balance = users.get(str(user_id), {}).get("balance", 0.0)

    if balance < MIN_WITHDRAW:
        bot.send_message(user_id, f"⚠️ Minimum withdraw: {MIN_WITHDRAW} TON.")
        return

    msg = bot.send_message(user_id, "💸 Enter withdrawal amount:")
    bot.register_next_step_handler(msg, process_withdrawal, balance)

def process_withdrawal(message, available_balance):
    user_id = message.from_user.id
    try:
        requested_amount = float(message.text.strip())
    except ValueError:
        bot.send_message(user_id, "⚠️ Invalid number.")
        return

    if requested_amount < MIN_WITHDRAW:
        bot.send_message(user_id, f"⚠️ Minimum {MIN_WITHDRAW} TON.")
    elif requested_amount > MAX_WITHDRAW:
        bot.send_message(user_id, f"⚠️ Maximum {MAX_WITHDRAW} TON.")
    elif requested_amount > available_balance:
        bot.send_message(user_id, f"⚠️ Insufficient balance.")
    else:
        users = load_users()
        wallet = users.get(str(user_id), {}).get("wallet")
        if not wallet:
            bot.send_message(user_id, "⚠️ Set your wallet first.")
            return

        withdrawal_message = (f"🚨 New Withdraw Request:\n"
                              f"User: {user_id}\n"
                              f"Wallet: {wallet}\n"
                              f"Amount: {requested_amount:.4f} TON")
        bot.send_message(PAYMENT_CHANNEL, withdrawal_message)

        users[str(user_id)]["balance"] -= requested_amount
        save_users(users)

        bot.send_message(user_id, f"✅ Withdraw request of {requested_amount:.4f} TON sent!")

# Admin Panel and Broadcast Handlers
@bot.message_handler(func=lambda message: message.text == "🪠 Admin Panel")
def admin_panel(message):
    user_id = message.from_user.id
    if user_id not in ADMIN_IDS:
        return
    users = load_users()
    markup = ReplyKeyboardMarkup(resize_keyboard=True)
    markup.row(KeyboardButton("🔓 Open Withdrawal"),
               KeyboardButton("🔒 Close Withdrawal"))
    markup.row(KeyboardButton("📢 Broadcast Message"))
    bot.send_message(user_id, f"Admin Panel:\nTotal Users: {len(users)}", reply_markup=markup)

@bot.message_handler(func=lambda message: message.text == "📢 Broadcast Message")
def ask_broadcast_message(message):
    user_id = message.from_user.id
    if user_id not in ADMIN_IDS:
        return
    msg = bot.send_message(user_id, "✉️ Please enter the broadcast message to send to all users:")
    bot.register_next_step_handler(msg, send_broadcast_message)

def send_broadcast_message(message):
    user_id = message.from_user.id
    if user_id not in ADMIN_IDS:
        return

    broadcast_text = message.text.strip()
    users = load_users()
    success = 0
    fail = 0

    for uid in users.keys():
        try:
            bot.send_message(int(uid), f"📢 Admin Announcement:\n\n{broadcast_text}")
            success += 1
            time.sleep(0.05)  # avoid hitting flood limits
        except Exception as e:
            print(f"Failed to send to {uid}: {e}")
            fail += 1

    bot.send_message(user_id, f"✅ Broadcast sent!\nDelivered: {success}, Failed: {fail}")

# Open/Close Withdrawal Handlers
@bot.message_handler(func=lambda message: message.text in ["🔓 Open Withdrawal", "🔒 Close Withdrawal"])
def toggle_withdrawal(message):
    global WITHDRAWAL_OPEN

    user_id = message.from_user.id
    if user_id not in ADMIN_IDS:
        return

    if message.text == "🔓 Open Withdrawal":
        WITHDRAWAL_OPEN = True
        bot.send_message(user_id, "✅ Withdrawal portal opened.")
    else:
        WITHDRAWAL_OPEN = False
        bot.send_message(user_id, "❌ Withdrawal portal closed.")

    bot.send_message(user_id, "🏠 Returning to Main Menu...", reply_markup=main_menu(user_id))


# --- Run Bot ---
print("Bot is running...")
# Use long polling with timeout and allowed_updates parameters to avoid conflicts
bot.polling(timeout=60, long_polling_timeout=60, allowed_updates=["message", "callback_query"])
