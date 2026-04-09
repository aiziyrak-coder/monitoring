"""
Serverda to'g'ridan to'g'ri Django ORM orqali vitals yozish
va socket emit qilish. Bu curl muammosini bypass qiladi.
"""
import sys, time, os, tempfile
try:
    import paramiko
except ImportError:
    print("pip install paramiko"); sys.exit(1)

SCRIPT = """
import time
from monitoring.models import Patient, Device, VitalHistory
from monitoring.services.device_ingest import apply_device_vitals_dict
from monitoring.asgi_support import schedule_vitals_emit

dev = Device.objects.filter(id='dev1775709079856').first()
pat = Patient.objects.filter(id='p2319a6af5b').first()

if not dev:
    print("Device topilmadi!")
    import sys; sys.exit(1)
if not pat:
    print("Patient topilmadi!")
    import sys; sys.exit(1)

print(f"Device: {dev.id} status={dev.status}")
print(f"Patient before: HR={pat.hr} SpO2={pat.spo2} last_real={pat.last_real_vitals_ms}")

vitals = {
    "hr": 88,
    "spo2": 96,
    "nibpSys": 138,
    "nibpDia": 86,
    "rr": 18,
    "temp": 36.8,
}

payload = apply_device_vitals_dict(dev, vitals)
print(f"apply_device_vitals_dict result: {payload is not None}")

if payload:
    schedule_vitals_emit([payload])
    print("socket.io emit scheduled!")

pat.refresh_from_db()
print(f"Patient after: HR={pat.hr} SpO2={pat.spo2} last_real={pat.last_real_vitals_ms}")
print(f"VitalHistory count: {VitalHistory.objects.filter(patient=pat).count()}")
"""

client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
print("Ulanish: root@167.71.53.238")
client.connect('167.71.53.238', username='root', password='Ziyrak2025Ai', timeout=30)

def run(cmd, label='', timeout=60):
    if label: print(f'\n=== {label} ===')
    stdin, stdout, stderr = client.exec_command(cmd, timeout=timeout)
    out = stdout.read().decode(errors='replace').strip()
    if out: print(out[:2000].encode('ascii', errors='replace').decode())
    return out

with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False, encoding='utf-8') as f:
    f.write(SCRIPT)
    tmp = f.name

sftp = client.open_sftp()
sftp.put(tmp, '/tmp/inject.py')
sftp.close()
os.unlink(tmp)

run("cd /opt/clinicmonitoring/backend && .venv/bin/python manage.py shell < /tmp/inject.py 2>&1 | grep -v 'HL7 server\\|Address already\\|imported'", "Vitals inject (Django ORM)")

# Health check
run("curl -s http://127.0.0.1:8010/api/health 2>&1 | python3 -c \"import sys,json;d=json.load(sys.stdin);i=d['ingest'];print('vitalsWritten:',i['vitalUpdatesWrittenToPatientDb'])\"", "Health vitalsWritten")
run("rm -f /tmp/inject.py")

client.close()
print("\nTayyor!")
