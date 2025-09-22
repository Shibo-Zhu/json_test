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

class RequestQueue_without_sched:
    def __init__(self):
        self.requests = []
        self.lock = threading.Lock()

    def add_request(self, timestamp, color, belt_index):
        with self.lock:
            self.requests.append((timestamp, color, belt_index))


    def process_request(self):
        if self.requests:
            earliest_request = min(self.requests, key=lambda x: x[0])
            with self.lock:
                self.requests.remove(earliest_request)
            return earliest_request

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

Sched = {Sched}

if Sched:
    task_queue = RequestQueue_sched()
else:
    task_queue = RequestQueue_without_sched()

fifo_path1 = "/../sensor_data/{sensor_fifo1}"
fifo_path2 = "/../sensor_data/{sensor_fifo2}"

fifo_path1 = os.path.normpath(os.path.dirname(os.path.abspath(__file__)) + fifo_path1)
fifo_path2 = os.path.normpath(os.path.dirname(os.path.abspath(__file__)) + fifo_path2)

belt1_index = {belt1_index}
belt2_index = {belt2_index}
camera1_index = {camera1_index}
camera2_index = {camera2_index}
thread1 = threading.Thread(target=process_conveyor, args=(fifo_path1, camera1_index,belt1_index, task_queue))
thread2 = threading.Thread(target=process_conveyor, args=(fifo_path2, camera2_index, belt2_index, task_queue))
scheduler_thread = threading.Thread(target=scheduler, args=(task_queue,))

thread1.start()
thread2.start()
scheduler_thread.start()

thread1.join()
thread2.join()
scheduler_thread.join()

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
            prog = data[str(value['output'][0]['id'])]
            body.update(prog['proData'])
            dataflag = data[str(prog['output'][0]['id'])]
            body.update({"DataFlag": dataflag['DataFlag']})
            bodys.append(body)
    code = code_template.format(ip=ip,port=port,bodys=bodys)
    # with open(os.path.join(current_path, 'njuITprogram' + str(0) + '.py'), 'w') as f:
    #     f.write(code)
    # process = subprocess.Popen(['python', os.path.join(current_path, 'njuITprogram' + str(0) + '.py')])
    # print(process.pid)

    return code

# current_path = os.path.dirname(__file__)
# filename = 'ydsITproject.json'
# current_path = os.path.dirname(__file__)
# output_path = os.path.join(current_path, "ydsdata_output.json")
# with open(output_path,'r') as f:
#     data = json.load(f)
    # code = generate_ydspycode(data, ydscode_template)