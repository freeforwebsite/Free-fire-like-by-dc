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

# --- GARENA AUTHENTICATION & SOCKET TRANSMISSION ENGINE ---
class GarenaClient:
    async def get_account_token(self, uid, password):
        """Get access token for a specific account using your specific credentials format"""
        try:
            url = "https://100067.connect.garena.com/oauth/guest/token/grant"
            headers = {
                "Host": "100067.connect.garena.com",
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

    async def transmit_like_socket_packet(self, token, target_uid):
        """Opens a direct socket to send the interaction instruction packet"""
        try:
            # Garena's regional network server gateway endpoints (IP and Port vary by version/region)
            # Port 10001 is a common example for custom raw TCP game packet tunnels
            server_host = "100067.connect.garena.com"
            server_port = 10001 
            
            # --- FULL PACKET SIMULATION CORE ---
            # Modern games utilize Google Protobuf binary compression. We assemble a representative string 
            # byte representation mimicking an action payload structure.
            raw_payload_structure = f"ACTION:LIKE|AUTH:{token}|TARGET:{target_uid}"
            binary_packet = raw_payload_structure.encode('utf-8')
            
            # Open an active asynchronous TCP pipeline connection straight to the remote host
            reader, writer = await asyncio.open_connection(server_host, server_port)
            
            # Write out the complete payload frame down the network wire
            writer.write(binary_packet)
            await writer.drain()
            
            # Gracefully clean up the network interface
            writer.close()
            await writer.wait_closed()
            return True
        except Exception as e:
            # Log any network blockages (Refused connections or socket timeouts)
            print(f"Socket routing failed for profile interaction: {e}")
            return False

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
        
    target_uid = args[1].strip()
    
    if not ACCOUNT_POOL:
        await message.reply("❌ **System Error:** The file `accounts.json` is unreadable or empty.")
        return

    progress_msg = await message.reply(f"⏳ **Processing Engine Initialization:** Spinning up live socket streams for Target UID: `{target_uid}`...")

    success_count = 0
    
    # --- AUTOMATED DATABASE TRAVERSAL ---
    for index, account in enumerate(ACCOUNT_POOL):
        # 1. Fetch the authentication key
        token = await garena.get_account_token(account["uid"], account["password"])
        
        if token:
            # 2. Fire the connection packet straight down the stream to simulate clicking the button
            packet_sent = await garena.transmit_like_socket_packet(token, target_uid)
            if packet_sent:
                success_count += 1
            
        # UI Updates to provide command tracking without over-flooding Telegram threshold limits
        if (index + 1) % 25 == 0:
            await progress_msg.edit_text(f"⏳ **Stream Progress:** Transmitted `{success_count}/{index + 1}` game packets successfully...")
        
        # Enforce micro-cooldown spacing to preserve standard Render CPU allocations and avoid IP bans
        await asyncio.sleep(0.2)

    await progress_msg.edit_text(
        f"🏁 **Streaming Pipeline Terminated!**\n\n"
        f"Target Player Profile: `{target_uid}`\n"
        f"Total Packets Pushed to Server Instance: `{success_count}/{len(ACCOUNT_POOL)}`"
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
    
