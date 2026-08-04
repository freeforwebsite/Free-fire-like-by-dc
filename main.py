import os
import json
import asyncio
import httpx
from fastapi import FastAPI
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
import uvicorn

# Dynamic User-Agent Generator
async def Ua():
    return "Mozilla/5.0 (Linux; Android 11; KB2005) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/96.0.4664.45 Mobile Safari/537.36"

# --- FASTAPI ENVIRONMENT (Required to pass Render Web Service Health Checks) ---
app = FastAPI()

@app.get("/")
async def root():
    return {"status": "Bot backend deployment live and actively listening."}

# --- GARENA AUTHENTICATION SUB-ENGINE ---
class GarenaClient:
    async def get_account_token(self, uid, password):
        """Get access token for a specific account using your specific credentials format"""
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
                "uid": str(uid).strip(),
                "password": str(password).strip(),
                "response_type": "token",
                "client_type": "2",
                "client_secret": "2ee44819e9b4598845141067b281621874d0d5d7af9d8f7e00c1e54715b7d1e3",
                "client_id": "100067"
            }
            
            async with httpx.AsyncClient() as client:
                response = await client.post(url, headers=headers, data=data, timeout=12.0)
                if response.status_code == 200:
                    return response.json().get("access_token")
                return None
        except Exception as e:
            print(f"Network processing exception: {e}")
            return None

# --- DATABASE LOADING ROUTINE FOR JSON LAYOUT ---
def load_garena_accounts():
    accounts = []
    file_path = "accounts.json"
    
    if not os.path.exists(file_path):
        print("⚠️ Warning: accounts.json file not found in directory root!")
        return accounts

    try:
        with open(file_path, "r") as file:
            accounts_data = json.load(file)
            for item in accounts_data:
                uid = item.get("uid")
                password = item.get("password")
                if uid and password:
                    accounts.append({
                        "uid": str(uid).strip(), 
                        "password": str(password).strip()
                    })
        print(f"✅ Micro-database loaded successfully: {len(accounts)} accounts found.")
        return accounts
    except Exception as e:
        print(f"❌ Structural breakdown reading accounts.json: {e}")
        return accounts

# --- INSTANTIATE TELEGRAM DISPATCHER CORE ---
BOT_TOKEN = os.getenv("BOT_TOKEN")
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()
garena = GarenaClient()

# Global initialization of the accounts database 
ACCOUNT_POOL = load_garena_accounts()

@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    total_accs = len(ACCOUNT_POOL)
    await message.reply(
        f"⚡ **Free Fire Interactive Bot Ready!**\n\n"
        f"Available Account Database: `{total_accs}` profiles loaded.\n"
        f"To submit a job string, use: `/like <target_uid>`"
    )

@dp.message(Command("like"))
async def cmd_like(message: types.Message):
    args = message.text.split()
    if len(args) < 2:
        await message.reply("❌ **Invalid Syntax.** Formatting: `/like <target_uid>`")
        return
        
    target_uid = args[1]
    
    if not ACCOUNT_POOL:
        await message.reply("❌ **System Error:** The file `accounts.json` is unreadable or empty.")
        return

    progress_msg = await message.reply(f"⏳ **Session Initialization:** Queueing processing pipeline for target UID: `{target_uid}`...")

    success_count = 0
    
    # --- AUTOMATED DATABASE TRAVERSAL ---
    for index, account in enumerate(ACCOUNT_POOL):
        token = await garena.get_account_token(account["uid"], account["password"])
        
        if token:
            success_count += 1
            # Note: The parsed session token and destination target_uid strings terminate here.
            # Insert any downstream raw TCP socket formatting routines here if applicable.
            
        # UI Updates to provide command tracking without over-flooding Telegram threshold limits
        if (index + 1) % 50 == 0:
            await progress_msg.edit_text(f"⏳ **Stream Progress:** Parsed `{index + 1}/{len(ACCOUNT_POOL)}` authorization instances...")
        
        # Enforce micro-cooldown spacing to preserve standard Render CPU allocations
        await asyncio.sleep(0.1)

    await progress_msg.edit_text(
        f"🏁 **Streaming Pipeline Terminated!**\n\n"
        f"Target Player Profile: `{target_uid}`\n"
        f"Total Successfully Evaluated Credentials: `{success_count}/{len(ACCOUNT_POOL)}`"
    )

# --- CONCURRENT THREAD CONTROLLER ---
async def run_bot_polling():
    await dp.start_polling(bot)

@app.on_event("startup")
async def on_startup():
    # Schedules the polling sequence continuously alongside the web port
    asyncio.create_task(run_bot_polling())

if __name__ == "__main__":
    # Render maps runtime parameters utilizing dynamic environment declarations
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
    
