# - *- coding: utf- 8 - *-
import json
import os
import subprocess

current_dir = os.path.dirname(os.path.abspath(__file__))
json_file = os.path.join(current_dir, 'itdata_output.json')

ydscode_template = """
import cv2
import numpy as np
import os
from time import sleep, time
import paramiko
import threading
from queue import PriorityQueue
from filelock import FileLock


def connect_arm(return_color, belt_index):
    try:
        with FileLock("robot_arm.lock"):
            print(f"belt{{belt_index}} try to connect arm")
            ssh = paramiko.SSHClient()
            print("start to cnnect arm")
            ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            ssh.connect(hostname='192.168.3.12', port=22, username='ubuntu', password='ubuntu')

            if belt_index ==0:
                if return_color == "green":
                    stdin, stdout, stderr = ssh.exec_command('sudo python3 /home/ubuntu/Ai_FPV/YDS/turnLeftGreen.py')
                else:
                    stdin, stdout, stderr = ssh.exec_command('sudo python3 /home/ubuntu/Ai_FPV/YDS/turnLeftRed.py')
            elif belt_index ==1:
                if return_color == "green":
                    stdin, stdout, stderr = ssh.exec_command('sudo python3 /home/ubuntu/Ai_FPV/YDS/turnRightGreen.py')
                else:
                    stdin, stdout, stderr = ssh.exec_command('sudo python3 /home/ubuntu/Ai_FPV/YDS/turnRightRed.py')

            print(stdout.read().decode())

            ssh.close()

    except Exception as e:
        print(e)


def find_largest_color_object(frame):
    hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)

    green_lower_color = np.array([50, 90, 90])
    green_upper_color = np.array([90, 255, 255])
    green_text_color = (0, 255, 0)  #
    red_lower_color = np.array([0, 100, 100])
    red_upper_color = np.array([10, 255, 255])
    red_lower_color2 = np.array([160, 100, 100])
    red_upper_color2 = np.array([180, 255, 255])
    red_text_color = (0, 0, 255)  #

    mask1 = cv2.inRange(hsv, red_lower_color, red_upper_color)
    mask2 = cv2.inRange(hsv, red_lower_color2, red_upper_color2)
    red_mask = cv2.bitwise_or(mask1, mask2)
    green_mask = cv2.inRange(hsv, green_lower_color, green_upper_color)

    kernel = np.ones((5,5), np.uint8)
    red_dilated_mask = cv2.dilate(red_mask, kernel, iterations=1)
    green_dilated_mask = cv2.dilate(green_mask, kernel, iterations=1)

    red_contours, _ = cv2.findContours(red_dilated_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    green_contours, _ = cv2.findContours(green_dilated_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    red_max_contour = None
    red_max_area = 0
    for contour in red_contours:
        area = cv2.contourArea(contour)
        if area > red_max_area:
            red_max_area = area
            red_max_contour = contour

    green_max_contour = None
    green_max_area = 0
    for contour in green_contours:
        area = cv2.contourArea(contour)
        if area > green_max_area:
            green_max_area = area
            green_max_contour = contour

    return_color = ''
    if (red_max_contour is not None) and (green_max_contour is not None):
        if red_max_area > green_max_area:
            x, y, w, h = cv2.boundingRect(red_max_contour)
            cv2.rectangle(frame, (x, y), (x + w, y + h), red_text_color, 2)
            cv2.putText(frame, 'red good', (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 1, red_text_color, 2)
            return_color = 'red'
        else:
            x, y, w, h = cv2.boundingRect(green_max_contour)
            cv2.rectangle(frame, (x, y), (x + w, y + h), green_text_color, 2)
            cv2.putText(frame, 'green good', (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 1, green_text_color, 2)
            return_color = 'green'

    return frame, return_color


def process_conveyor(fifo_path, camera_index, belt_index, task_queue):
    num_true = 0

    with open(fifo_path, "r") as fifo:
        while True:
            sleep(0.1)
            message = fifo.readline().strip()
            print(f"variable{{fifo_path}}:{{message}}")
            if message == "True" and num_true == 0:
                print(f"belt {{belt_index}} video detect ...")
                num_true = num_true + 1
                color = "red"
                with FileLock("camera.lock"):
                    cap = cv2.VideoCapture(camera_index)

                    if cap.isOpened():
                        ret, frame = cap.read()
                        frame_with_box, return_color = find_largest_color_object(frame)
                        color = return_color
                        print(f"belt {{belt_index}} detect:", color)
                    cap.release()


                task_queue.add_request(time(),color,belt_index)

            elif message == "False":
                num_true = 0



class RequestQueue_sched:
    def __init__(self):
        self.red_requests = []
        self.green_requests = []
        self.lock = threading.Lock()
        self.num_green = 0

    def add_request(self, timestamp, color, belt_index):
        with self.lock:
            if color == 'red':
                self.red_requests.append((timestamp, color, belt_index))
            else:
                self.green_requests.append((timestamp, color, belt_index))


    def process_request(self):
        if self.red_requests:
            earliest_red_request = min(self.red_requests, key=lambda x: x[0])
            with self.lock:
                self.red_requests.remove(earliest_red_request)
            return earliest_red_request
        else:
            if self.num_green == 1:
                print("Second green, process!")
                earliest_green_request = min(self.green_requests, key=lambda x: x[0])
                with self.lock:
                    self.green_requests.remove(earliest_green_request)
                self.num_green = 0
                return earliest_green_request
            elif self.num_green == 0 and self.green_requests:
                print("First green, wait 3s")
                self.num_green = self.num_green +1
                sleep(3)
                return None

    def start_processing(self):
        request = self.process_request()
        if request:
            timestamp, color, belt_index = request
            print(f"Processing {{color}} request from belt {{belt_index}} at {{timestamp}}")

            connect_arm(color,belt_index)  


def scheduler(task_queue):
    while True:
        task_queue.start_processing()
        sleep(0.1)
fifo_path1 = "/../sensor_data/{sensor_fifo1}"
fifo_path2 = "/../sensor_data/{sensor_fifo2}"

fifo_path1 = os.path.normpath(os.path.dirname(os.path.abspath(__file__)) + fifo_path1)
fifo_path2 = os.path.normpath(os.path.dirname(os.path.abspath(__file__)) + fifo_path2)

belt1_index = {belt1_index}
belt2_index = {belt2_index}
camera1_index = {camera1_index}
camera2_index = {camera2_index}

Sched = {Sched}

if Sched:
    task_queue = RequestQueue_sched()

    thread1 = threading.Thread(target=process_conveyor, args=(fifo_path1, camera1_index,belt1_index, task_queue))
    thread2 = threading.Thread(target=process_conveyor, args=(fifo_path2, camera2_index, belt2_index, task_queue))
    scheduler_thread = threading.Thread(target=scheduler, args=(task_queue,))

    thread1.start()
    thread2.start()
    scheduler_thread.start()

    thread1.join()
    thread2.join()
    scheduler_thread.join()
else:
    thread1 = threading.Thread(target=process_conveyor, args=(fifo_path1, camera1_index,belt1_index))
    thread2 = threading.Thread(target=process_conveyor, args=(fifo_path2, camera2_index, belt2_index))

    thread1.start()
    thread2.start()


    thread1.join()
    thread2.join()

"""

njucode_template = """
import json
import time
import requests
import traceback

url = "http://{ip}:{port}/"
start_url = "http://{ip}:{port}/start"
end_url = "http://{ip}:{port}/end"
result_url = "http://{ip}:{port}/result"
bodys =  {bodys}

DataFlag1 = bodys[0]['DataFlag']
DataFlag2 = bodys[1]['DataFlag']
DataFlag3 = bodys[2]['DataFlag']

def send_request(url, body):
    response = requests.post(url, json=body)
    return response.status_code

for body in bodys:
    status_code = send_request(start_url, body)

while True:
    if DataFlag1 == "true":
        response1 = requests.get(result_url)
        print(response1.text)
    if DataFlag2 == "true":
        response2 = requests.get(result_url)
        print(response1.text)
    if DataFlag3 == "true":
        response3 = requests.get(result_url)
        print(response1.text)
    
    if DataFlag1 == "false" and DataFlag2 == "false" and DataFlag3 == "false":
        break

    time.sleep(1)
"""

fmlcode_template = """# -*- coding: utf-8 -*-
import socket
import sys
import binascii
import time
import requests
import json
import threading
from pynput import keyboard

from pymodbus.client.sync import ModbusTcpClient
from pymodbus.exceptions import ConnectionException

class fmlROBOT:
    def __init__(self):
        self.client = ModbusTcpClient('192.168.1.32')
        self.client.connect()

    def JQZX_read(self):
        result1 = self.client.read_holding_registers(36)
        if result1.isError():
            print("失败: {}".format(result1))
        else:
            data1 = result1.registers
            print("剪切中心->管控系统(bit), 返回信号: {}".format(data1))

        result2 = self.client.read_holding_registers(38)
        if result2.isError():
            print("失败: {}".format(result2))
        else:
            data2 = result2.registers
            print("剪切中心->管控系统(byte), 返回信号: {}".format(data2))

        result3 = self.client.read_holding_registers(54)
        if result3.isError():
            print("失败: {}".format(result3))
        else:
            data3 = result3.registers
            print("管控系统->剪切中心(bit), 返回信号: {}".format(data3))

        result4 = self.client.read_holding_registers(56)
        if result4.isError():
            print("失败: {}".format(result4))
        else:
            data4 = result4.registers
            print("管控系统->剪切中心(byte), 返回信号: {}".format(data4))

    def JQZX_write(self, flag1=0, flag2=1, flag3=256):
        try:
            result1 = self.client.write_register(address=54, value=flag1)
            result2 = self.client.write_register(address=56, value=flag2)
            result3 = self.client.write_register(address=55, value=flag3) #演示，启动
        except ConnectionException:
            return -1
        if result1.isError() or result2.isError() or result3.isError():
            return -1
        else:
            print("启动 = {}, 工艺编号 = {}, 演示 = {}".format(flag1, flag2, flag3))
            return 1


    def YQJCK_read(self):
        result1 = self.client.read_holding_registers(72)
        if result1.isError():
            print("失败: {}".format(result1))
        else:
            data1 = result1.registers
            print("元器件仓库->管控系统(bit), 返回信号: {}".format(data1))

        result3 = self.client.read_holding_registers(90)
        if result3.isError():
            print("失败: {}".format(result3))
        else:
            data3 = result3.registers
            print("管控系统->元器件仓库(bit), 返回信号: {}".format(data3))


    def DKGJAZB_read(self):
        result1 = self.client.read_holding_registers(108)
        if result1.isError():
            print("失败: {}".format(result1))
        else:
            data1 = result1.registers
            print("电控柜及安装版->管控系统(bit), 返回信号: {}".format(data1))

        result3 = self.client.read_holding_registers(126)
        if result3.isError():
            print("失败: {}".format(result3))
        else:
            data3 = result3.registers
            print("管控系统->电控柜及安装版(bit), 返回信号: {}".format(data3))


    def DZZPZX_read(self):
        result1 = self.client.read_holding_registers(144)
        if result1.isError():
            print("失败: {}".format(result1))
        else:
            data1 = result1.registers
            print("端子装配中心->管控系统(bit), 返回信号: {}".format(data1))

        result2 = self.client.read_holding_registers(146)
        if result2.isError():
            print("失败: {}".format(result2))
        else:
            data2 = result2.registers
            print("端子装配中心->管控系统(byte), 返回信号: {}".format(data2))

        result3 = self.client.read_holding_registers(162)
        if result3.isError():
            print("失败: {}".format(result3))
        else:
            data3 = result3.registers
            print("管控系统->端子装配中心(bit), 返回信号: {}".format(data3))

        result4 = self.client.read_holding_registers(164)
        if result4.isError():
            print("失败: {}".format(result4))
        else:
            data4 = result4.registers
            print("管控系统->端子装配中心(byte), 返回信号: {}".format(data4))

    def DZZPZX_write(self, flag1=0, flag2=1):
        try:
            result1 = self.client.write_register(address=162, value=flag1)
            result2 = self.client.write_register(address=164, value=flag2)
        
        except ConnectionException:
            return -1
        
        if result1.isError() or result2.isError():
            return -1
        else:
            print("启动 = {}, 工艺编号 = {}".format(flag1, flag2))
            return 1

    def ZDZPGZZ_read(self):
        result1 = self.client.read_holding_registers(180)
        if result1.isError():
            print("失败: {}".format(result1))
        else:
            data1 = result1.registers
            print("自动装配工作站->管控系统(bit), 返回信号: {}".format(data1))

        result2 = self.client.read_holding_registers(182)
        if result2.isError():
            print("失败: {}".format(result2))
        else:
            data2 = result2.registers
            print("自动装配工作站->管控系统(byte), 返回信号: {}".format(data2))

        result3 = self.client.read_holding_registers(198)
        if result3.isError():
            print("失败: {}".format(result3))
        else:
            data3 = result3.registers
            print("管控系统->自动装配工作站(bit), 返回信号: {}".format(data3))

        result4 = self.client.read_holding_registers(200)
        if result4.isError():
            print("失败: {}".format(result4))
        else:
            data4 = result4.registers
            print("管控系统->自动装配工作站(byte), 返回信号: {}".format(data4))

    def ZDZPGZZ_write(self, flag1=0, flag2=1, flag3=256):
        try:
            result1 = self.client.write_register(address=198, value=flag1)
            result2 = self.client.write_register(address=200, value=flag2)
            result3 = self.client.write_register(address=199, value=flag3) # 演示
        except ConnectionException:
            return -1
        if result1.isError() or result2.isError():
            return -1
        else:
            print("启动 = {}, 工艺编号 = {}".format(flag1, flag2))
            return 1

    def ZDJXGZZ_read(self):
        result1 = self.client.read_holding_registers(216)
        if result1.isError():
            print("失败: {}".format(result1))
        else:
            data1 = result1.registers
            print("自动接线工作站->管控系统(bit), 返回信号: {}".format(data1))

        result2 = self.client.read_holding_registers(218)
        if result2.isError():
            print("失败: {}".format(result2))
        else:
            data2 = result2.registers
            print("自动接线工作站->管控系统(byte), 返回信号: {}".format(data2))

        result3 = self.client.read_holding_registers(234)
        if result3.isError():
            print("失败: {}".format(result3))
        else:
            data3 = result3.registers
            print("管控系统->自动接线工作站(bit), 返回信号: {}".format(data3))

        result4 = self.client.read_holding_registers(236)
        if result4.isError():
            print("失败: {}".format(result4))
        else:
            data4 = result4.registers
            print("管控系统->自动接线工作站(byte), 返回信号: {}".format(data4))


    def JJGZX_read(self):
        result1 = self.client.read_holding_registers(252)
        if result1.isError():
            print(result1.isError())
            print("失败: {}".format(result1))
        else:
            data1 = result1.registers
            print("机加工中心->管控系统(bit), 返回信号: {}".format(data1))

        result2 = self.client.read_holding_registers(254)
        if result2.isError():
            print(result2.isError())
            print("失败: {}".format(result2))
        else:
            data2 = result2.registers
            print("机加工中心->管控系统(byte), 返回信号: {}".format(data2))

        result3 = self.client.read_holding_registers(270)
        if result3.isError():
            print(result3.isError())
            print("失败: {}".format(result3))
        else:
            data3 = result3.registers
            print("管控系统->机加工中心(bit), 返回信号: {}".format(data3))

        result4 = self.client.read_holding_registers(272)
        if result4.isError():
            print(result4.isError())
            print("失败: {}".format(result4))
        else:
            data4 = result4.registers
            print("管控系统->机加工中心(byte), 返回信号: {}".format(data4))

    def JJGZX_write(self, flag1=0, flag2=1):
        try:
            result1 = self.client.write_register(address=270, value=flag1)
            result2 = self.client.write_register(address=272, value=flag2)
            
        except ConnectionException:
            return -1
        if result1.isError() or result2.isError():
            return -1
        else:
            print("启动 = {}, 工艺编号 = {}".format(flag1, flag2))
            return 1

    def MRFZJXGZZ_read(self):
        result1 = self.client.read_holding_registers(288)
        if result1.isError():
            print("失败: {}".format(result1))
        else:
            data1 = result1.registers
            print("MR->管控系统(bit), 返回信号: {}".format(data1))

        result3 = self.client.read_holding_registers(306)
        if result3.isError():
            print("失败: {}".format(result3))
        else:
            data3 = result3.registers
            print("管控系统->MR(bit), 返回信号: {}".format(data3))


orderID_count = int(time.time())# orderID的初始值

class Control_Signs:
    # 开始时间
    begin = None

    # 工位标志
    PAUSE_FLAG = False
    START_FLAG = False
    D_OVER_FLAG = False
    C_OVER_FLAG = False
    E_OVER_FLAG = False
    G_OVER_FLAG = False
    A_OVER_FLAG = False
    B_OVER_FLAG = False

    # AGV标志
    TRANSPORT_FLAG_C_TO_E=False #测试
    TRANSPORT_FLAG_D_TO_E=False
    TRANSPORT_FLAG_A_TO_B=False
    TRANSPORT_FLAG_F_TO_G=False
    TRANSPORT_FLAG_H_TO_F=False
    TRANSPORT_FLAG_C_TO_D=False
    TRANSPORT_FLAG_G_TO_H=False
    TRANSPORT_FLAG_B_TO_C=False
    TRANSPORT_FLAG_E_TO_A=False
    TRANSPORT_FLAG_K_TO_J=False

    FINISH_FLAG = False
    FINISH_AGV1_FLAG = False
    FINISH_AGV2_FLAG = False


    # AGV切换标志
    AGV2_FLAG = False
    AGV2_4_TO_3_FINISH_FLAG = False
    AGV2_3_TO_4_FINISH_FLAG = False

    # 固定信息
    # 设置各个工位的IP
    A_IP = 1
    D_IP = 1
    F_IP = 1
    JQ_IP = 1
    DZ_IP = 1
    ZDZP_IP = 1

    # AGV1移动到各个工位对应的任务号
    A_num = 1056
    B_num = 1006
    C_num = 1005
    D_num = 1055
    E_num = 1004
    F_num = 1009
    G_num = 1007
    H_num = 1008
    J_num = 1001
    K_num = 1002 # k to J


## 基本动作定义
# 任务状态查询
def Task_state_check(orderID):
    url = "http://192.168.1.71:7000/ics/out/task/getTaskOrderStatus"
    data={"orderId":str(orderID)}
    response = requests.post(url, json=data).json()
    return response['data']['taskOrderDetail'][0]['status']

# 任务终止
def cancel(orderID_count):
    url = "http://192.168.1.71:7000/ics/out/task/cancelTask"
    data = [{
        "orderId": str(orderID_count),
        "destPosition":""
    }]
    # 使用requests库发送POST请求
    response = requests.post(url, json=data)
    print('cancel response',response.json())

# AGV线程
# AGV1移动后停止
def move_stop_AGV1(destination, control_sign):
    global orderID_count
    url = "http://192.168.1.71:7000/ics/taskOrder/addTask"
    taskpath = str(destination)
    for i in range(3):
        taskpath = taskpath + ","+str(destination)

    data = {
        "areaId": 1,
        "fromSystem": "MainControlSystem",
        "modelProcessCode": str(3),
        "orderId": str(orderID_count),
        "priority": 1,
        "taskOrderDetail": [
            {
                "actionParam": "",
                "material": "",
                "shelfNumber": "",
                "storageNum": "",
                "taskPath": taskpath
            }
        ]
    }
    # 使用requests库发送POST请求
    response = requests.post(url, json=data)
    sleep_times = 0
    print(Task_state_check(orderID_count))
    while Task_state_check(orderID_count)!=6:  #等待AGV移动完毕
        if sleep_times % 100 == 0:
            print('response',response.json())
            print('status',Task_state_check(orderID_count))  # 打印对应任务状态
        time.sleep(0.02)
        sleep_times = sleep_times + 1

        # if destination == control_sign.C_num:
        #     STOP_OVER_FLAG = control_sign.C_OVER_FLAG
        # elif destination == control_sign.G_num:
        #     STOP_OVER_FLAG = control_sign.G_OVER_FLAG
        # elif destination == control_sign.E_num:
        #     STOP_OVER_FLAG = control_sign.E_OVER_FLAG
        # else:
        #     STOP_OVER_FLAG = False
        #
        # if STOP_OVER_FLAG:
        #     print('stopping is over!continue next task.', response.json())
        #     cancel(orderID_count)
        #     time.sleep(0.1)
        #     break

    print('response', response.json())
    print('status', Task_state_check(orderID_count))

    orderID_count = orderID_count+1  # 每运行一次MOVE都会增加一个orderID
    print('AGV1 move stop over!')

# AGV1从起点搬到终点
def transport_AGV1(origin, destination):
    global orderID_count
    url = "http://192.168.1.71:7000/ics/taskOrder/addTask"
    data = {
        "areaId": 1,
        "fromSystem": "MainControlSystem",
        "modelProcessCode": str(1),
        "orderId": str(orderID_count),
        "priority": 6,
        "taskOrderDetail": [
            {
                "actionParam": "",
                "material": "",
                "shelfNumber": "",
                "storageNum": "",
                "taskPath": str(origin) + "," + str(destination)
            }
        ]
    }
    # 使用requests库发送POST请求
    response = requests.post(url, json=data)

    sleep_times = 0
    while Task_state_check(orderID_count)!=8:  #等待AGV移动完毕
        if sleep_times % 100 == 0:
            print('response',response.json())
            print('status',Task_state_check(orderID_count))  # 打印对应任务状态
        time.sleep(0.02)
        sleep_times = sleep_times + 1

    print('response', response.json())
    print('status', Task_state_check(orderID_count))

    orderID_count = orderID_count+1  # 每运行一次MOVE都会增加一个orderID
    print('AGV1 transportation over!')

#AGV2移动
def move_AGV2(destination):
    global orderID_count
    url = "http://192.168.1.71:7000/ics/taskOrder/addTask"

    data = {
        "areaId": 1,
        "fromSystem": "MainControlSystem",
        "modelProcessCode": str(2),
        "orderId": str(orderID_count),
        "priority": 1,
        "taskOrderDetail": [
            {
                "actionParam": "",
                "material": "",
                "shelfNumber": "",
                "storageNum": "",
                "taskPath": str(destination)+","+str(destination)
            }
        ]
    }
    # 使用requests库发送POST请求
    response = requests.post(url, json=data)
    sleep_times = 0
    while Task_state_check(orderID_count) != 8:  # 等待AGV移动完毕
        if sleep_times % 100 == 0:
            print('response', response.json())
            print('status', Task_state_check(orderID_count))  # 打印对应任务状态
        time.sleep(0.02)
        sleep_times = sleep_times + 1

    print('response', response.json())
    print('status', Task_state_check(orderID_count))
    orderID_count = orderID_count+1  # 每运行一次MOVE都会增加一个orderID
    print('AGV2 move over!')

def deviceInfo():
    url = "http://192.168.1.71:7000/ics/out/device/list/deviceInfo"
    data = {
        "areaId": 1,
        "deviceType": 0,
    }
    # 使用requests库发送POST请求
    response = requests.post(url, json=data)
    position_AGV1 = response.json()['data'][0]['devicePostionRec']
    position_AGV2 = response.json()['data'][1]['devicePostionRec']

    position_dictionary = {"AGV1": position_AGV1, "AGV2": position_AGV2}
    return position_AGV1, position_AGV2


def GPS_process(control_sign):
    # 清空json文件
    data = {}
    with open("position_data.json", "w") as file:
        json.dump(data, file)
    print("begin to record!")
    begin_time = time.time()
    # 持续询问，更新json文件
    while True:
        position_AGV1, position_AGV2 = deviceInfo()
        new_data = {time.time() - begin_time: {"AGV1": position_AGV1, "AGV2": position_AGV2}}
        with open("position_data.json", "r") as file:
            try:
                existing_data = json.load(file)
            except Exception:
                print("empty file")
        existing_data.update(new_data)
        with open("position_data.json", "w") as file:
            json.dump(existing_data, file)
        # 停止查询条件，可以写个键盘监听器停止
        if control_sign.FINISH_FLAG:
            print("GPS stops")
            break


# AGV1主线程
def AGV1_process(control_sign):
    # 检查是否可以开始AGV的运动
    while True:
        print("Waiting for start..")
        time.sleep(0.5)
        if control_sign.START_FLAG:
            print("AGV1 starts to work!")
            break
    # # AGV进程已经开启，从K搬到J
    print("AGV1 starts to transport from K to J!")
    transport_AGV1(control_sign.K_num, control_sign.J_num)
    control_sign.TRANSPORT_FLAG_K_TO_J = True

    # 从D搬到E
    print("AGV1 starts to transport from D to E!")
    transport_AGV1(control_sign.D_num, control_sign.E_num)
    control_sign.TRANSPORT_FLAG_D_TO_E = True

    # # 搬到E后，直接从A搬到B
    # print("AGV1 starts to move to A and stop at A!")
    # # 一直停止
    # while not control_sign.A_OVER_FLAG:
    #     move_stop_AGV1(control_sign.A_num, control_sign)
    #
    # print("AGV1 starts to move to B and stop at B!")
    # # 一直停止
    # while not control_sign.B_OVER_FLAG:
    #     move_stop_AGV1(control_sign.B_num, control_sign)

    # control_sign.TRANSPORT_FLAG_A_TO_B = True
    print("AGVs start to transport from A to B!")
    transport_AGV1(control_sign.A_num, control_sign.B_num)
    control_sign.TRANSPORT_FLAG_A_TO_B = True
    # 搬到B后，直接从F搬到G
    print("AGV1 starts to transport from F to G!")
    transport_AGV1(control_sign.F_num, control_sign.G_num)
    control_sign.TRANSPORT_FLAG_F_TO_G = True

    # 搬到G后，直接从H搬到F
    print("AGV1 starts to transport from H to F!")
    transport_AGV1(control_sign.H_num, control_sign.F_num)
    control_sign.TRANSPORT_FLAG_H_TO_F = True

    # 等一会儿 AGV2开始工作
    time.sleep(10)
    control_sign.AGV2_FLAG = True # AGV2开始工作

    # 空载去C，等待C完成，然后从C搬到D
    # print("AGV1 starts to move to C and stop at C!")
    # AGV2_Begin_FLAG = False
    # while not control_sign.C_OVER_FLAG:
    #     move_stop_AGV1(control_sign.C_num, control_sign)
    #     if not AGV2_Begin_FLAG:
    #         control_sign.AGV2_FLAG = True
    #         AGV2_Begin_FLAG = True
    # print("station C is over!")
    # print("AGVs start to transport from C to D!")
    # while not control_sign.D_OVER_FLAG:
    #     move_stop_AGV1(control_sign.D_num, control_sign)
    # # transport_AGV1(control_sign.C_num, control_sign.D_num)
    #control_sign.TRANSPORT_FLAG_C_TO_D = True
    #
    # # 空载去G，等待G完成，然后从G搬到H
    # print("AGVs start to move to G and stop at G!")
    # while not control_sign.G_OVER_FLAG:
    #      move_stop_AGV1(control_sign.G_num, control_sign)
    # print("station G is over!")
    # print("AGVs start to transport from G to H!")
    # transport_AGV1(control_sign.G_num, control_sign.H_num)
    # control_sign.TRANSPORT_FLAG_G_TO_H = True
    #
    # # 搬到H后，直接从B搬到C
    # print("AGVs start to transport from B to C!")
    # transport_AGV1(control_sign.B_num, control_sign.C_num)
    # control_sign.TRANSPORT_FLAG_B_TO_C = True
    #
    # # # 空载去E，等待E完成，然后从E搬到A
    # print("AGVs start to move to E and stop at E!")
    # while not control_sign.E_OVER_FLAG:
    #     move_stop_AGV1(control_sign.E_num, control_sign)
    # print("E is over!")
    # print("AGVs start to transport from E to A!")
    # #transport_AGV1(control_sign.E_num, control_sign.A_num)
    # control_sign.TRANSPORT_FLAG_E_TO_A = True

    # # 结束
    print("AGV1 works over!")
    # 自动回到原点
    control_sign.FINISH_AGV1_FLAG = True


# AGV2线程
def AGV2_process(control_sign):
    #  server
    server = socket.socket()  # 创建socket对象
    ip_port = ('192.168.1.69', 7000)  # 给程序设置一个ip地址和端口号
    server.bind(ip_port)  # 绑定ip地址和端口
    sleep_times = 0
    # 等待AGV2运动信号
    while True:
        if control_sign.AGV2_FLAG:
            print("begin to connect")
            break
    # 一开始就连接上
    while True:
        server.listen()  # 监听ip地址和端口，简称开机
        conn, addr = server.accept()  # 等待建立连接  conn是连接通道，addr是客户端的地址
        from_client_mag = conn.recv(1024)  # 服务端通过conn连接来收发消息，通过recv方法，recv里面的参数是字节（B），1024B=1KB
        request_str = "\x4D\x45\x53\x05\x01\x01\x02\x0D\x0A"
        if from_client_mag == request_str.encode('utf-8'):
            print("connection success!")
            break
    # AGV2开始从4搬到3
    if not control_sign.FINISH_FLAG:
        print("AGV2 starts to work and transport from 4 to 3")
        transport_code = b'MES\x08\x03\x06\x04\x03\x01\x11\r\n'
        conn.send(transport_code)  # 回复消息，通过send方法，由于接收的消息是字节类型的，所以也要发送字节类型的
        msg = conn.recv(64)
        print("response:", msg)
    # 查询从4搬到3状态
    while not control_sign.AGV2_4_TO_3_FINISH_FLAG and not control_sign.FINISH_FLAG:
        query_code = b'MES\x05\x02\x01\x03\r\n'
        conn.send(query_code)
        msg = str(conn.recv(1024))
        time.sleep(0.5)
        sleep_times = sleep_times + 1
        if sleep_times % 10 == 0:
            print("not working : 4 to 3 : AGV2 state", msg[22])
            sleep_times = 0
        if msg[22] == "4":
            while not control_sign.FINISH_FLAG:
                conn.send(query_code)
                msg = str(conn.recv(1024))
                time.sleep(0.5)
                sleep_times = sleep_times + 1
                if sleep_times % 10 == 0:
                    print("working : 4 to 3 : AGV2 state", msg[22])
                    sleep_times = 0
                if msg[22] == "1":
                    print("4 to 3 works over")
                    control_sign.AGV2_4_TO_3_FINISH_FLAG = True
                    break
    # 等待一会儿开始下一个动作
    time.sleep(5)

    # AGV2开始从3搬到4
    if not control_sign.FINISH_FLAG:
        print("AGV2 starts to work and transport from 3 to 4")
        transport_code = b'MES\x08\x03\x06\x03\x04\x0B\x1B\r\n'
        conn.send(transport_code)  # 回复消息，通过send方法，由于接收的消息是字节类型的，所以也要发送字节类型的
        try:
            msg = conn.recv(64)
            print("3 to 4: response:", msg)
        except Exception:
            print("transport no return")
    # 查询从3搬到4状态

    while not control_sign.AGV2_3_TO_4_FINISH_FLAG and not control_sign.FINISH_FLAG:
        query_code = b'MES\x05\x02\x01\x03\r\n'
        try:
            conn.send(query_code)
            msg = str(conn.recv(1024))
            time.sleep(0.5)
            sleep_times = sleep_times + 1
            if sleep_times % 10 == 0:
                print("not working: 3 to 4: AGV2 state", msg[22])
                sleep_times = 0
            if msg[22] == "4":
                while not control_sign.FINISH_FLAG:
                    conn.send(query_code)
                    msg = str(conn.recv(1024))
                    time.sleep(0.5)
                    sleep_times = sleep_times + 1
                    if sleep_times % 10 == 0:
                        print("working : 3 to 4 : AGV2 state", msg[22])
                        sleep_times = 0
                    if msg[22] == "1":
                        print("working : 3 to 4 : AGV2 state", msg[22])
                        print("3 to 4 works over")
                        control_sign.AGV2_3_TO_4_FINISH_FLAG = True
                        break
        except ConnectionResetError:
            print("network error!")
            break


    print("AGV2 works over!")
    control_sign.FINISH_AGV2_FLAG = True

def on_press(key):
    try:
        if key.char == 's':
            print('you pressed the s key!')
            control_sign.START_FLAG = True
        # elif key.char == 'd':
        #     print('you pressed the d key!')
        #     control_sign.D_OVER_FLAG = True
        # elif key.char == 'e':
        #     print('you pressed the e key!')
        #     control_sign.E_OVER_FLAG = True
        # elif key.char == 'g':
        #     print('you pressed the g key!')
        #     control_sign.G_OVER_FLAG = True
        # elif key.char == 'a':
        #     print('you pressed the a key!')
        #     control_sign.A_OVER_FLAG = True
        # elif key.char == 'b':
        #     print('you pressed the b key!')
        #     control_sign.B_OVER_FLAG = True
        # elif key.char == '2':
        #     print('you press the 2 key')
        #     control_sign.AGV2_FLAG = True
        
        # elif key.char == '1':
        #     print('you pressed the 1 key')
        #     control_sign.TRANSPORT_FLAG_K_TO_J = True
        # elif key.char == '2':
        #     print('you pressed the 2 key')
        #     control_sign.TRANSPORT_FLAG_D_TO_E = True
        # elif key.char == '3':
        #     print('you pressed the 3 key')
        #     control_sign.TRANSPORT_FLAG_A_TO_B = True
        # elif key.char == '4':
        #     print('you pressed the 4 key')
        #     control_sign.TRANSPORT_FLAG_F_TO_G = True
        # elif key.char == '5':
        #     print('you pressed the 5 key')
        #     control_sign.TRANSPORT_FLAG_H_TO_F = True        
        # elif key.char == '6':
        #     print('you pressed the 6 key')
        #     control_sign.FINISH_AGV1_FLAG = True
        # elif key.char == '7':
        #     print('you pressed the 7 key')
        #     control_sign.FINISH_AGV2_FLAG = True
        
        elif key.char == 'f':
            print('finished!')
            control_sign.FINISH_FLAG = True
    except AttributeError:
        print('press error')

def get_main_Button(client):
    
    global main_Button
    while True:
        time.sleep(0.1)
        try:
            result = client.read_discrete_inputs(0)
        
        except ConnectionException:
            continue
        
        if result.isError():
            print("失败: {}".format(result))
        
        else:
            main_Button = result.bits[0]
            # if main_Button == True:
            #     print("Main button pressed! System start! main_Button = {}".format(main_Button))
            # else:
            #     print("Main button up! System stop! main_Button = {}".format(main_Button))



if __name__ == "__main__":

    main_Button = False
    try_modbus_connection_max_num = 100

    client = ModbusTcpClient('localhost')
    # client = ModbusTcpClient('192.168.1.66')
    
    client.connect()

    main_Button_thread = threading.Thread(target=get_main_Button, args=[client])
    main_Button_thread.setDaemon(True)
    main_Button_thread.start()

    control_sign = Control_Signs()

    while not control_sign.FINISH_FLAG:
        if main_Button:

            control_sign.START_FLAG = True

            control_sign.begin = time.time()

            fmlRobot = fmlROBOT()

            AGV1_thread = threading.Thread(target=AGV1_process, args=[control_sign])
            AGV2_thread = threading.Thread(target=AGV2_process, args=[control_sign])
            # GPS_thread = threading.Thread(target=GPS_process, args=[control_sign])
            # listener = keyboard.Listener(on_press=on_press)

            AGV1_thread.setDaemon(True)
            AGV2_thread.setDaemon(True)
            # GPS_thread.setDaemon(True)
            # listener.setDaemon(True)

            AGV1_thread.start()
            AGV2_thread.start()
            # GPS_thread.start()
            # listener.start()
            # 键盘监听

            # 模拟工位开始信号
            # control_sign.begin=time.time()
            # while not control_sign.FINISH_FLAG:
            #     if control_sign.START_FLAG:
            #         break


            # 启动C工位（剪切）
            if not control_sign.FINISH_FLAG:
                Cok1 = -1
                for i in range(try_modbus_connection_max_num):
                    Cok1 = fmlRobot.JQZX_write(0, 1, 256)
                    if Cok1 == 1:
                        print("C ROBOT success")

                        client.write_coil(24, 1)

                        break
                    else:
                        print("Try {} time(s), J connection failed!".format(i+1))
                    if i+1 == try_modbus_connection_max_num:
                        control_sign.FINISH_FLAG = True
                        print("C ROBOT error! Finish process")

            # 从K运到J
            begin_K = time.time()
            while not control_sign.FINISH_FLAG:
                if control_sign.TRANSPORT_FLAG_K_TO_J:
                    # 从D运到E结束
                    print("AGV1 has transported from K to J")
                    print(time.time() - begin_K, "s is used!")
                    break
        
            # 启动J工位
            if not control_sign.FINISH_FLAG:
                Jok1 = -1
                print("Jok1 = -1!!!")
                for i in range(try_modbus_connection_max_num):
                    print("Jok1 = fmlRobot.JJGZX_write(1)!!!")
                    Jok1 = fmlRobot.JJGZX_write(1)
                    if Jok1 == 1:
                        print("J ROBOT success")

                        client.write_coil(8, 1)

                        break
                    else:
                        print("Try {} time(s), J connection failed!".format(i+1))
                    if i+1 == try_modbus_connection_max_num:
                        control_sign.FINISH_FLAG = True
                        print("J ROBOT error! Finish process")
        
            # 从D运到E
            begin_D = time.time()
            while not control_sign.FINISH_FLAG:
                if control_sign.TRANSPORT_FLAG_D_TO_E:
                    # 从D运到E结束
                    print("AGV1 has transported from D to E")
                    print(time.time() - begin_D, "s is used!")
                    break
        
            # 启动E工位
            if not control_sign.FINISH_FLAG:
                Jok2 = -1
                # Jok3 = -1
                for i in range(try_modbus_connection_max_num):
                    Jok2 = fmlRobot.JJGZX_write(3)   # 在当前时序下可以，修改移动速度、AGV轨迹等可能出问题
                    # Jok3 = fmlRobot.JJGZX_write(0)
                    if Jok2 == 1:
                        client.write_coil(8, 0)
                        break
                    else:
                        print("Try {} time(s), J connection failed!".format(i+1))
                    if i+1 == try_modbus_connection_max_num:
                        control_sign.FINISH_FLAG = True
                        print("J ROBOT error! Finish process")

            if not control_sign.FINISH_FLAG:
                Eok1 = -1
                Eok2 = -1
                for i in range(try_modbus_connection_max_num):
                    Eok1 = fmlRobot.DZZPZX_write(1)
                    time.sleep(1)
                    Eok2 = fmlRobot.DZZPZX_write(0)
                    if Eok1 == 1 and Eok2 == 1:
                        print("E ROBOT success")

                        client.write_coil(16, 1)

                        break
                    else:
                        print("Try {} time(s), E connection failed!".format(i+1))
                    if i+1 == try_modbus_connection_max_num:
                        control_sign.FINISH_FLAG = True
                        print("E ROBOT error! Finish process")
        

            # # 直接从A运到B，检查运输是否结束
            begin_A = time.time()
            while not control_sign.FINISH_FLAG:
                if control_sign.TRANSPORT_FLAG_A_TO_B:
                    print("AGV1 has transported from A to B")
                    print(time.time() - begin_A, "s is used!")            # 从A运到B结束
                    break
            # 直接从F运到G，检查运输是否结束
            begin_F = time.time()
            while not control_sign.FINISH_FLAG:
                if control_sign.TRANSPORT_FLAG_F_TO_G:
                    print("AGV1 has transported from F to G")
                    print(time.time() - begin_F, "s is used!")  # 从A运到B结束
                    break

            # 启动G工位
            if not control_sign.FINISH_FLAG:
                Gok1 = -1
                Gok2 = -1
                for i in range(try_modbus_connection_max_num):
                    Gok1 = fmlRobot.ZDZPGZZ_write(7)
                    time.sleep(5)
                    Gok2 = fmlRobot.ZDZPGZZ_write(0)
                    
                    if Gok1 == 1 and Gok2 == 1:
                        print("G ROBOT success")

                        client.write_coil(32, 1)

                        break
                    else:
                        print("Try {} time(s), G connection failed!".format(i+1))
                    if i+1 == try_modbus_connection_max_num:
                        control_sign.FINISH_FLAG = True
                        print("G ROBOT error! Finish process")


            # 直接从H运到F，检查运输是否结束
            begin_H = time.time()
            while not control_sign.FINISH_FLAG:
                if control_sign.TRANSPORT_FLAG_H_TO_F:
                    print("AGV1 has transported from H to F")
                    print(time.time() - begin_H, "s is used!")  # 从h运到F结束
                    break
            

            # 保护程序
            while True:
                if control_sign.FINISH_AGV1_FLAG and control_sign.FINISH_AGV2_FLAG:
                    control_sign.FINISH_FLAG = True
                    client.write_coil(8*1,0)
                    client.write_coil(8*2,0)
                    client.write_coil(8*3,0)
                    client.write_coil(8*4,0)
                    break
                elif control_sign.FINISH_FLAG:
                    break
           
"""

detect_template = """
import json
import cv2
import numpy as np
import os
from time import sleep
import paramiko
import requests
import random
from filelock import FileLock

import posix_ipc
from multiprocessing import shared_memory, resource_tracker
import ctypes

def connect_arm(type):
    try:
        with FileLock("robot_arm.lock"):
            print("Arm connecting……")
            ssh = paramiko.SSHClient()
            print("start to connect arm")
            ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            ssh.connect(hostname='192.168.2.150', port=22, username='ubuntu', password='ubuntu')
            print("ssh successfully!!!!")
            if type == "crack":
                stdin, stdout, stderr = ssh.exec_command('sudo python3 /home/ubuntu/Ai_FPV/YDS/turnRightCrack.py')
            elif type== "scar":
                stdin, stdout, stderr = ssh.exec_command('sudo python3 /home/ubuntu/Ai_FPV/YDS/turnRightScar.py')
            elif type== "rippled":
                stdin, stdout, stderr = ssh.exec_command('sudo python3 /home/ubuntu/Ai_FPV/YDS/turnRightRippled.py')
            print(stdout.read().decode())

            ssh.close()

    except Exception as e:
        print(e)


print("Start!!!!")

# fifo_path1 = "/../sensor_data/{ITOT_value}"
# fifo_path = os.path.normpath(os.path.dirname(os.path.abspath(__file__)) + fifo_path1)
# 链接信号量
sem = posix_ipc.Semaphore("/semaphore1")
# 连接到名为 "steel" 的共享内存块
shm = shared_memory.SharedMemory(name="steel")
# 使用 ctypes 将共享内存映射为一个整数
shared_int = ctypes.c_int.from_buffer(shm.buf)
# 取消资源跟踪，在另一个内存中取消
resource_tracker.unregister(shm._name, "shared_memory")

ip = '{ip}'
port = 8910
url = f"http://{{ip}}:{{port}}"

# 向边缘计算节点发送开启相机的指令
url_process = url + '/process'
data = [{{
    'camera_address': '{camera_address}',
    'camera_id': {camera_id},
    'is_open':1,
    'priority':0,
    'pipeline':['camera','{algorithm}','result']
}}]
response = requests.post(url_process,data=json.dumps(data))
print('Status Code:', response.status_code)
print('Response Body:', response.text)
#sleep(10)# 等待信息返回

num_true = 0

while True:
    sleep(0.1)
    
    sem.acquire()  # 获取信号量
    if shared_int.value ==1:
        message = "True"
    else:
        message = "False"
    sem.release()  # 释放信号量

    if message == "True" and num_true == 0:
        num_true = num_true + 1
        print("Item!!!!!!!!")
        # 向边缘计算节点发送开启相机的指令
        # url_process = url + '/process'
        # response = requests.post(url_process,data=json.dumps(data))
        # print('Status Code:', response.status_code)
        # print('Response Body:', response.text)
        # sleep(4)# 等待信息返回
while True:
    sleep(0.1)
        
    sem.acquire()  # 获取信号量
    if shared_int.value ==1:
        message = "True"
    else:
        message = "False"
    sem.release()  # 释放信号量

    if message == "True" and num_true == 0:
        num_true = num_true + 1
        print("Item!!!!!!!!")
            # 向边缘计算节点发送开启相机的指令
            # url_process = url + '/process'
            # response = requests.post(url_process,data=json.dumps(data))
            # print('Status Code:', response.status_code)
            # print('Response Body:', response.text)
            # sleep(4)# 等待信息返回
        print("Call message!!!!!!")
        url_result = url + '/result/{camera_id}'
        sleep(2)
        response = requests.get(url_result)
        print('Status Code:', response.status_code)
            # 假设对方是返回json数组
        response_data = json.loads(response.text)
        print("Get message!!!!!!")
        if response_data.get('is_ok')==0:
            print("Good!")
        else:
            type = response_data.get('type')
            print(f"Get {{type}}!!!!!!")
            connect_arm(type)


            # type = "crack" # 生成1~4之间的随机整数，替代返回的整数
            # print("准备连接机械臂……")
            # connect_arm(type)

    elif message == "False":
        num_true = 0

"""

terminal_detect_template = """
import json
import cv2
import numpy as np
import os
from time import sleep
import paramiko
import requests
import random
from filelock import FileLock

import ctypes
import posix_ipc
import mmap
import struct

ip = '{ip}'
port = 8910
url = f"http://{{ip}}:{{port}}"

# 向边缘计算节点发送开启相机的指令
url_process = url + '/process'
data = [{{
    'camera_address': '{camera_address}',
    'camera_id': {camera_id},
    'is_open':1,
    'priority':0,
    'pipeline':['camera','{algorithm}','result']
}}]
response = requests.post(url_process,data=json.dumps(data))
print('Status Code:', response.status_code)
print('Response Body:', response.text)
#sleep(10)# 等待信息返回

# 共享变量button
# 读取变量控制
button = False

# 链接信号量
sem_button = posix_ipc.Semaphore("/button_semaphore1")
sem_switch = posix_ipc.Semaphore("/switch_semaphore1")

# 连接到共享内存块
shm_button = posix_ipc.SharedMemory("/button")
shm_switch = posix_ipc.SharedMemory("/switch")

# 使用 mmap 将共享内存映射为一个整数
mmy_button = mmap.mmap(shm_button.fd,shm_button.size)
mmy_switch = mmap.mmap(shm_switch.fd,shm_button.size)

try:
    while True:
        sleep(0.5)
        
        sem_button.acquire()  # 获取信号量
        if struct.pack('i', mmy_button[:4])[0] ==1:
            button = "True"
        else:
            button = "False"
        sem_button.release()  # 释放信号量
        
        
        if button:
            url_result = url + '/result/{camera_id}'
            response = requests.get(url_result)
            print('Status Code:', response.status_code)
            # 假设对方是返回json数组
            response_data = json.loads(response.text)
            if response_data.get('is_ok')==0:
                print("Good!")
                sem_switch.acquire()  # 获取信号量
                mmy_switch[:] =struct.pack('i', 0)
                sem_switch.release()  # 释放信号量
            else:
                # 装配完备，共享变量置true
                sem_switch.acquire()  # 获取信号量
                mmy_switch[:] =struct.pack('i', 1)
                sem_switch.release()  # 释放信号量
                type = response_data.get('type')
except KeyboardInterrupt:
    print("\n程序被中断，正在清理资源...")

finally:
    # 无论如何，最终都要执行资源清理
    print("关闭共享内存和文件描述符")
    mmy_button.close()  # 关闭内存映射
    shm_button.close_fd()  # 关闭共享内存的文件描述符

        # type = "crack" # 生成1~4之间的随机整数，替代返回的整数
        # print("准备连接机械臂……")
        # connect_arm(type)

    elif message == "False":
        num_true = 0

    mmy_switch.close()  # 关闭内存映射
    shm_switch.close_fd()  # 关闭共享内存的文件描述符

    # 可以显式关闭
    # 删除信号量
    sem_button.unlink()
    sem_switch.unlink()
"""

def generate_ydspycode(data, code_template):
    current_path = os.path.dirname(__file__)
    output_path = os.path.join(current_path, "ydsdata_output.json")
    with open(output_path,'w') as f:
        json.dump(data, f)
    # default camera ID
    camID = 1
    codes = []
    params = []
    Sched = False
    for key, value in data.items():
        if value['type'] == 'ITOT':
            param = {}
            param['fifo'] = value['name']
            outputs = value['output']
            grabs = []
            while len(outputs) > 0:
                for output in outputs:
                    block = data[output['id']]
                    port = output['port']
                    if block['type'] == 'Camera':
                        param['camID'] = int(block['camera']['ID'])
                        if block['name'] == 'camera1':
                            param['beltID'] = 0
                        elif block['name'] == 'camera2':
                            param['beltID'] = 1
                        outputs = block['output']
                    elif block['type'] == 'Detect':
                        outputs = block['output']
                    elif block['type'] == 'scheduler':
                        outputs = block['output']
                        inputs = block['input']
                        for input in inputs:
                            inblock = data[input['id']]
                            if inblock['type'] == 'Variable' and inblock['name'] == '1':
                                Sched = True
                    elif block['type'] == 'Grab':
                        outputs = block['output']
                        inputs = block['input']
                        for input in inputs:
                            inblock = data[input['id']]
                            if inblock['type'] == 'Variable' and inblock['name'] == '1':
                                Sched = True
            params.append(param)           
    code = code_template.format(Sched=Sched, sensor_fifo1=params[0]['fifo'], sensor_fifo2=params[1]['fifo'], belt1_index=params[0]['beltID'], belt2_index=params[1]['beltID'], camera1_index=params[0]['camID'], camera2_index=params[1]['camID'])
    codes.append(code)

    return codes

def generate_njupycode(data, code_template):
    bodys = []
    ip = "127.0.0.1"
    port = "5000"
    for key, value in data.items():
        if value['type'] == 'Camera':
            body = {}
            body = value['camera']
            prog = data[value['output'][0]['id']]
            body.update(prog['proData'])
            dataflag = data[prog['output'][0]['id']]
            body.update({"DataFlag": dataflag['DataFlag']})
            bodys.append(body)
    code = code_template.format(ip=ip,port=port,bodys=bodys)
    # with open(os.path.join(current_path, 'njuITprogram' + str(0) + '.py'), 'w') as f:
    #     f.write(code)
    # process = subprocess.Popen(['python', os.path.join(current_path, 'njuITprogram' + str(0) + '.py')])
    # print(process.pid)

    return code

def generate_fmlpycode(data, code_template):
    code = code_template
    return code

def generate_detectpycode(data, code_template):
    for key, value in data.items():
        if value['type'] == 'Camera':
            ip = value['camera']['Res']
            camera_address = value['camera']['Addr']
            camera_id = value['camera']['ID']
        if value['type'] == 'Detect':
            algorithm = 'steel_detection'
        if value['type'] == 'ITOT':
            ITOT_value = value['name']

    code = code_template.format(ip=ip, algorithm=algorithm, ITOT_value=ITOT_value,camera_address=camera_address,
                                camera_id=camera_id)

    return code

def generate_TerminalDetectPycode(data, code_template):
    for key, value in data.items():
        if value['type'] == 'Camera':
            ip = value['camera']['Res']
            Addr = value['camera']['Addr']
            camera_address = 'rtsp://' + Addr + ':8554/stream0'
            camera_id = value['camera']['ID']
        if value['type'] == 'Detect':
            algorithm = 'terminal_assembly_detection'

    code = code_template.format(ip=ip, algorithm=algorithm, camera_address=camera_address,
                                camera_id=camera_id)
    return code