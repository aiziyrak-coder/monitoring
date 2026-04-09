"""Port 6006 barcha paketlar — ma'lumot yuborilishini kutamiz."""
import sys, time
try:
    import paramiko
except ImportError:
    print("pip install paramiko"); sys.exit(1)

client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
print("Ulanish: root@167.71.53.238")
client.connect('167.71.53.238', username='root', password='Ziyrak2025Ai', timeout=30)

def run(cmd, label='', timeout=90):
    if label: print(f'\n=== {label} ===')
    stdin, stdout, stderr = client.exec_command(cmd, timeout=timeout)
    out = stdout.read().decode(errors='replace').strip()
    if out: print(out[:4000].encode('ascii', errors='replace').decode())
    return out

# eth0 da barcha port 6006 paketlarni ko'rish (45s)
print("\n45 soniya eth0 port 6006 barcha paketlar...")
run(
    "timeout 45 tcpdump -i eth0 -X -s 4096 'tcp port 6006' 2>&1 | head -200",
    "TCPdump eth0 port 6006 (barcha paketlar)",
    timeout=50
)

client.close()
