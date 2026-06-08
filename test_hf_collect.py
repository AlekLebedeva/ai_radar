import json
import time
import urllib.request
import http.cookiejar

BASE = "http://127.0.0.1:8000"
LOGIN = f"{BASE}/api/v1/admin/login"
HF_TASK = f"{BASE}/api/v1/admin/tasks/huggingface"

cj = http.cookiejar.CookieJar()
opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cj))

creds = {"username": "admin", "password": "admin"}

# wait for server
for i in range(40):
    try:
        req = urllib.request.Request(LOGIN, data=json.dumps(creds).encode(), headers={"Content-Type": "application/json"})
        resp = opener.open(req, timeout=3)
        body = resp.read().decode()
        print("login response:", resp.status, body)
        break
    except Exception as e:
        if i == 39:
            print("server did not start in time:", e)
            raise
        time.sleep(0.5)

# send HF task
task = {
    "date_from": "2024-01-01T00:00:00Z",
    "date_to": "2026-06-01T00:00:00Z",
    "filters": {},
    "max_items": 10
}
req2 = urllib.request.Request(HF_TASK, data=json.dumps(task).encode(), headers={"Content-Type": "application/json"})
resp2 = opener.open(req2, timeout=10)
print("create task response:", resp2.status, resp2.read().decode())
