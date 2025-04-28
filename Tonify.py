import time
import telebot
import os
import json
from telebot import types
from telebot.types import ReplyKeyboardMarkup, KeyboardButton
import logging

# --- Bot Config ---
TOKEN = '7818570118:AAE0Nhb50JxpvSc-RVW3txsequwemWRP_Nk'
bot = telebot.TeleBot(TOKEN)

ADMIN_IDS = [7694475176]
REFERRAL_REWARD = 0.0005
DAILY_BONUS = 0.0002
MIN_WITHDRAW = 0.001
MAX_WITHDRAW = 0.01  # Maximum withdraw limit

# --- Example of REQUIRED_CHANNELS dictionary ---
REQUIRED_CHANNELS = {
    "@moneyflowg18",
    "@primerefgroup",
    "@moneyflowo18",
    "@primerefchannel",
    "@xrefchannelx",
    "@xrefchannel",
    "@paymentchannel5"
}

# Define the payment channel where withdrawal requests will be sent
PAYMENT_CHANNEL = "@paymentchannel5"

# Global variable to control withdrawal portal status
WITHDRAWAL_OPEN = True  # Set to False to close the withdrawal portal

# --- Database (using JSON file) ---
if not os.path.exists("users.json"):
    with open("users.json", "w") as f:
        json.dump({}, f)

def load_users():
    if not os.path.exists("users.json"):
        with open("users.json", "w") as f:
            json.dump({}, f)
    
    with open("users.json", "r") as f:
        content = f.read().strip()
        if not content:
            return {}  # If empty file, return empty dict
        return json.loads(content)


def save_users(data):
    with open("users.json", "w") as f:
        json.dump(data, f, indent=4)

# --- Menu Keyboard ---
def main_menu(user_id):
    markup = ReplyKeyboardMarkup(resize_keyboard=True)
    markup.row(KeyboardButton("🪙 Balance"), KeyboardButton("🤜 Invite"))
    markup.row(KeyboardButton("🏱 Bonus"), KeyboardButton("💸 Withdraw"))
    markup.row(KeyboardButton("📝 Add Wallet"))

    # Add Admin Panel button only for admin
    if user_id in ADMIN_IDS:
        markup.row(KeyboardButton("🪠 Admin Panel"))

    return markup


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
	    "referrer": None  # Store the referrer here

        }
        save_users(users)

# --- Start Command ---
# --- Start Command ---
@bot.message_handler(commands=['start'])
def start(message):
    user_id = message.from_user.id
    args = message.text.split()

    users = load_users()

    # If user already exists and is verified
    if str(user_id) in users:
        if is_verified(user_id):
            bot.send_message(user_id, "🏡 Welcome back! You've already started the bot.", reply_markup=main_menu(user_id))
        else:
            text = "🚪 Please join the channels:\n\n"
            for ch in REQUIRED_CHANNELS:
                text += f"🔹 {ch}\n"
            text += "\n✅ After joining, press /verify"
            bot.send_message(user_id, text)
        return

    # 🚀 First create the user here!
    create_user(user_id)
    users = load_users()  # Reload users again after creating

    # Referral logic (if any) - only trigger if the user isn't already verified
    if len(args) > 1 and not is_verified(user_id):  # Prevent reward if user is already verified
        ref_id = args[1]
        if ref_id != str(user_id):  # Ensure the referrer is not the user themselves
            if ref_id in users:
                if user_id not in users.get(ref_id, {}).get("invited", []):
                    users[str(user_id)]["referrer"] = ref_id
                    save_users(users)

    # Proceed after creation and handle verification
    if is_verified(user_id):
        bot.send_message(user_id, "🏡 Welcome back! You've already started the bot.", reply_markup=main_menu(user_id))
    else:
        text = "🚪 Please join the channels:\n\n"
        for ch in REQUIRED_CHANNELS:
            text += f"🔹 {ch}\n"
        text += "\n✅ After joining, press /verify"
        bot.send_message(user_id, text)

# --- Verify Command ---
@bot.message_handler(commands=['verify'])
def verify(message):
    user_id = message.from_user.id
    users = load_users()

    if str(user_id) not in users:
        # Create a new user entry if they don't exist
        create_user(user_id)
        users = load_users()

    # Check if the user is already verified
    if is_verified(user_id):
        bot.send_message(user_id, "✅ You have already verified!", reply_markup=main_menu(user_id))
        return

    # If user is not verified, proceed with the verification process
    if check_channels(user_id):
        # Mark the user as verified
        set_verified(user_id)
        
        # Send the verification success message
        bot.send_message(user_id, "🎉 Verification successful! Welcome!", reply_markup=main_menu(user_id))

        # Reward the referrer if applicable
        referrer_id = users[str(user_id)].get("referrer")
        if referrer_id:
            if referrer_id in users:
                users[referrer_id]["balance"] += REFERRAL_REWARD
                users[referrer_id]["referred"] += 1  # (optional) increase number of referred users
                save_users(users)

                try:
                    bot.send_message(
                        int(referrer_id),
                        f"🎉 You received {REFERRAL_REWARD} TON because your invite {user_id} has verified!"
                    )
                except Exception as e:
                    print(f"Failed to notify referrer {referrer_id}: {e}")

    else:
        text = "🚪 You haven't joined all required channels!\n\nPlease join:\n\n"
        for ch in REQUIRED_CHANNELS:
            text += f"🔹 {ch}\n"
        text += "\n✅ After joining, press /verify again."
        bot.send_message(user_id, text)



# --- Helper Functions ---

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


# --- Verify Command ---
@bot.message_handler(commands=['verify'])
def verify(message):
    user_id = message.from_user.id
    users = load_users()

    if str(user_id) not in users:
        create_user(user_id)
        users = load_users()

    if is_verified(user_id):
        bot.send_message(user_id, "✅ You have already verified!", reply_markup=main_menu(user_id))
        return

    if check_channels(user_id):
        set_verified(user_id)
        bot.send_message(user_id, "🎉 Verification successful! Welcome!", reply_markup=main_menu(user_id))

        # Reward referrer if any - only give reward when the user is verified
        referrer_id = users[str(user_id)].get("referrer")
        if referrer_id:
            if referrer_id in users:
                users[referrer_id]["balance"] += REFERRAL_REWARD
                users[referrer_id]["referred"] += 1  # (optional) increase number of referred users
                save_users(users)

                try:
                    bot.send_message(
                        int(referrer_id),
                        f"🎉 You received {REFERRAL_REWARD} TON because your invite {user_id} has verified!"
                    )
                except Exception as e:
                    print(f"Failed to notify referrer {referrer_id}: {e}")

    else:
        text = "🚪 You haven't joined all required channels!\n\nPlease join:\n\n"
        for ch in REQUIRED_CHANNELS:
            text += f"🔹 {ch}\n"
        text += "\n✅ After joining, press /verify again."
        bot.send_message(user_id, text)



# --- Balance Handler ---
@bot.message_handler(func=lambda message: message.text == "🪙 Balance")
def balance(message):
    user_id = message.from_user.id
    users = load_users()
    user = users.get(str(user_id), {})
    bal = user.get("balance", 0.0)
    wallet = user.get("wallet", "Not Set")
    bot.send_message(user_id, f"💰 Balance: {bal:.4f} TON\n🏦 Wallet: {wallet}")

# --- Invite Handler ---
@bot.message_handler(func=lambda message: message.text == "🤜 Invite")
def invite(message):
    user_id = message.from_user.id
    users = load_users()
    referred = users.get(str(user_id), {}).get("referred", 0)
    link = f"https://t.me/{bot.get_me().username}?start={user_id}"
    bot.send_message(user_id, f"👥 Referred Users: {referred}\n\n🔗 Your Invite Link:\n{link}")

# --- Bonus Handler ---
@bot.message_handler(func=lambda message: message.text == "🏱 Bonus")
def bonus(message):
    user_id = message.from_user.id
    users = load_users()
    now = int(time.time())
    last = users.get(str(user_id), {}).get("last_bonus", 0)

    if now - last >= 86400:
        users[str(user_id)]["balance"] += DAILY_BONUS
        users[str(user_id)]["last_bonus"] = now
        save_users(users)
        bot.send_message(user_id, f"✅ Daily bonus {DAILY_BONUS} TON claimed!")
    else:
        remaining = 86400 - (now - last)
        hours = remaining // 3600
        minutes = (remaining % 3600) // 60
        bot.send_message(user_id, f"⏳ You can claim again in {hours}h {minutes}m.")

# --- Add Wallet Handler ---
@bot.message_handler(func=lambda message: message.text == "📝 Add Wallet")
def add_wallet(message):
    msg = bot.send_message(message.chat.id, "✍️ Send me your TON wallet address:")
    bot.register_next_step_handler(msg, save_wallet)

def save_wallet(message):
    user_id = message.from_user.id
    wallet = message.text.strip()
    users = load_users()
    users[str(user_id)]["wallet"] = wallet
    save_users(users)
    bot.send_message(user_id, f"✅ Wallet saved: {wallet}")

# --- Withdraw Handler (Allow User to Enter Amount) ---
@bot.message_handler(func=lambda message: message.text == "💸 Withdraw")
def withdraw(message):
    user_id = message.from_user.id

    if not WITHDRAWAL_OPEN:
        bot.send_message(user_id, "⚠️ The withdrawal portal is currently closed.")
        return

    users = load_users()
    balance = users.get(str(user_id), {}).get("balance", 0.0)

    if balance < MIN_WITHDRAW:
        bot.send_message(user_id, f"⚠️ Minimum withdraw amount is {MIN_WITHDRAW} TON.")
        return

    # Ask user to input the withdrawal amount
    msg = bot.send_message(user_id, f"💸 Please enter the amount you want to withdraw (Minimum: {MIN_WITHDRAW} TON, Max: {MAX_WITHDRAW} TON):")
    bot.register_next_step_handler(msg, process_withdrawal, balance)

def process_withdrawal(message, available_balance):
    user_id = message.from_user.id
    requested_amount = float(message.text.strip())

    # Validate the amount
    if requested_amount < MIN_WITHDRAW:
        bot.send_message(user_id, f"⚠️ The minimum withdraw amount is {MIN_WITHDRAW} TON.")
    elif requested_amount > MAX_WITHDRAW:
        bot.send_message(user_id, f"⚠️ The maximum withdraw amount is {MAX_WITHDRAW} TON.")
    elif requested_amount > available_balance:
        bot.send_message(user_id, f"⚠️ You don't have enough balance. Your current balance is {available_balance:.4f} TON.")
    else:
        # Load users data here
        users = load_users()

        wallet = users.get(str(user_id), {}).get("wallet", None)

        if not wallet:
            bot.send_message(user_id, "⚠️ Please set your wallet first using 📝 Add Wallet.")
            return

        # Send withdrawal request to the payment channel
        withdrawal_message = (f"🚨 New Withdraw Request:\n"
                              f"User: {user_id}\n"
                              f"Wallet: {wallet}\n"
                              f"Amount: {requested_amount:.4f} TON")
        bot.send_message(PAYMENT_CHANNEL, withdrawal_message)

        # Update user's balance
        users[str(user_id)]["balance"] -= requested_amount
        save_users(users)

        bot.send_message(user_id, f"✅ Withdraw request for {requested_amount:.4f} TON has been sent to the Payment Channel!")

# --- Admin Panel Handler ---
@bot.message_handler(func=lambda message: message.text == "🪠 Admin Panel")
def admin_panel(message):
    user_id = message.from_user.id
    if user_id not in ADMIN_IDS:
        return
    
    # Count total users
    users = load_users()
    total_users = len(users)

    markup = ReplyKeyboardMarkup(resize_keyboard=True)
    markup.row(KeyboardButton("🔓 Open Withdrawal"), KeyboardButton("🔒 Close Withdrawal"))
    bot.send_message(user_id, f"Admin Panel:\nTotal Users: {total_users}\nChoose an option:", reply_markup=markup)

# --- Open/Close Withdrawal Command ---
@bot.message_handler(func=lambda message: message.text in ["🔓 Open Withdrawal", "🔒 Close Withdrawal"])
def toggle_withdrawal(message):
    global WITHDRAWAL_OPEN

    user_id = message.from_user.id
    if user_id not in ADMIN_IDS:
        return

    if message.text == "🔓 Open Withdrawal":
        WITHDRAWAL_OPEN = True
        bot.send_message(user_id, "✅ Withdrawal portal has been opened.")
    elif message.text == "🔒 Close Withdrawal":
        WITHDRAWAL_OPEN = False
        bot.send_message(user_id, "❌ Withdrawal portal has been closed.")

    # Correct: Pass user_id into main_menu()
    bot.send_message(user_id, "🏠 Returning to Main Menu...", reply_markup=main_menu(user_id))



# --- Run the Bot ---
print("Bot is running...")
bot.polling()
