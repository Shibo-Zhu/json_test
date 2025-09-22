# -*- coding: utf-8 -*-
import sys
import json

def main():
    # 从 stdin 读取所有数据
    raw = sys.stdin.read()
    # print(raw)
    data = json.loads(raw)

    # 处理数据，比如返回 keys
    print("keys: %s" % list(data.keys()))

if __name__ == "__main__":
    main()
