"""Git pull + build frontend + restart backend."""
import sys, time
try:
    import paramiko
except ImportError:
    print("pip install paramiko"); sys.exit(1)

APP = "/opt/clinicmonitoring"

client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
print("Ulanish: root@167.71.53.238")
client.connect('167.71.53.238', username='root', password='Ziyrak2025Ai', timeout=30)

def run(cmd, label='', timeout=300):
    if label: print(f'\n=== {label} ===')
    stdin, stdout, stderr = client.exec_command(cmd, timeout=timeout)
    out = stdout.read().decode(errors='replace').strip()
    err = stderr.read().decode(errors='replace').strip()
    if out: print(out[:2000].encode('ascii', errors='replace').decode())
    if err and 'deprecat' not in err.lower() and 'warn' not in err.lower() and 'warning' not in err.lower():
        print('[ERR]', err[:400].encode('ascii', errors='replace').decode())
    return out

run(f"cd {APP}/backend && git pull origin main 2>&1 | tail -5", "Git pull")
run("systemctl restart clinicmonitoring-backend", "Backend restart")
time.sleep(4)
run("systemctl is-active clinicmonitoring-backend", "Status")
run(f"cd {APP}/frontend && npm run build 2>&1 | tail -5", "Frontend build", timeout=240)
run("nginx -s reload", "Nginx reload")
time.sleep(3)

# Final check
run("curl -s http://127.0.0.1:8010/api/patients 2>&1 | python3 -c \"import sys,json; d=json.load(sys.stdin); [print(p['id'], p['name'], 'HR='+str(p['vitals']['hr']), 'SpO2='+str(p['vitals']['spo2']), 'device='+str(p.get('linkedDeviceId','none')), 'lastSeen='+str(p.get('linkedDeviceLastSeenMs',0))) for p in d if 'Islombek' in p.get('name','')]\"", "Islombek patient vitals")

client.close()
print("\nDeploy tayyor!")
