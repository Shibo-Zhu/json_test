import requests

json_file = "/media/zs/ubuntu_disk/json_test/json_test/input.json"

with open(json_file, "rb") as f:
    files = {"file": (json_file, f, "application/json")}
    response = requests.post("http://127.0.0.1:5000/upload", files=files)

print(response.status_code)
print(response.json())
