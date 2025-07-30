import glob
import math
import platform
import re
import time
import requests
from flask_apscheduler import APScheduler
from flask import *
from flask_socketio import *
import psutil
import copy
import cpuinfo
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
import subprocess
import ping3
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

app = Flask(__name__)
socketio = SocketIO(app, cors_allowed_origins='*')
BASIC_PATH = "/root/MaiMBot/MaiBot/logs"
serviceList = [{"name": "MaiBot-Core", "service": "maiBot", "ping": False, "status": False},
               {"name": "MaiBot-Napcat-Adapter", "service": "maiAda", "ping": False, "status": False},
               {"name": "Napcat", "service": False, "ping": "https://bot.hshidianlu.site:1234", "status": False}]
APIList = [{"name": "DeepSeek", "url": "api.deepseek.com", "status": False, "ping": -1},
           {"name": "SiliconFlow", "url": "api.siliconflow.cn", "status": False, "ping": -1},
           {"name": "火山引擎", "url": "ark.cn-beijing.volces.com", "status": False, "ping": -1}]


class Config(object):
    SCHEDULER_API_ENABLED = True
    SECRET_KEY = "P<IJL_[/c@@Y#'*A&A{:6:Y7Ur])+,v}>l*kSAOOK3z9L_,U-Hh!SJhw<{9lWW}Ad+nlNj@8F9;2h|flmott8%12g*1:a}Cp!;.X"


limiter = Limiter(app=app, default_limits=["5/second", "50/minute", "10000/day"], key_func=get_remote_address,
                  storage_uri="redis://default:XGf0vSksWTJXJW7e@38.207.185.236:6379/1")

app.config.from_object(Config())

scheduler = APScheduler()
scheduler.init_app(app)
scheduler.start()

cpuCore = psutil.cpu_count(logical=False)
cpuFreq = psutil.cpu_freq().max / 1000
ramTotal = round(psutil.virtual_memory().total / (1024 ** 3), 1)
swapTotal = round(psutil.swap_memory().total / (1024 ** 3), 1)
diskTotal = round(psutil.disk_usage('/').total / (1024 ** 3), 1)
system = platform.platform()
try:
    cpu = cpuinfo.get_cpu_info()['brand_raw']
except:
    cpu = "未知 CPU"

cnt, cpuUsage, ramUsage, swapUsed, proces, startHour, start, diskUsed = (0, 0, 0, 0, 0, 0, 0, 0)

def checkService(name):
    try:
        result = subprocess.run(['/usr/bin/systemctl', 'status', name], capture_output=True, text=True)
    except Exception as e:
        print(e)
        return False
    print(result.stdout)
    if 'Active: active (running)' in result.stdout:
        print("Running")
        return True
    else:
        return False


@scheduler.task('interval', id='refreshState', seconds=5, max_instances=100)
def init():
    global cnt, cpuUsage, ramUsage, swapUsed, proces, startHour, start, diskUsed
    cpuUsage = int(psutil.cpu_percent(interval=1, percpu=False))
    ramUsage = round(psutil.virtual_memory().percent)
    swapUsed = round(psutil.swap_memory().used / (1024 ** 3), 1)
    cnt = 0
    for i in psutil.process_iter():
        cnt += 1
    proces = cnt
    startHour = round((time.time() - psutil.boot_time()) % (24 * 3600) / 3600)
    start = math.floor((time.time() - psutil.boot_time()) / (24 * 3600))
    diskUsed = round(psutil.disk_usage('/').used / (1024 ** 3), 1)
    socketio.emit('dataRefresh',
                  {'data': {"cpuUsage": str(cpuUsage), "ramUsage": str(ramUsage), "swapUsed": str(swapUsed),
                            "proces": str(proces),
                            "startHour": str(startHour), "start": str(start), "diskUsed": str(diskUsed)}})


@scheduler.task('interval', id='procsApi', seconds=60, max_instances=100)
def init():
    for i in serviceList:
        if i['service']:
            i['status'] = checkService(i['service'])
        elif i['ping']:
            try:
                t = requests.get(i['ping'], timeout=1)
                if t.status_code == 200:
                    i['status'] = True
                else:
                    i['status'] = False
            except Exception as e:
                print(e)
                i['status'] = False
    for i in APIList:
        try:
            t = ping3.ping(i['url'], timeout=2)
            print(t)
            if t:
                i['status'] = True
                i['ping'] = round(t * 1000)
            else:
                i['status'] = False
                i['ping'] = -1
        except Exception as e:
            print("APIError:", e)
            i['status'] = False
            i['ping'] = -1
    print(serviceList, APIList)
    socketio.emit('apiRefresh',
                  {'data': {"service": serviceList, "api": APIList}})


init()

f = glob.glob(BASIC_PATH + "/app_*_*.log.jsonl")
s = {}
for i in f:
    s[i] = int(''.join(re.findall(r'\d+', i)))
s = dict(sorted(s.items(), key=lambda item: item[1]))
print(s)
logName = "找不到 Logs 文件夹"
log = []
try:
    logName = list(s.keys())[-1]
    log = open(list(s.keys())[-1], 'r', encoding="utf-8").readlines()
    for i in range(len(log)):
        log[i] = eval(log[i])
except:
    pass


class LogHandler(FileSystemEventHandler):
    def on_modified(self, event):
        global log
        if not event.is_directory:
            print("Change detected")
            nl = open(logName, "r", encoding="utf-8").readlines()
            for i in range(len(nl)):
                nl[i] = eval(nl[i])
            diff = nl[len(log):]
            print(diff)
            if not diff:
                return
            socketio.emit('newLog', {'data': diff})
            log = copy.deepcopy(nl)

    def on_created(self, event):
        global log, logName
        if not event.is_directory:
            if "~" in event.src_path:
                return
            print("New log detected")
            time.sleep(1)
            logName = event.src_path
            nl = open(logName, "r", encoding="utf-8").readlines()
            for i in range(len(nl)):
                nl[i] = eval(nl[i])
            socketio.emit('newLogFile', {'data': nl, 'file': logName})
            log = copy.deepcopy(nl)


observer = Observer()
event_handler = LogHandler()
observer.schedule(event_handler, path=BASIC_PATH, recursive=False)
if log:
    observer.start()


@app.route('/')
def index():
    return render_template('index.html', log=log[-1000:], logName=logName, cpu=cpu, cpuCore=cpuCore,
                           cpuFreq=cpuFreq,
                           ramTotal=ramTotal, ramUsage=ramUsage, swapTotal=swapTotal, swapUsed=swapUsed,
                           diskTotal=diskTotal, diskUsed=diskUsed, system=system, proces=proces,
                           startHour=startHour, start=start, cpuUsage=cpuUsage, serviceList=serviceList,
                           APIList=APIList)


@app.errorhandler(404)
def handler404(error):
    if request.method == "POST":
        return jsonify({'result': 'error', 'code': 1404})
    return render_template("alert.html", title="出错啦 (っ °Д °;)っ", alertTitle="找不到网页",
                           alertText="你是怎么过来的？| " + str(error), alertIcon="error"), 404


# Maybe this is useless
@app.errorhandler(500)
def handler500(error):
    if request.method == "POST":
        return jsonify({'result': 'error', 'code': 1500})
    return render_template("alert.html", title="出错啦 （；´д｀）ゞ", alertTitle="发生错误",
                           alertText="服务器发生内部错误。请将此问题上报网站管理员。| " + str(error),
                           alertIcon="error", reload=True), 500


@app.errorhandler(Exception)
def handlerException(error):
    if request.method == "POST":
        return jsonify({'result': 'error', 'code': 1500})
    return render_template("alert.html", title="出错啦 （；´д｀）ゞ", alertTitle="发生错误",
                           alertText="服务器发生内部错误。请将此问题上报网站管理员。| " + str(error),
                           alertIcon="error", reload=True), 500


@app.errorhandler(429)
def handler429(error):
    if request.method == "POST":
        return jsonify({'result': 'error', 'code': 1429})
    return render_template("alert.html", title="出错啦 o((>ω< ))o", alertTitle="流量限制",
                           alertText="访问页面过于频繁。你在干什么？！| " + str(error), alertIcon="error",
                           reload=True), 429


@app.errorhandler(405)
def handler405(error):
    if request.method == "POST":
        return jsonify({'result': 'error', 'code': 1405})
    return render_template("alert.html", title="出错啦 (；′⌒`)", alertTitle="发生错误",
                           alertText="请求方式不正确。不要再瞎输啦……| " + str(error), alertIcon="error"), 405


@app.errorhandler(403)
def handler405(error):
    if request.method == "POST":
        return jsonify({'result': 'error', 'code': 1403})
    return render_template("alert.html", title="出错啦 (○´･д･)ﾉ", alertTitle="权限不足",
                           alertText="请求被拒绝。您可能没有适当的权限访问此页面。| " + str(error),
                           alertIcon="error"), 403


if __name__ == '__main__':
    socketio.run(app, host="0.0.0.0", port=5000, allow_unsafe_werkzeug=True)
