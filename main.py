import os
import json
import asyncio
import httpx
import binascii
from fastapi import FastAPI
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
import uvicorn

from get_jwt import create_jwt
from encrypt_like_body import create_like_payload

# --- FASTAPI ENVIRONMENT (Required to pass Render Web Service Health Checks) ---
app = FastAPI()

@app.get("/")
async def root():
    return {"status": "Bot backend deployment live and actively listening."}

def get_base_url(server_name: str) -> str:
    if server_name == "IND":
        return "https://client.ind.freefiremobile.com"
    elif server_name in {"BR", "US", "SAC", "NA"}:
        return "https://client.us.freefiremobile.com"
    else:
        return "https://clientbp.ggblueshark.com"

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
# If BOT_TOKEN is None, bot will fail to init. We catch this gracefully.
bot = Bot(token=BOT_TOKEN) if BOT_TOKEN else None
dp = Dispatcher()

# Global initialization of the accounts database 
ACCOUNT_POOL = load_garena_accounts()

@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    total_accs = len(ACCOUNT_POOL)
    await message.reply(
        f"⚡ **Free Fire Interactive Bot Ready!**\n\n"
        f"Available Account Database: `{total_accs}` profiles loaded.\n"
        f"To submit a job string, use: `/like <target_uid> [region]`\n"
        f"Region is optional (default: IND). Example: `/like 123456789 BR`"
    )

@dp.message(Command("like"))
async def cmd_like(message: types.Message):
    args = message.text.split()
    if len(args) < 2:
        await message.reply("❌ **Invalid Syntax.** Formatting: `/like <target_uid> [region]`")
        return
        
    target_uid = args[1].strip()
    region = "IND"
    if len(args) > 2:
        region = args[2].strip().upper()
    
    if not ACCOUNT_POOL:
        await message.reply("❌ **System Error:** The file `accounts.json` is unreadable or empty.")
        return

    progress_msg = await message.reply(f"⏳ **Processing Engine Initialization:** Spinning up HTTP clients for Target UID: `{target_uid}` on region `{region}`...")

    success_count = 0
    first_error = None
    BASE_URL = get_base_url(region)
    
    # Cap to 100 max likes per run to respect FF limits and avoid blocking telegram handler indefinitely
    accounts_to_use = ACCOUNT_POOL[:100]
    total_attempted = len(accounts_to_use)
    
    # --- AUTOMATED DATABASE TRAVERSAL ---
    for index, account in enumerate(accounts_to_use):
        guest_uid = account["uid"]
        guest_pass = account["password"]
        try:
            jwt, region_from_jwt, server_url_from_jwt = await create_jwt(guest_uid, guest_pass)
            if jwt:
                payload = create_like_payload(target_uid, region_from_jwt)
                if isinstance(payload, str):
                    payload = binascii.unhexlify(payload)

                headers = {
                    "User-Agent": "Dalvik/2.1.0 (Linux; U; Android 14; Pixel 8 Build/UP1A.231005.007)",
                    "Connection": "Keep-Alive",
                    "Accept-Encoding": "gzip",
                    "Content-Type": "application/octet-stream",
                    "Expect": "100-continue",
                    "Authorization": f"Bearer {jwt}",
                    "X-Unity-Version": "2018.4.11f1",
                    "X-GA": "v1 1",
                    "ReleaseVersion": "OB50",
                }

                async with httpx.AsyncClient() as client:
                    url = f"{BASE_URL}/LikeProfile"
                    response = await client.post(url, data=payload, headers=headers, timeout=30)
                    if response.status_code == 200:
                        success_count += 1
                    else:
                        err_msg = f"HTTP {response.status_code} - {response.text}"
                        print(f"Error liking with {guest_uid}: {err_msg}")
                        if not first_error:
                            first_error = err_msg
                        
        except Exception as e:
            print(f"Error liking with {guest_uid}: {e}")
            if not first_error:
                first_error = str(e)
            
        # UI Updates to provide command tracking without over-flooding Telegram threshold limits
        if (index + 1) % 10 == 0:
            try:
                await progress_msg.edit_text(f"⏳ **Stream Progress:** Transmitted `{success_count}/{index + 1}` likes successfully...")
            except Exception:
                pass
        
        # Enforce micro-cooldown spacing to preserve standard Render CPU allocations and avoid IP bans
        await asyncio.sleep(0.5)

    try:
        final_text = (
            f"🏁 **Streaming Pipeline Terminated!**\n\n"
            f"Target Player Profile: `{target_uid}`\n"
            f"Total Likes Sent: `{success_count}/{total_attempted}`"
        )
        if first_error and success_count == 0:
            final_text += f"\n\n⚠️ **Error Example:** `{first_error}`"
            
        await progress_msg.edit_text(final_text)
    except Exception:
        pass

# --- CONCURRENT THREAD CONTROLLER ---
async def run_bot_polling():
    if bot:
        await dp.start_polling(bot)
    else:
        print("BOT_TOKEN not provided, skipping telegram polling.")

@app.on_event("startup")
async def on_startup():
    # Schedules the polling sequence continuously alongside the web port
    asyncio.create_task(run_bot_polling())

if __name__ == "__main__":
    # Render maps runtime parameters utilizing dynamic environment declarations
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
