import json
import cv2
import numpy as np
import os
from time import sleep
import paramiko
import requests
import random
from filelock import FileLock

def connect_arm(type):
    try:
        with FileLock("robot_arm.lock"):
            print("正在尝试连接机械臂……")
            ssh = paramiko.SSHClient()
            print("start to cnnect arm")
            ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            ssh.connect(hostname='192.168.2.150', port=22, username='ubuntu', password='ubuntu')

            if type == "crack":
                stdin, stdout, stderr = ssh.exec_command('sudo python3 /home/ubuntu/Ai_FPV/YDS/turnRightCrack.py')
            elif type== "scar":
                stdin, stdout, stderr = ssh.exec_command('sudo python3 /home/ubuntu/Ai_FPV/YDS/turnRightCrack.py')

            print(stdout.read().decode())

            ssh.close()

    except Exception as e:
        print(e)




fifo_path1 = "/../sensor_data/fifo1"
fifo_path = os.path.normpath(os.path.dirname(os.path.abspath(__file__)) + fifo_path1)

url = 'http://192.168.2.125:5000'

num_true = 0


with open(fifo_path, "r") as fifo:
    while True:
        sleep(0.1)
        message = fifo.readline().strip()
        # print(f"variable{fifo_path}:{message}")
        print(f"message:{message}")
        print(f"num_true:{num_true}")
        if message == "True" and num_true == 0:
            num_true = num_true + 1

            # 向边缘计算节点发送开启相机的指令
            # url_process = url + '/process'
            # data = [{
            #     'camera_address': 1,
            #     'is_open':1,
            #     'priority':0,
            #     'Pipeline':['camera','steel_inspection','result']
            # }]
            # response = requests.post(url_process,data=json.dumps(data))
            # print('Status Code:', response.status_code)
            # print('Response Body:', response.text)
            # sleep(4)# 等待信息返回

            url_result = url + '/result'
            response = requests.get(url_result)
            print('Status Code:', response.status_code)
            # 假设对方是返回json数组
            response_data = json.loads(response.text)
            if response_data.get('is_ok')==0:
                print("Good!")
            else:
                type = response_data.get('type')
                connect_arm(type)


            # type = "crack" # 生成1~4之间的随机整数，替代返回的整数
            # print("准备连接机械臂……")
            # connect_arm(type)

        elif message == "False":
            num_true = 0

