"""Patch hl7_mllp_listener.py - loopback guards va log first chunk."""

TARGET = "backend/monitoring/hl7_mllp_listener.py"

with open(TARGET, 'r', encoding='utf-8', errors='replace') as f:
    content = f.read()

changes = 0

# 1. record_hl7_tcp_external_accept ni loopback uchun o'chirish
old1 = '    max_buf = int(getattr(settings, "HL7_MAX_BUFFER_BYTES", 2 * 1024 * 1024))\n    record_hl7_tcp_external_accept(peer)'
new1 = '    max_buf = int(getattr(settings, "HL7_MAX_BUFFER_BYTES", 2 * 1024 * 1024))\n    if not _is_loopback:\n        record_hl7_tcp_external_accept(peer)'
if old1 in content:
    content = content.replace(old1, new1, 1)
    changes += 1
    print("OK: record_hl7_tcp_external_accept guarded")
else:
    print("SKIP: record_hl7_tcp_external_accept not found")

# 2. record_hl7_tcp_session_with_device ni guarded
old2 = "        if dev0:\n            record_hl7_tcp_session_with_device()"
new2 = "        if dev0 and not _is_loopback:\n            record_hl7_tcp_session_with_device()"
if old2 in content:
    content = content.replace(old2, new2, 1)
    changes += 1
    print("OK: session_with_device guarded")
else:
    print("SKIP: session_with_device not found")

# 3. record_hl7_tcp_external_no_device guarded
old3 = "            record_hl7_tcp_external_no_device()\n            log.warning(\n"
new3 = "            if not _is_loopback:\n                record_hl7_tcp_external_no_device()\n            log.warning(\n"
if old3 in content:
    content = content.replace(old3, new3, 1)
    changes += 1
    print("OK: no_device guarded")
else:
    print("SKIP: no_device not found")

with open(TARGET, 'w', encoding='utf-8') as f:
    f.write(content)

print(f"\n{changes} o'zgarish. Fayl saqlandi.")
