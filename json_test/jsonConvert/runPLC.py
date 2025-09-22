import requests
import os
import platform
import json

def get_desktop_path():
    if platform.system() == "Windows":
        desktop = os.path.join(os.path.join(os.environ['USERPROFILE']), 'Desktop')
    elif platform.system() == "Linux":
        desktop = os.path.join(os.path.join(os.path.expanduser('~')), 'Desktop')
    return desktop

ProjectPath = get_desktop_path()

url_file = os.path.join(ProjectPath, 'config.json')
with open(url_file, 'r') as f:
    config = json.load(f)
    url = config['planturl']

url = 'http://'+url+ ':5001'

def start_plc():
    url_start_plc=url+'/run'
    response = requests.get(url_start_plc)
    print('Status Code:', response.status_code)
    print('Response Body:', response.text)
    if response.status_code == 200:
        print('PLC started')
    else:
        print('PLC not started')

start_plc()
