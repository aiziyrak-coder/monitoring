"""PatientMonitor.tsx - hasLiveVitals logikasini kengaytirish."""

TARGET = "frontend/src/components/PatientMonitor.tsx"

with open(TARGET, 'r', encoding='utf-8', errors='replace') as f:
    content = f.read()

old = "  const hasLiveVitals = patient.lastRealVitalsMs != null && patient.lastRealVitalsMs > 0;\n\n  const linked = Boolean(patient.linkedDeviceId);\n  const lastSeen = patient.linkedDeviceLastSeenMs;\n  const deviceOnline =\n    linked &&\n    lastSeen != null &&\n    lastSeen > 0 &&\n    Date.now() - lastSeen <= DEVICE_STALE_MS;\n  const deviceProbablyOffline = linked && !deviceOnline;\n\n  /**\n   * Jonli vital yo'q, lekin DB da qiymat bor — ko'rsatamiz (bazaviy/placeholder).\n   * Sensorlar ulanmagan bo'lsa ham, DB vitals ko'rsatilsin.\n   */\n  const hasDbVitals = vitals.hr > 0 || vitals.spo2 > 0 || vitals.nibpSys > 0 || vitals.rr > 0;\n  const showDbPlaceholder = !hasLiveVitals && hasDbVitals;"

if old not in content:
    # Try with replacement characters
    idx = content.find("const hasLiveVitals = patient.lastRealVitalsMs")
    if idx >= 0:
        end_idx = content.find("const showDbPlaceholder", idx) + len("const showDbPlaceholder = !hasLiveVitals && hasDbVitals;")
        print("Found block:")
        print(repr(content[idx:end_idx]))
    else:
        print("NOT FOUND - checking file content")
        print(repr(content[1000:1400]))
    exit(0)

new = """  const linked = Boolean(patient.linkedDeviceId);
  const lastSeen = patient.linkedDeviceLastSeenMs;
  const deviceOnline =
    linked &&
    lastSeen != null &&
    lastSeen > 0 &&
    Date.now() - lastSeen <= DEVICE_STALE_MS;
  const deviceProbablyOffline = linked && !deviceOnline;

  /**
   * hasLiveVitals: real HL7/REST vital kelgan YOKI qurilma online + DB da vital bor.
   * Sensorlarsiz TCP ulanib turgan qurilma ham "live" ko'rsatilsin.
   */
  const hasRealVitalsMs = patient.lastRealVitalsMs != null && patient.lastRealVitalsMs > 0;
  const hasDbVitals = vitals.hr > 0 || vitals.spo2 > 0 || vitals.nibpSys > 0 || vitals.rr > 0;
  const hasLiveVitals = hasRealVitalsMs || (deviceOnline && hasDbVitals);
  const showDbPlaceholder = !hasRealVitalsMs && hasDbVitals;"""

content = content.replace(old, new, 1)

with open(TARGET, 'w', encoding='utf-8') as f:
    f.write(content)
print("OK: hasLiveVitals logic updated")
