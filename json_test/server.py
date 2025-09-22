import subprocess
import os
import logging
from flask import Flask, request, jsonify

app = Flask(__name__)

current_dir = os.path.dirname(os.path.abspath(__file__))

logging.basicConfig(level=logging.INFO, filename=os.path.join(current_dir, 'server.log'),
                    format='%(asctime)s - %(levelname)s - %(message)s')


@app.route('/upload', methods=['POST'])
def upload_json():
    if 'file' not in request.files:
        return jsonify({"error": "No file uploaded"}), 400

    file = request.files['file']
    json_data = file.read()   # 直接读取文件内容 (bytes)
    with open(os.path.join(current_dir, "input.json"), "wb") as f:
        f.write(json_data)
    python_exe = os.path.join(current_dir, "jsonConvert", "env", "python.exe")
    script_path = os.path.join(current_dir, "jsonConvert", "json2xml_test.py")
    try:
        # 把 JSON 数据传到 Python2 脚本的 stdin
        logging.info("Received JSON data for processing.")
        logging.info("Executing %s %s", python_exe, script_path)
        result = subprocess.run(
            [python_exe, script_path],
            input=str(json_data, 'utf-8'),  # 传递给 stdin 的数据
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True  # 把输出解码为字符串
        )

        if result.returncode != 0:
            logging.error("Error occurred while executing script: %s", result.stderr)
            return jsonify({"error": result.stderr}), 500

        logging.info("Script executed successfully: %s", result.stdout.strip())
        return jsonify({"result": result.stdout.strip()})

    except Exception as e:
        logging.error("Unexpected error occurred: %s", str(e))
        return jsonify({"error": str(e)}), 500


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
