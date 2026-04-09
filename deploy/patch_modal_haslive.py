"""PatientDetailsModal hasLiveVitals logikasini kengaytirish."""

TARGET = "frontend/src/components/PatientDetailsModal.tsx"

with open(TARGET, 'r', encoding='utf-8', errors='replace') as f:
    content = f.read()

old = "  const hasLiveVitals =\n    patient != null &&\n    patient.lastRealVitalsMs != null &&\n    patient.lastRealVitalsMs > 0;"

new = """  const deviceOnlineModal =
    patient != null &&
    Boolean(patient.linkedDeviceId) &&
    (patient.linkedDeviceLastSeenMs ?? 0) > 0 &&
    Date.now() - (patient.linkedDeviceLastSeenMs ?? 0) < 120_000;
  const hasDbVitalsModal =
    patient != null &&
    ((patient.vitals?.hr ?? 0) > 0 ||
      (patient.vitals?.spo2 ?? 0) > 0 ||
      (patient.vitals?.nibpSys ?? 0) > 0);
  const hasLiveVitals =
    patient != null &&
    ((patient.lastRealVitalsMs != null && patient.lastRealVitalsMs > 0) ||
      (deviceOnlineModal && hasDbVitalsModal));"""

if old in content:
    content = content.replace(old, new, 1)
    print("OK: hasLiveVitals logic updated in PatientDetailsModal")
else:
    print("NOT FOUND - trying without whitespace")
    idx = content.find("const hasLiveVitals =")
    print(repr(content[idx:idx+200]))

with open(TARGET, 'w', encoding='utf-8') as f:
    f.write(content)
