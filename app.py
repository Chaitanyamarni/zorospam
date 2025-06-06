from flask import Flask, request, jsonify
import requests
import json
import threading
from byte import Encrypt_ID, encrypt_api
import like_count_pb2
import gzip
from io import BytesIO

app = Flask(__name__)

def load_tokens(region):
    try:
        if region.upper() != "IND":
            return None
        with open("token_ind.json", "r") as f:
            data = json.load(f)
            return [item["token"] for item in data]
    except Exception as e:
        app.logger.error(f"Error loading tokens: {e}")
        return None

def get_request_url(region):
    return "https://client.ind.freefiremobile.com/RequestAddingFriend"

def get_nickname(uid, token):
    try:
        encrypted_id = Encrypt_ID(uid)
        payload = f"08a7c4839f1e10{encrypted_id}1801"
        encrypted_payload = encrypt_api(payload)

        url = "https://client.ind.freefiremobile.com/GetPlayerPersonalShow"
        headers = {
            "Authorization": f"Bearer {token}",
            "User-Agent": "Dalvik/2.1.0 (Linux; Android 9)",
            "Content-Type": "application/x-www-form-urlencoded",
            "Content-Length": "16",
            "Host": "client.ind.freefiremobile.com",
            "Connection": "close",
            "Accept-Encoding": "gzip"
        }

        response = requests.post(url, headers=headers, data=bytes.fromhex(encrypted_payload))

        if response.status_code == 200:
            try:
                decompressed = gzip.decompress(response.content)
                info = like_count_pb2.Info()
                info.ParseFromString(decompressed)
                return info.AccountInfo.PlayerNickname
            except Exception as e:
                print(f"[ERROR] Decompression or parsing failed: {e}")
                return None
        else:
            print(f"[ERROR] Nickname request failed with status {response.status_code}")
    except Exception as e:
        print(f"[ERROR] Nickname fetch failed: {e}")
    return None

def send_friend_request(uid, token, results):
    try:
        encrypted_id = Encrypt_ID(uid)
        payload = f"08a7c4839f1e10{encrypted_id}1801"
        encrypted_payload = encrypt_api(payload)
        url = get_request_url("IND")

        headers = {
            "Authorization": f"Bearer {token}",
            "X-Unity-Version": "2018.4.11f1",
            "X-GA": "v1 1",
            "ReleaseVersion": "OB49",
            "Content-Type": "application/x-www-form-urlencoded",
            "Content-Length": "16",
            "User-Agent": "Dalvik/2.1.0 (Linux; Android 9)",
            "Host": "client.ind.freefiremobile.com",
            "Connection": "close",
            "Accept-Encoding": "gzip"
        }

        response = requests.post(url, headers=headers, data=bytes.fromhex(encrypted_payload))
        if response.status_code == 200:
            results["success"] += 1
        else:
            results["failed"] += 1
    except:
        results["failed"] += 1

@app.route("/send_requests", methods=["GET"])
def send_requests():
    uid = request.args.get("uid")
    region = request.args.get("region")

    if not uid or region.upper() != "IND":
        return jsonify({"error": "Only IND region is supported"}), 400

    tokens = load_tokens(region)
    if not tokens:
        return jsonify({"error": "No tokens found"}), 500

    results = {"success": 0, "failed": 0}
    threads = []

    for token in tokens[:110]:
        t = threading.Thread(target=send_friend_request, args=(uid, token, results))
        threads.append(t)
        t.start()

    for t in threads:
        t.join()

    nickname = get_nickname(uid, tokens[0])

    return jsonify({
        "UID": uid,
        "Region": "IND",
        "Totalspam": results["success"] + results["failed"],
        "Successfulspam": results["success"],
        "Failedspam": results["failed"],
       
    })

if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5000)
