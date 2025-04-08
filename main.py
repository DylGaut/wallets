import os
import requests
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, ConversationHandler, CallbackContext

# Load env variables (for local testing)
load_dotenv()

# Get keys from environment
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
HELIUS_API_KEY = os.getenv("HELIUS_API_KEY")

# Telegram bot states
ASK_WALLETS, ASK_TOKENS = range(2)

# Start command
def start(update: Update, context: CallbackContext):
    update.message.reply_text("👋 Send me the wallet addresses (one per line):")
    return ASK_WALLETS

# Step 1: Receive wallet addresses
def get_wallets(update: Update, context: CallbackContext):
    wallet_text = update.message.text.strip()
    context.user_data['wallets'] = wallet_text.splitlines()
    update.message.reply_text("✅ Got wallets. Now send the token mint addresses (one per line):")
    return ASK_TOKENS

# Step 2: Receive token mint addresses and process
def get_tokens(update: Update, context: CallbackContext):
    token_text = update.message.text.strip()
    wallets = context.user_data.get('wallets', [])
    token_mints = token_text.splitlines()

    update.message.reply_text("🔍 Checking wallet interactions... please wait.")

    matching_wallets = filter_wallets_by_token_interactions(wallets, token_mints)

    if matching_wallets:
        result = "✅ Wallets that interacted with ALL listed tokens:\n" + "\n".join(matching_wallets)
    else:
        result = "❌ No wallets interacted with all the tokens."

    update.message.reply_text(result)
    return ConversationHandler.END

# Cancel command
def cancel(update: Update, context: CallbackContext):
    update.message.reply_text("🚫 Canceled.")
    return ConversationHandler.END

# Pull token transfer history using Helius
def get_token_transfers(wallet):
    url = f"https://api.helius.xyz/v0/addresses/{wallet}/transactions?api-key={HELIUS_API_KEY}"
    try:
        response = requests.get(url)
        response.raise_for_status()
        transactions = response.json()
        interacted_mints = set()

        for tx in transactions:
            token_transfers = tx.get("tokenTransfers", [])
            for transfer in token_transfers:
                mint = transfer.get("mint")
                if mint:
                    interacted_mints.add(mint)

        return interacted_mints
    except Exception as e:
        print(f"Error with wallet {wallet}: {e}")
        return set()

# Filter wallets that interacted with all listed tokens
def filter_wallets_by_token_interactions(wallets, token_mints):
    qualifying_wallets = []

    for wallet in wallets:
        print(f"Checking wallet: {wallet}")
        interacted = get_token_transfers(wallet)
        if set(token_mints).issubset(interacted):
            qualifying_wallets.append(wallet)

    return qualifying_wallets

# Main function to run the bot
def main():
    updater = Updater(TELEGRAM_BOT_TOKEN, use_context=True)
    dp = updater.dispatcher

    conv_handler = ConversationHandler(
        entry_points=[CommandHandler('start', start)],
        states={
            ASK_WALLETS: [MessageHandler(Filters.text & ~Filters.command, get_wallets)],
            ASK_TOKENS: [MessageHandler(Filters.text & ~Filters.command, get_tokens)],
        },
        fallbacks=[CommandHandler('cancel', cancel)]
    )

    dp.add_handler(conv_handler)

    print("🤖 Bot is running...")
    updater.start_polling()
    updater.idle()

if __name__ == "__main__":
    main()
