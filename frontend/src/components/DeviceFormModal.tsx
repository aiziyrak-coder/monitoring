import { useEffect, useState, type FormEvent } from 'react';
import { X, MonitorSmartphone, MapPin } from 'lucide-react';
import { apiUrl } from '../lib/api';
import { cascadeFromBedId, LocationCascadeSelects } from './LocationCascadeSelects';

type Infra = {
  departments: any[];
  rooms: any[];
  beds: any[];
};

type DeviceRow = {
  id: string;
  ipAddress?: string;
  macAddress?: string;
  model?: string;
  hl7SendingApplication?: string;
  hl7NatSourceIp?: string | null;
  bedId?: string | null;
};

/** Yangi qurilma / tahrirlash — joy tanlash birinchi bo‘lib, katta ko‘rinishda. */
export function DeviceFormModal({
  open,
  onClose,
  onSaved,
  onError,
  infra,
  editingDevice,
}: {
  open: boolean;
  onClose: () => void;
  onSaved: () => void;
  onError: (msg: string) => void;
  infra: Infra;
  editingDevice: DeviceRow | null;
}) {
  const { departments = [], rooms = [], beds = [] } = infra;
  const isEdit = Boolean(editingDevice);

  const [departmentId, setDepartmentId] = useState('');
  const [roomId, setRoomId] = useState('');
  const [bedId, setBedId] = useState('');
  const [ipAddress, setIpAddress] = useState('');
  const [macAddress, setMacAddress] = useState('');
  const [model, setModel] = useState('');
  const [hl7SendingApplication, setHl7SendingApplication] = useState('');
  const [hl7NatSourceIp, setHl7NatSourceIp] = useState('');
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    if (!open) return;
    if (editingDevice) {
      setIpAddress(editingDevice.ipAddress ?? '');
      setMacAddress(editingDevice.macAddress ?? '');
      setModel(editingDevice.model ?? '');
      setHl7SendingApplication(editingDevice.hl7SendingApplication ?? '');
      setHl7NatSourceIp(editingDevice.hl7NatSourceIp ?? '');
      const c = cascadeFromBedId(editingDevice.bedId, beds, rooms);
      setDepartmentId(c.departmentId);
      setRoomId(c.roomId);
      setBedId(c.bedId);
    } else {
      setDepartmentId('');
      setRoomId('');
      setBedId('');
      setIpAddress('');
      setMacAddress('');
      setModel('');
      setHl7SendingApplication('');
      setHl7NatSourceIp('');
    }
  }, [open, editingDevice, beds, rooms]);

  if (!open) return null;

  const hasBeds = beds.length > 0;

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    if (!ipAddress.trim()) {
      onError('IP manzilni kiriting.');
      return;
    }
    setSaving(true);
    try {
      const body = {
        ipAddress: ipAddress.trim(),
        macAddress: macAddress.trim(),
        model: model.trim(),
        hl7SendingApplication: hl7SendingApplication.trim(),
        hl7NatSourceIp: hl7NatSourceIp.trim(),
        bedId: bedId || '',
      };
      const url = isEdit
        ? apiUrl(`/api/devices/${editingDevice!.id}`)
        : apiUrl('/api/devices');
      const res = await fetch(url, {
        method: isEdit ? 'PUT' : 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
      });
      if (!res.ok) {
        const errBody = await res.json().catch(() => ({}));
        const msg = typeof errBody?.detail === 'string' ? errBody.detail : 'Saqlashda xatolik';
        throw new Error(msg);
      }
      onSaved();
      onClose();
    } catch (e) {
      onError(e instanceof Error ? e.message : 'Saqlashda xatolik yuz berdi.');
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="fixed inset-0 z-[100] flex items-center justify-center bg-zinc-900/50 backdrop-blur-sm p-4">
      <div className="bg-white rounded-2xl shadow-2xl w-full max-w-lg max-h-[92vh] overflow-hidden flex flex-col border border-zinc-200">
        <div className="flex items-start justify-between p-5 border-b border-zinc-200 bg-emerald-50/60">
          <div className="flex items-center gap-3">
            <div className="p-2.5 bg-emerald-100 rounded-xl border border-emerald-200">
              <MonitorSmartphone className="w-6 h-6 text-emerald-700" />
            </div>
            <div>
              <h2 className="text-lg font-bold text-zinc-900 leading-snug">
                {isEdit
                  ? 'Qurilmani tahrirlash (xona/joy + tarmoq)'
                  : 'Yangi qurilma — avval XONA va JOY tanlang'}
              </h2>
              <p className="text-xs text-emerald-800 mt-1 leading-relaxed max-w-sm">
                Avval <strong>qaysi xonaning qaysi joyiga</strong> tegishliligini tanlang. Bemor shu joyga{' '}
                <strong>qabul qilinganda</strong> monitor (HL7) ma’lumotlari shu bemor kartasiga chiqadi.
              </p>
            </div>
          </div>
          <button
            type="button"
            onClick={onClose}
            className="p-2 rounded-lg text-zinc-500 hover:bg-white hover:text-zinc-900"
            aria-label="Yopish"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        <form onSubmit={handleSubmit} className="flex flex-col flex-1 min-h-0">
          <div className="overflow-y-auto flex-1 px-5 py-4 space-y-5">
            <div className="rounded-xl border-2 border-emerald-200 bg-emerald-50/40 p-4">
              <label className="flex items-center gap-2 text-sm font-semibold text-emerald-900 mb-3">
                <MapPin className="w-4 h-4" />
                Bo‘lim, palata, karavat
              </label>
              {!hasBeds ? (
                <p className="text-sm text-amber-800 bg-amber-50 border border-amber-200 rounded-lg p-3">
                  Hozircha joy yo‘q. «Tuzilma» bo‘limida bo‘lim → xona → joy yarating, keyin bu oynani qayta oching.
                </p>
              ) : (
                <LocationCascadeSelects
                  departments={departments}
                  rooms={rooms}
                  beds={beds}
                  departmentId={departmentId}
                  roomId={roomId}
                  bedId={bedId}
                  onDepartmentChange={setDepartmentId}
                  onRoomChange={setRoomId}
                  onBedChange={setBedId}
                  emphasize
                />
              )}
            </div>

            <div>
              <label htmlFor="device-ip" className="block text-sm font-medium text-zinc-700 mb-1">
                IP manzil (monitorning lokal tarmoq manzili)
              </label>
              <input
                id="device-ip"
                type="text"
                required
                value={ipAddress}
                onChange={(e) => setIpAddress(e.target.value)}
                placeholder="192.168.0.228"
                className="w-full border border-zinc-300 rounded-lg px-3 py-2.5 text-zinc-900 focus:ring-2 focus:ring-emerald-500/30 focus:border-emerald-500"
              />
              <p className="text-[11px] text-zinc-500 mt-1 leading-snug">
                Bulut serverga HL7 chiqarilsa, server ko‘radigan manzil odatda routerning <strong>tashqi</strong> IPsi
                bo‘ladi — pastdagi «NAT tashqi IP» maydoniga shuni kiriting; bir nechta monitor bo‘lsa HL7 MSH-3 majburiy.
              </p>
            </div>
            <div>
              <label htmlFor="device-nat" className="block text-sm font-medium text-zinc-700 mb-1">
                NAT tashqi IP (HL7 uchun, ixtiyoriy)
              </label>
              <input
                id="device-nat"
                type="text"
                value={hl7NatSourceIp}
                onChange={(e) => setHl7NatSourceIp(e.target.value)}
                placeholder="Masalan klinikaning Internet IP (91.x.y.z)"
                className="w-full border border-zinc-300 rounded-lg px-3 py-2.5 text-zinc-900 focus:ring-2 focus:ring-emerald-500/30 focus:border-emerald-500"
              />
            </div>
            <div>
              <label htmlFor="device-mac" className="block text-sm font-medium text-zinc-700 mb-1">
                MAC manzil
              </label>
              <input
                id="device-mac"
                type="text"
                value={macAddress}
                onChange={(e) => setMacAddress(e.target.value)}
                placeholder="02:03:06:02:A3:F0"
                className="w-full border border-zinc-300 rounded-lg px-3 py-2.5 text-zinc-900 focus:ring-2 focus:ring-emerald-500/30 focus:border-emerald-500"
              />
            </div>
            <div>
              <label htmlFor="device-model" className="block text-sm font-medium text-zinc-700 mb-1">
                Model
              </label>
              <input
                id="device-model"
                type="text"
                value={model}
                onChange={(e) => setModel(e.target.value)}
                placeholder="Mindray uMEC10"
                className="w-full border border-zinc-300 rounded-lg px-3 py-2.5 text-zinc-900 focus:ring-2 focus:ring-emerald-500/30 focus:border-emerald-500"
              />
            </div>
            <div>
              <label htmlFor="device-hl7" className="block text-sm font-medium text-zinc-700 mb-1">
                HL7 MSH-3 (yuboruvchi ID, Mindray xabari bilan bir xil bo‘lsin)
              </label>
              <input
                id="device-hl7"
                type="text"
                value={hl7SendingApplication}
                onChange={(e) => setHl7SendingApplication(e.target.value)}
                placeholder="Bo‘sh qoldiring yoki monitor MSH-3 dagi qiymat"
                className="w-full border border-zinc-300 rounded-lg px-3 py-2.5 text-zinc-900 focus:ring-2 focus:ring-emerald-500/30 focus:border-emerald-500"
              />
            </div>
          </div>

          <div className="flex justify-end gap-2 px-5 py-4 border-t border-zinc-200 bg-zinc-50">
            <button
              type="button"
              onClick={onClose}
              className="px-4 py-2.5 text-zinc-600 hover:text-zinc-900"
            >
              Bekor qilish
            </button>
            <button
              type="submit"
              disabled={saving}
              className="px-5 py-2.5 rounded-lg bg-emerald-600 text-white font-medium hover:bg-emerald-500 disabled:opacity-50"
            >
              {saving ? 'Saqlanmoqda…' : 'Saqlash'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}

/** Faqat joyni o‘zgartirish / biriktirish. */
export function DeviceBedAssignModal({
  open,
  onClose,
  onSaved,
  onError,
  infra,
  device,
}: {
  open: boolean;
  onClose: () => void;
  onSaved: () => void;
  onError: (msg: string) => void;
  infra: Infra;
  device: DeviceRow | null;
}) {
  const { departments = [], rooms = [], beds = [] } = infra;
  const [departmentId, setDepartmentId] = useState('');
  const [roomId, setRoomId] = useState('');
  const [bedId, setBedId] = useState('');
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    if (open && device) {
      const c = cascadeFromBedId(device.bedId, beds, rooms);
      setDepartmentId(c.departmentId);
      setRoomId(c.roomId);
      setBedId(c.bedId);
    }
  }, [open, device, beds, rooms]);

  if (!open || !device) return null;

  const hasBeds = beds.length > 0;

  const submit = async (e: FormEvent) => {
    e.preventDefault();
    setSaving(true);
    try {
      const res = await fetch(apiUrl(`/api/devices/${device.id}`), {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ bedId: bedId || '' }),
      });
      if (!res.ok) throw new Error('xato');
      onSaved();
      onClose();
    } catch {
      onError('Saqlashda xatolik.');
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="fixed inset-0 z-[100] flex items-center justify-center bg-zinc-900/50 backdrop-blur-sm p-4">
      <div className="bg-white rounded-2xl shadow-2xl w-full max-w-md border border-zinc-200 p-6">
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-lg font-bold text-zinc-900">Joyga biriktirish</h3>
          <button type="button" onClick={onClose} className="p-2 text-zinc-500 hover:bg-zinc-100 rounded-lg">
            <X className="w-5 h-5" />
          </button>
        </div>
        <p className="text-sm text-zinc-600 mb-4">
          Qurilma: <span className="font-mono text-zinc-800">{device.model}</span> ({device.id})
        </p>
        <form onSubmit={submit} className="space-y-4">
          {!hasBeds ? (
            <p className="text-sm text-amber-800">Avval «Tuzilma»da joy yarating.</p>
          ) : (
            <LocationCascadeSelects
              departments={departments}
              rooms={rooms}
              beds={beds}
              departmentId={departmentId}
              roomId={roomId}
              bedId={bedId}
              onDepartmentChange={setDepartmentId}
              onRoomChange={setRoomId}
              onBedChange={setBedId}
            />
          )}
          <div className="flex justify-end gap-2 pt-2">
            <button type="button" onClick={onClose} className="px-4 py-2 text-zinc-600">
              Bekor qilish
            </button>
            <button
              type="submit"
              disabled={saving || !hasBeds}
              className="px-4 py-2 rounded-lg bg-emerald-600 text-white hover:bg-emerald-500 disabled:opacity-50"
            >
              Saqlash
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
