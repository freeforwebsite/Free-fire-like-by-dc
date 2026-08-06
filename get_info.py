import httpx
import json
import base64
from google.protobuf import json_format
from ff_proto import core_pb2, account_show_pb2, freefire_pb2
from get_jwt import create_jwt, json_to_proto, aes_cbc_encrypt, decode_protobuf, MAIN_KEY, MAIN_IV, RELEASEVERSION, USERAGENT

async def get_account_info(target_uid: str, guest: dict) -> dict:
    """
    Fetches the profile info of a target_uid using a valid guest account (or token) for authentication.
    """
    if "token" in guest:
        token = guest["token"]
        # Default to IND server if we are bypassing the JWT extraction flow
        server_url = "https://client.ind.freefiremobile.com"
    else:
        token, region, server_url = await create_jwt(guest["uid"], guest.get("password"))
    
    # 2. Fetch target profile
    json_data = json.dumps({
        "a": target_uid,
        "b": "0"
    })
    encoded_result = await json_to_proto(json_data, core_pb2.GetPlayerPersonalShow())
    payload = aes_cbc_encrypt(MAIN_KEY, MAIN_IV, encoded_result)
    
    headers = {
        'User-Agent': "Dalvik/2.1.0 (Linux; U; Android 13; A063 Build/TKQ1.221220.001)",
        'Connection': "Keep-Alive",
        'Accept-Encoding': "gzip",
        'Content-Type': "application/octet-stream",
        'Expect': "100-continue",
        'Authorization': f"Bearer {token}",
        'X-Unity-Version': "2018.4.11f1",
        'X-GA': "v1 1",
        'ReleaseVersion': RELEASEVERSION
    }
    
    endpoint = "/GetPlayerPersonalShow"
    async with httpx.AsyncClient() as client:
        response = await client.post(server_url + endpoint, data=payload, headers=headers)
        response_content = response.content
        message = json.loads(json_format.MessageToJson(decode_protobuf(response_content, account_show_pb2.AccountPersonalShowInfo)))
        return message
