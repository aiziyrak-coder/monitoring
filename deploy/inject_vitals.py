"""
REST API orqali vitals yuborish va HL7 test.
/api/device/<ip>/vitals POST endpoint.
"""
import sys, time, os, tempfile, json
try:
    import paramiko
except ImportError:
    print("pip install paramiko"); sys.exit(1)

DEVICE_IP  = "192.168.88.104"
DEVICE_ID  = "dev1775709079856"

client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
print("Ulanish: root@167.71.53.238")
client.connect('167.71.53.238', username='root', password='Ziyrak2025Ai', timeout=30)

def run(cmd, label='', timeout=30):
    if label: print(f'\n=== {label} ===')
    stdin, stdout, stderr = client.exec_command(cmd, timeout=timeout)
    out = stdout.read().decode(errors='replace').strip()
    err = stderr.read().decode(errors='replace').strip()
    if out: print(out[:2000].encode('ascii', errors='replace').decode())
    if err and 'warn' not in err.lower() and 'deprecat' not in err.lower():
        print('[ERR]', err[:300].encode('ascii', errors='replace').decode())
    return out

# 1. Barcha REST endpointlarni ko'rish
run("curl -s http://127.0.0.1:8010/api/ 2>&1 | head -30", "API root endpointlar")

# 2. Device ID bo'yicha vitals yuborish
payload_id = json.dumps({"hr": 88, "spo2": 96, "nibpSys": 138, "nibpDia": 86, "rr": 18, "temp": 36.8})
run(
    f"curl -s -X POST http://127.0.0.1:8010/api/devices/{DEVICE_ID}/vitals "
    f"-H 'Content-Type: application/json' -d '{payload_id}'",
    "POST /api/devices/<id>/vitals"
)

# 3. Device IP bo'yicha vitals
payload_ip = json.dumps({"hr": 88, "spo2": 96, "nibpSys": 138, "nibpDia": 86, "rr": 18, "temp": 36.8})
run(
    f"curl -s -X POST http://127.0.0.1:8010/api/device/{DEVICE_IP}/vitals "
    f"-H 'Content-Type: application/json' -d '{payload_ip}'",
    "POST /api/device/<ip>/vitals"
)

time.sleep(2)
run(
    "journalctl -u clinicmonitoring-backend -n 20 --no-pager 2>&1 | grep -E 'vital|POST|device|bemorga|yazildi' | tail -15",
    "Backend loglar"
)

# 4. Bemor holati
CHECK = """
from monitoring.models import Patient
p = Patient.objects.filter(id='p2319a6af5b').first()
if p:
    print(f"HR={p.hr} SpO2={p.spo2} NIBP={p.nibp_sys}/{p.nibp_dia} RR={p.rr} Temp={p.temp}")
    print(f"last_real_vitals_ms={p.last_real_vitals_ms}")
"""
with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False, encoding='utf-8') as f:
    f.write(CHECK)
    tmp = f.name
sftp = client.open_sftp()
sftp.put(tmp, '/tmp/chk.py')
sftp.close()
os.unlink(tmp)
run("cd /opt/clinicmonitoring/backend && .venv/bin/python manage.py shell < /tmp/chk.py 2>&1 | grep -v 'HL7 server\\|Address already\\|imported'", "Patient DB vitals")
run("rm -f /tmp/chk.py")

client.close()
