from machine import ADC, Pin, PWM
import time
import network
from microdot import Microdot, send_file

# ===== KONFIGURASI WiFi =====
SSID = "Hotspot-SMK"
PASSWORD = ""

def connect_wifi():
    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)
    if not wlan.isconnected():
        print('Menghubungkan ke WiFi...')
        wlan.connect(SSID, PASSWORD)
        while not wlan.isconnected():
            time.sleep(1)
    print('WiFi Connected:', wlan.ifconfig())

connect_wifi()

# ===== KONFIGURASI SENSOR & BUZZER =====
mq_sensor = ADC(Pin(34))
mq_sensor.atten(ADC.ATTN_11DB)

buzzer = PWM(Pin(12))
buzzer.duty(0)

THRESHOLD = 2500

# ===== MICRODOT WEB SERVER =====
app = Microdot()

# Data global untuk web interface
sensor_data = {
    'value': 0,
    'status': 'Aman',
    'threshold': THRESHOLD,
    'buzzer_active': False
}

def activate_buzzer():
    """Fungsi untuk mengaktifkan buzzer dengan sirine"""
    for freq in range(800, 2000, 100):
        buzzer.freq(freq)
        buzzer.duty(512)
        time.sleep(0.005)
    for freq in range(2000, 800, -100):
        buzzer.freq(freq)
        buzzer.duty(512)
        time.sleep(0.005)

def stop_buzzer():
    """Fungsi untuk mematikan buzzer"""
    buzzer.duty(0)

# ===== ROUTES WEB =====
@app.route('/')
def index(request):
    return send_file('static/index.html')

@app.route('/api/sensor')
def get_sensor_data(request):
    """API untuk mendapatkan data sensor terbaru"""
    return sensor_data

@app.route('/api/threshold', methods=['POST'])
def update_threshold(request):
    """API untuk mengubah threshold"""
    data = request.json
    if 'threshold' in data:
        sensor_data['threshold'] = int(data['threshold'])
        return {'message': 'Threshold updated', 'threshold': sensor_data['threshold']}
    return {'error': 'Invalid data'}, 400

@app.route('/api/buzzer', methods=['POST'])
def control_buzzer(request):
    """API untuk mengontrol buzzer manual"""
    data = request.json
    if 'action' in data:
        if data['action'] == 'on':
            activate_buzzer()
            return {'message': 'Buzzer diaktifkan'}
        elif data['action'] == 'off':
            stop_buzzer()
            return {'message': 'Buzzer dimatikan'}
    return {'error': 'Invalid action'}, 400

@app.route('/static/<path:path>')
def static(request, path):
    return send_file('static/' + path)

# ===== FUNGSI BACA SENSOR =====
def read_sensor():
    """Fungsi untuk membaca sensor secara kontinu"""
    while True:
        sensor_value = mq_sensor.read()
        sensor_data['value'] = sensor_value
        
        if sensor_value > sensor_data['threshold']:
            sensor_data['status'] = 'BAHAYA!'
            sensor_data['buzzer_active'] = True
            print("🚨 Asap terdeteksi!")
            activate_buzzer()
        else:
            sensor_data['status'] = 'Aman'
            sensor_data['buzzer_active'] = False
            print("✅ Aman.")
            stop_buzzer()
        
        time.sleep(2)

# ===== JALANKAN SISTEM =====
print("Sistem deteksi asap aktif...")

# Jalankan pembacaan sensor di background
import _thread
_thread.start_new_thread(read_sensor, ())

if __name__ == '__main__':
    print('Web server starting...')
    print('Akses http://' + str(network.WLAN(network.STA_IF).ifconfig()[0]) + ':5000')
    app.run(port=5000, debug=True)
