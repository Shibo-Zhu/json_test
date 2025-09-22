import requests

json_file = "C:\\Users\\zs348\\Desktop\\2025_08_21project0.json"

with open(json_file, "rb") as f:
    files = {"file": (json_file, f, "application/json")}
    response = requests.post("http://127.0.0.1:5000/upload", files=files)

print(response.status_code)
print(response.json())
