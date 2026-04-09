"""
PatientDetailsModal dan:
1. healthIngest state va useEffect ni olib tashlash
2. DeviceStatusBadge komponentini qoshish
3. HealthIngest interfeysi - olib tashlash
"""

TARGET = "frontend/src/components/PatientDetailsModal.tsx"

with open(TARGET, 'r', encoding='utf-8', errors='replace') as f:
    content = f.read()

# 1. HealthIngest interface va healthIngest state ni olib tashlash
# Remove HealthIngest interface
content = content.replace(
    '/** /api/health \u2192 ingest */\ninterface HealthIngest {\n  hl7MessagesWithResolvedDevice?: number;\n  /** TCP 6006 da qurilma topilgan ulanishlar (matn kelmasa ham) */\n  hl7TcpSessionsDeviceResolved?: number;\n  hl7ObxPresentButVitalsEmpty?: number;\n  hl7ParsedToVitalsNonEmpty?: number;\n  vitalUpdatesWrittenToPatientDb?: number;\n}\n\n',
    ''
)

# Also try without the unicode arrow
for old in [
    '/** /api/health -> ingest */\ninterface HealthIngest {\n  hl7MessagesWithResolvedDevice?: number;\n  /** TCP 6006 da qurilma topilgan ulanishlar (matn kelmasa ham) */\n  hl7TcpSessionsDeviceResolved?: number;\n  hl7ObxPresentButVitalsEmpty?: number;\n  hl7ParsedToVitalsNonEmpty?: number;\n  vitalUpdatesWrittenToPatientDb?: number;\n}\n\n',
]:
    if old in content:
        content = content.replace(old, '')
        print("Removed HealthIngest interface")

# 2. Remove healthIngest state
content = content.replace(
    '  const [healthIngest, setHealthIngest] = useState<HealthIngest | null>(null);\n',
    ''
)
print("Removed healthIngest state" if '  const [healthIngest' not in content else "healthIngest state still present")

# 3. Remove the healthIngest useEffect (from "useEffect(() => {\n    if (hasLiveVitals) {\n      setHealthIngest" to "}, [hasLiveVitals, patientId]);")
import re
pattern = r'  useEffect\(\(\) => \{\n    if \(hasLiveVitals\) \{\n      setHealthIngest\(null\);.*?\}, \[hasLiveVitals, patientId\]\);\n'
result = re.sub(pattern, '', content, flags=re.DOTALL)
if result != content:
    content = result
    print("Removed healthIngest useEffect")
else:
    print("healthIngest useEffect pattern not matched - trying alternative")

# 4. Add DeviceStatusBadge component after the msAgoLabel function
device_badge_component = '''
function DeviceStatusBadge({
  hasLiveVitals,
  lastRealVitalsMs,
  linkedDeviceLastSeenMs,
}: {
  hasLiveVitals: boolean;
  lastRealVitalsMs: number | null | undefined;
  linkedDeviceLastSeenMs: number | null | undefined;
}) {
  const deviceOnline =
    (linkedDeviceLastSeenMs ?? 0) > 0 &&
    Date.now() - (linkedDeviceLastSeenMs ?? 0) < 120_000;

  const cls = hasLiveVitals
    ? 'bg-emerald-50 border-emerald-200 text-emerald-800'
    : deviceOnline
      ? 'bg-sky-50 border-sky-200 text-sky-800'
      : 'bg-zinc-100 border-zinc-200 text-zinc-500';

  const dotCls = hasLiveVitals
    ? 'bg-emerald-500 animate-pulse'
    : deviceOnline
      ? 'bg-sky-400 animate-pulse'
      : 'bg-zinc-400';

  const label = hasLiveVitals
    ? `Jonli vitallar — oxirgi: ${msAgoLabel(lastRealVitalsMs)}`
    : deviceOnline
      ? `Qurilma ulangan (${msAgoLabel(linkedDeviceLastSeenMs)})`
      : `Qurilma signal yo'q — ${msAgoLabel(linkedDeviceLastSeenMs)}`;

  return (
    <div className={`flex items-center gap-2 px-3 py-2 rounded-lg text-xs font-medium border ${cls}`}>
      <span className={`w-2 h-2 rounded-full shrink-0 ${dotCls}`} />
      {label}
    </div>
  );
}

'''

# Insert after msAgoLabel function (find the closing } of msAgoLabel)
insert_after = 'function msAgoLabel(ms: number | null | undefined): string {\n  if (ms == null || ms <= 0) return \'\u2014\';\n  try {\n    return formatDistanceToNow(ms, { addSuffix: true, locale: uz });\n  } catch {\n    return \'\u2014\';\n  }\n}'
insert_after2 = "function msAgoLabel(ms: number | null | undefined): string {\n  if (ms == null || ms <= 0) return '\u2014';\n  try {\n    return formatDistanceToNow(ms, { addSuffix: true, locale: uz });\n  } catch {\n    return '\u2014';\n  }\n}"

idx = content.find(insert_after)
if idx < 0:
    idx = content.find(insert_after2)
    if idx >= 0:
        end_idx = idx + len(insert_after2)
    else:
        # try with em-dash variants
        idx = content.find("function msAgoLabel")
        if idx >= 0:
            end_idx = content.find('\n}', idx) + 2
        else:
            end_idx = -1
else:
    end_idx = idx + len(insert_after)

if end_idx > 0:
    content = content[:end_idx] + device_badge_component + content[end_idx:]
    print("Added DeviceStatusBadge component")
else:
    print("Could not find msAgoLabel end - badge not added")

# Save
with open(TARGET, 'w', encoding='utf-8') as f:
    f.write(content)
print(f"Done. File size: {len(content)} chars")
