import os
import asyncio
import httpx
from fastapi import FastAPI
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
import uvicorn

async def Ua():
    return "Mozilla/5.0 (Linux; Android 11; KB2005) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/96.0.4664.45 Mobile Safari/537.36"

app = FastAPI()

@app.get("/")
async def root():
    return {"status": "Bot server running with account database loaded"}

class GarenaClient:
    async def get_account_token(self, uid, password):
        """Get access token for a specific account"""
        try:
            url = "https://garena.com"
            headers = {
                "Host": "://garena.com",
                "User-Agent": await Ua(),
                "Content-Type": "application/x-www-form-urlencoded",
                "Accept-Encoding": "gzip, deflate, br",
                "Connection": "close"
            }
            data = {
                "uid": uid,
                "password": password,
                "response_type": "token",
                "client_type": "2",
                "client_secret": "2ee44819e9b4598845141067b281621874d0d5d7af9d8f7e00c1e54715b7d1e3",
                "client_id": "100067"
            }
            
            async with httpx.AsyncClient() as client:
                response = await client.post(url, headers=headers, data=data, timeout=10.0)
                if response.status_code == 200:
                    return response.json().get("access_token")
                return None
        except Exception:
            return None

# --- NEW: HELPER TO LOAD 300+ ACCOUNTS FROM FILE ---
def load_garena_accounts():
    accounts = []
    file_path = "accounts.txt"
    
    if not os.path.exists(file_path):
        print("⚠️ Warning: accounts.txt file not found!")
        return accounts

    with open(file_path, "r") as file:
        for line in file:
            line = line.strip()
            if line and ":" in line:
                uid, password = line.split(":", 1)
                accounts.append({"uid": uid.strip(), "password": password.strip()})
                
    print(f"✅ Successfully loaded {len(accounts)} accounts into memory.")
    return accounts

BOT_TOKEN = os.getenv("BOT_TOKEN")
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()
garena = GarenaClient()

# Load the accounts list globally when the script initializes
ACCOUNT_POOL = load_garena_accounts()

@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    total_accs = len(ACCOUNT_POOL)
    await message.reply(
        f"⚡ **Free Fire Bot Active!**\n\n"
        f"Loaded Accounts Pool: `{total_accs}` accounts ready.\n"
        f"Use `/like <target_uid>` to begin processing stream."
    )

@dp.message(Command("like"))
async def cmd_like(message: types.Message):
    args = message.text.split()
    if len(args) < 2:
        await message.reply("❌ Formatting: `/like <target_uid>`")
        return
        
    target_uid = args[1]
    
    if not ACCOUNT_POOL:
        await message.reply("❌ Error: System account database is completely empty.")
        return

    progress_msg = await message.reply(f"⏳ Processing transaction stream via 300+ accounts for UID: `{target_uid}`...")

    success_count = 0
    
    # --- NEW: AUTOMATED ACCOUNT ROTATION LOOP ---
    for index, acc in enumerate(ACCOUNT_POOL):
        # Request access token for current account in pool
        token = await garena.get_account_token(acc["uid"], acc["password"])
        
        if token:
            success_count += 1
            # Note: Place your network socket binary instruction here.
            # E.g., await send_socket_like_packet(token, target_uid)
            
        # Optional: update user every 50 accounts to show progress without spamming Telegram limits
        if (index + 1) % 50 == 0:
            await progress_msg.edit_text(f"⏳ Progress: Authenticated `{index + 1}/{len(ACCOUNT_POOL)}` sessions...")
        
        # Micro sleep interval (0.1 seconds) to prevent overwhelming your Render CPU limit
        await asyncio.sleep(0.1)

    await progress_msg.edit_text(
        f"🏁 **Stream Completed!**\n\n"
        f"Target Player: `{target_uid}`\n"
        f"Successful Sessions Handled: `{success_count}/{len(ACCOUNT_POOL)}`"
    )

async def start_bot():
    await dp.start_polling(bot)

@app.on_event("startup")
async def on_startup():
    asyncio.create_task(start_bot())

if __name__ == "__main__":
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
  
