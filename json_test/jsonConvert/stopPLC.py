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

def stop_plc():
    url_stop_plc = url + '/stop'
    response = requests.get(url_stop_plc)
    print('Status Code:', response.status_code)
    print('Response Body:', response.text)

def upload_file(file_path):
    if not file_path.endswith('.st'):
        print("Invalid file type. Only .st files are supported.")
        exit()
    files = {'file': open(file_path, 'rb')}
    url_file = url+'/upload'
    response = requests.post(url_file, files=files)
    print('Status Code:', response.status_code)
    print('Response Body:', response.text)

def upload_IT_file(file_path):
    files = {'file': open(file_path, 'rb')}
    url_file = url+'/uploadIT'
    response = requests.post(url_file, files=files)
    print(response.text)

def stop_IT_file(filename):
    # url_file =  f'{url}/stopIT/{filename}'
    url_file = url+'/stopIT/'+filename
    print(url_file)
    response = requests.get(url_file)
    print(response.text)

def get_IT_files():
    files = []
    print('aaaaaaaaa')
    for i in range(0, 100):
        # filename = f'{ProjectPath}/ITprogram{i}.py'
        filename = 'ITprogram' + str(i) + '.py'
        global_filename = ProjectPath + '/ITprogram' + str(i) + '.py'
        if os.path.exists(global_filename):
            files.append(filename)
    return files

try:
    for file in get_IT_files(): 
        print(file)
        stop_IT_file(file)
except:
    print('')

stop_plc()


