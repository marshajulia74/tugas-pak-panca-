from machine import ADC, Pin, PWM
import time
import network
from microdot import Microdot, send_file, Response
import ujson
import _thread

# ===== KONFIGURASI WiFi =====
SSID = "Hotspot-SMK"
PASSWORD = ""

def connect_wifi():
    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)
    if not wlan.isconnected():
        print("Menghubungkan ke WiFi...")
        wlan.connect(SSID, PASSWORD)
        while not wlan.isconnected():
            time.sleep(1)
    print("WiFi Connected:", wlan.ifconfig())

connect_wifi()

# ===== KONFIG SENSOR & BUZZER =====
mq_sensor = ADC(Pin(34))
mq_sensor.atten(ADC.ATTN_11DB)

buzzer = PWM(Pin(12))
buzzer.duty(0)

THRESHOLD = 2500

# ===== DATA GLOBAL =====
sensor_data = {
    "value": 0,
    "status": "AMAN",
    "threshold": THRESHOLD,
    "buzzer_active": False
}

# ===== BUZZER NON-BLOCKING =====
def buzzer_thread():
    while sensor_data["buzzer_active"]:
        for freq in range(800, 2000, 100):
            if not sensor_data["buzzer_active"]:
                break
            buzzer.freq(freq)
            buzzer.duty(512)
            time.sleep(0.005)
        for freq in range(2000, 800, -100):
            if not sensor_data["buzzer_active"]:
                break
            buzzer.freq(freq)
            buzzer.duty(512)
            time.sleep(0.005)
    buzzer.duty(0)

def activate_buzzer():
    if not sensor_data["buzzer_active"]:
        sensor_data["buzzer_active"] = True
        _thread.start_new_thread(buzzer_thread, ())

def stop_buzzer():
    sensor_data["buzzer_active"] = False

# ===== SENSOR LOOP =====
def read_sensor():
    while True:
        val = mq_sensor.read()
        sensor_data["value"] = val
        if val > sensor_data["threshold"]:
            sensor_data["status"] = "BAHAYA"
            activate_buzzer()
        else:
            sensor_data["status"] = "AMAN"
            stop_buzzer()
        time.sleep(1)

_thread.start_new_thread(read_sensor, ())

# ===== WEB SERVER =====
app = Microdot()

@app.route('/')
def index(request):
    return send_file("templates/index.html")  # pastikan ada

@app.route('/api/sensor')
def get_sensor(request):
    return Response(ujson.dumps(sensor_data), headers={"Content-Type":"application/json"})

@app.route('/api/threshold', methods=['POST'])
def set_threshold(request):
    try:
        data = ujson.loads(request.body)
        thr = int(data.get("threshold", sensor_data["threshold"]))
        sensor_data["threshold"] = thr
        return Response(ujson.dumps({"message":"Threshold updated","threshold":thr}),
                        headers={"Content-Type":"application/json"})
    except:
        return Response(ujson.dumps({"error":"Invalid data"}), status=400,
                        headers={"Content-Type":"application/json"})

@app.route('/api/buzzer', methods=['POST'])
def buzzer_api(request):
    try:
        data = ujson.loads(request.body)
        action = data.get("action","")
        if action == "on":
            activate_buzzer()
        elif action == "off":
            stop_buzzer()
        else:
            return Response(ujson.dumps({"error":"Invalid action"}), status=400,
                            headers={"Content-Type":"application/json"})
        return Response(ujson.dumps({"message":"OK"}), headers={"Content-Type":"application/json"})
    except:
        return Response(ujson.dumps({"error":"Invalid JSON"}), status=400,
                        headers={"Content-Type":"application/json"})

@app.route('/static/<path:path>')
def static_files(request, path):
    return send_file("static/"+path)

# ===== START SERVER =====
ip = network.WLAN(network.STA_IF).ifconfig()[0]
print("Server berjalan di http://{}:5000".format(ip))
app.run(host="0.0.0.0", port=5000)

