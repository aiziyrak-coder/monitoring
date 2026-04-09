"""
2 ta usul bilan real vital yuborish:
1) REST API orqali vitals POST (server o'ziga)
2) HL7 test xabari yuborish (ncat orqali)
"""
import sys, time, os, tempfile, json
try:
    import paramiko
except ImportError:
    print("pip install paramiko"); sys.exit(1)

PATIENT_ID = "p2319a6af5b"
DEVICE_ID  = "dev1775709079856"

# HL7 ORU^R01 test xabari — Creative K12 uslubi
HL7_MSG = (
    "\x0b"  # MLLP start
    "MSH|^~\\&|K12Monitor|CLinic|ClinicServer|CLinic|20260409120000||ORU^R01|MSG001|P|2.3\r"
    "PID|1||ISLOMBEK|||Raxmonberdiyev^Islombek||19800101|M\r"
    "OBR|1||||||20260409120000\r"
    "OBX|1|NM|8867-4^Heart rate^LN||88|/min|60-100||||F|||20260409120000\r"
    "OBX|2|NM|59408-5^SpO2^LN||96|%|95-100||||F|||20260409120000\r"
    "OBX|3|NM|9279-1^Respiratory rate^LN||18|/min|12-20||||F|||20260409120000\r"
    "OBX|4|NM|8310-5^Body temperature^LN||36.8|Cel|36.0-37.5||||F|||20260409120000\r"
    "OBX|5|NM|8480-6^Systolic BP^LN||138|mmHg|90-140||||F|||20260409120000\r"
    "OBX|6|NM|8462-4^Diastolic BP^LN||86|mmHg|60-90||||F|||20260409120000\r"
    "\x1c\r"  # MLLP end
)

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
    if err and 'deprecat' not in err.lower(): print('[ERR]', err[:400].encode('ascii', errors='replace').decode())
    return out

# 1. REST API orqali vitals yuborish
print("\n1. REST API orqali vitals yuborish...")
rest_payload = json.dumps({
    "deviceId": DEVICE_ID,
    "hr": 88,
    "spo2": 96,
    "nibpSys": 138,
    "nibpDia": 86,
    "rr": 18,
    "temp": 36.8
})

run(
    f"curl -s -X POST http://127.0.0.1:8010/api/ingest/vitals "
    f"-H 'Content-Type: application/json' "
    f"-d '{rest_payload}'",
    "REST /api/ingest/vitals"
)

# Agar /api/ingest/vitals ishlamasa — boshqa endpoint
run(
    f"curl -s http://127.0.0.1:8010/api/devices/{DEVICE_ID} 2>&1 | head -5",
    "Device info"
)

# 2. HL7 test xabari localhost ga yuborish
print("\n2. HL7 test xabari localhost 6006 ga yuborish...")
with tempfile.NamedTemporaryFile(mode='wb', suffix='.hl7', delete=False) as f:
    f.write(HL7_MSG.encode('utf-8'))
    tmp_hl7 = f.name

sftp = client.open_sftp()
sftp.put(tmp_hl7, '/tmp/test_hl7.bin')
sftp.close()
os.unlink(tmp_hl7)

run(
    "cat /tmp/test_hl7.bin | nc -q 2 127.0.0.1 6006 2>&1; echo 'HL7 sent'",
    "HL7 localhost ga yuborish (nc)"
)

time.sleep(3)
run(
    "journalctl -u clinicmonitoring-backend -n 30 --no-pager 2>&1 | grep -E 'HL7|OBX|vital|HR|SpO2|parsed|yozildi|bemorga' | tail -20",
    "Backend loglar (HL7 keyin)"
)
run(
    "curl -s http://127.0.0.1:8010/api/health 2>&1",
    "Health ingest stats"
)

# Bemorning vitallari tekshirish
CHECK = """
from monitoring.models import Patient
p = Patient.objects.filter(id='p2319a6af5b').first()
if p:
    print(f"HR={p.hr} SpO2={p.spo2} NIBP={p.nibp_sys}/{p.nibp_dia} RR={p.rr} Temp={p.temp}")
    print(f"last_real_vitals_ms={p.last_real_vitals_ms}")
"""
with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False, encoding='utf-8') as f:
    f.write(CHECK)
    tmp_py = f.name

sftp = client.open_sftp()
sftp.put(tmp_py, '/tmp/chk.py')
sftp.close()
os.unlink(tmp_py)

run("cd /opt/clinicmonitoring/backend && .venv/bin/python manage.py shell < /tmp/chk.py 2>&1 | grep -v 'HL7 server\\|Address already\\|imported'", "Patient vitals DB")
run("rm -f /tmp/test_hl7.bin /tmp/chk.py")
client.close()
