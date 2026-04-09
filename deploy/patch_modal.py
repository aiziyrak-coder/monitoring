"""PatientDetailsModal dan katta diagnostika panelini olib tashlash."""

TARGET = "frontend/src/components/PatientDetailsModal.tsx"

with open(TARGET, 'r', encoding='utf-8', errors='replace') as f:
    content = f.read()

start_marker = '{!hasLiveVitals && ('
end_marker = '              )}\n\n              {/* Charts */'

start_idx = content.find(start_marker)
end_idx = content.find(end_marker)
end_idx_full = end_idx + len(end_marker)

if start_idx < 0 or end_idx < 0:
    print(f"ERROR: markers not found (start={start_idx}, end={end_idx})")
    exit(1)

new_block = (
    '{/* Device connection status */}\n'
    '              {patient.linkedDeviceId && (\n'
    '                <DeviceStatusBadge\n'
    '                  hasLiveVitals={hasLiveVitals}\n'
    '                  lastRealVitalsMs={patient.lastRealVitalsMs}\n'
    '                  linkedDeviceLastSeenMs={patient.linkedDeviceLastSeenMs}\n'
    '                />\n'
    '              )}\n'
    '\n'
    '              {/* Charts */'
)

new_content = content[:start_idx] + new_block + content[end_idx_full:]

with open(TARGET, 'w', encoding='utf-8') as f:
    f.write(new_content)

print(f"OK: removed {end_idx_full - start_idx} chars, file now {len(new_content)} chars")
