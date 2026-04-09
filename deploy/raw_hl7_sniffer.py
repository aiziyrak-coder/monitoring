"""
Port 6006 ga kelayotgan barcha raw TCP baytlarni oldindan ko'rish.
60 soniya tinglaydi va birinchi xabarni hex + text formatida chiqaradi.
"""
import sys, time, os, tempfile
try:
    import paramiko
except ImportError:
    print("pip install paramiko"); sys.exit(1)

# Serverda parallel TCP sniffer ishga tushiramiz
SNIFFER = r'''
import socket, threading, sys, time

results = []
lock = threading.Lock()

def handle(conn, addr):
    chunks = []
    conn.settimeout(15)
    try:
        while True:
            d = conn.recv(4096)
            if not d:
                break
            chunks.append(d)
    except:
        pass
    finally:
        conn.close()
    raw = b"".join(chunks)
    with lock:
        results.append((addr[0], raw))

srv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)
srv.settimeout(30)
print("SNIFFER: listening on 6007 (mirror)", flush=True)
try:
    srv.bind(("0.0.0.0", 6007))
    srv.listen(10)
    deadline = time.time() + 60
    while time.time() < deadline:
        try:
            srv.settimeout(max(0.5, deadline - time.time()))
            c, a = srv.accept()
            t = threading.Thread(target=handle, args=(c,a), daemon=True)
            t.start()
        except socket.timeout:
            break
        except:
            break
except Exception as e:
    print("SNIFFER ERR:", e, flush=True)

print(f"SNIFFER: captured {len(results)} connections", flush=True)
for ip, raw in results:
    print(f"=== FROM {ip} ({len(raw)} bytes) ===", flush=True)
    if raw:
        # hex
        print("HEX:", raw[:512].hex(), flush=True)
        # text
        try:
            text = raw.decode("utf-8", errors="replace")
        except:
            text = raw.decode("latin-1", errors="replace")
        print("TEXT:", repr(text[:600]), flush=True)
    else:
        print("EMPTY (TCP connect/disconnect only)", flush=True)
'''

client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
print("Ulanish: root@167.71.53.238")
client.connect('167.71.53.238', username='root', password='Ziyrak2025Ai', timeout=30)

def run(cmd, label='', timeout=90):
    if label: print(f'\n=== {label} ===')
    stdin, stdout, stderr = client.exec_command(cmd, timeout=timeout)
    out = stdout.read().decode(errors='replace').strip()
    if out: print(out[:3000].encode('ascii', errors='replace').decode())
    return out

# 1. tcpdump bilan port 6006 ni tinglash (45 soniya)
print("\n45 soniya tcpdump bilan port 6006 ni to'liq ko'rish...")
run(
    "timeout 45 tcpdump -i any -X -s 2048 'tcp port 6006 and not src host 127.0.0.1 and (tcp[tcpflags] & tcp-push != 0)' 2>&1 | head -120",
    "TCPdump port 6006 PUSH paketlar (ma'lumot yuborilganda)",
    timeout=50
)

client.close()
