import { useState, useEffect } from 'react';
import { X, Server, Building2, MonitorSmartphone, Users, Plus, Trash2, Edit2, Info, AlertTriangle, Link2, UserPlus } from 'lucide-react';
import { apiUrl, hl7ServerDisplay } from '../lib/api';
import { useStore } from '../store';
import { AdmitPatientModal } from './AdmitPatientModal';
import { DeviceBedAssignModal, DeviceFormModal } from './DeviceFormModal';
import { formatBedLocationLine } from './LocationCascadeSelects';

function formatLastSeenRelative(ms: number | null | undefined): string {
  if (ms == null) return '—';
  const age = Date.now() - ms;
  if (age < 15_000) return 'hozir';
  if (age < 60_000) return `${Math.floor(age / 1000)} s oldin`;
  const m = Math.floor(age / 60_000);
  if (m < 120) return `${m} daq oldin`;
  const h = Math.floor(m / 60);
  return `${h} soat oldin`;
}

interface SettingsModalProps {
  onClose: () => void;
}

type SettingsPromptField =
  | { name: string; label: string; placeholder?: string; kind?: 'text' }
  | { name: string; label: string; kind: 'select'; options: { value: string; label: string }[] };

// Custom Dialogs to replace prompt/confirm in iframe
function CustomPrompt({ isOpen, title, description, fields, initialValues, onSubmit, onCancel }: { isOpen: boolean, title: string, description?: string, fields: SettingsPromptField[], initialValues?: Record<string, string>, onSubmit: (data: any) => void, onCancel: () => void }) {
  const [values, setValues] = useState<Record<string, string>>({});
  
  useEffect(() => {
    if (isOpen) setValues(initialValues ? { ...initialValues } : {});
  }, [isOpen, initialValues]);

  if (!isOpen) return null;

  const firstTextIdx = fields.findIndex(f => (f as { kind?: string }).kind !== 'select');

  return (
    <div className="fixed inset-0 z-[60] flex items-center justify-center bg-zinc-900/40 backdrop-blur-sm p-4">
      <div className="bg-white border border-zinc-200 rounded-xl w-full max-w-lg max-h-[90vh] shadow-2xl overflow-hidden flex flex-col">
        <div className="px-6 pt-5 pb-2 shrink-0 border-b border-zinc-100">
          <h3 className="text-lg font-bold text-zinc-900">{title}</h3>
          {description ? (
            <p className="text-xs text-zinc-500 mt-2 leading-relaxed">{description}</p>
          ) : null}
        </div>
        <form onSubmit={(e) => { e.preventDefault(); onSubmit(values); }} className="flex flex-col min-h-0 flex-1 px-6 pb-5 pt-4">
          <div className="space-y-4 mb-4 overflow-y-auto min-h-0 max-h-[min(52vh,420px)] pr-1 -mr-1">
            {fields.map((f, idx) => (
              <div key={f.name}>
                <label className="block text-sm text-zinc-600 mb-1">{f.label}</label>
                {f.kind === 'select' ? (
                  <select
                    value={values[f.name] ?? ''}
                    onChange={e => setValues({ ...values, [f.name]: e.target.value })}
                    className="w-full bg-zinc-50 border border-zinc-200 rounded-lg p-2 text-zinc-900 focus:border-emerald-500 outline-none"
                  >
                    {f.options.map(opt => (
                      <option key={opt.value === '' ? '__empty' : opt.value} value={opt.value}>
                        {opt.label}
                      </option>
                    ))}
                  </select>
                ) : (
                  <input 
                    type="text" 
                    value={values[f.name] || ''}
                    onChange={e => setValues({...values, [f.name]: e.target.value})}
                    placeholder={(f as { placeholder?: string }).placeholder}
                    className="w-full bg-zinc-50 border border-zinc-200 rounded-lg p-2 text-zinc-900 focus:border-emerald-500 outline-none"
                    autoFocus={firstTextIdx === idx}
                  />
                )}
              </div>
            ))}
          </div>
          <div className="flex justify-end space-x-3 pt-2 border-t border-zinc-100 shrink-0 mt-auto">
            <button type="button" onClick={onCancel} className="px-4 py-2 text-zinc-500 hover:text-zinc-900 transition-colors">Bekor qilish</button>
            <button type="submit" className="px-4 py-2 bg-emerald-500 text-white rounded-lg hover:bg-emerald-600 transition-colors">Saqlash</button>
          </div>
        </form>
      </div>
    </div>
  );
}

function CustomConfirm({ isOpen, title, message, onConfirm, onCancel }: { isOpen: boolean, title: string, message: string, onConfirm: () => void, onCancel: () => void }) {
  if (!isOpen) return null;
  return (
    <div className="fixed inset-0 z-[60] flex items-center justify-center bg-zinc-900/40 backdrop-blur-sm p-4">
      <div className="bg-white border border-zinc-200 rounded-xl w-full max-w-sm p-6 shadow-2xl">
        <div className="flex items-center space-x-3 mb-4 text-red-600">
          <AlertTriangle className="w-6 h-6" />
          <h3 className="text-lg font-bold">{title}</h3>
        </div>
        <p className="text-zinc-600 mb-6">{message}</p>
        <div className="flex justify-end space-x-3">
          <button onClick={onCancel} className="px-4 py-2 text-zinc-500 hover:text-zinc-900 transition-colors">Yo'q</button>
          <button onClick={onConfirm} className="px-4 py-2 bg-red-500 text-white rounded-lg hover:bg-red-600 transition-colors">Ha, o'chirish</button>
        </div>
      </div>
    </div>
  );
}

export function SettingsModal({ onClose }: SettingsModalProps) {
  const [activeTab, setActiveTab] = useState<'structure' | 'devices' | 'patients' | 'integration'>('structure');
  const [data, setData] = useState<any>({ departments: [], rooms: [], beds: [], devices: [] });
  const { patients, dischargePatient } = useStore();
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [showAdmitPatient, setShowAdmitPatient] = useState(false);
  const [deviceFormOpen, setDeviceFormOpen] = useState(false);
  const [deviceFormEditing, setDeviceFormEditing] = useState<any | null>(null);
  const [bedAssignOpen, setBedAssignOpen] = useState(false);
  const [bedAssignDevice, setBedAssignDevice] = useState<any | null>(null);

  // Dialog states
  const [promptConfig, setPromptConfig] = useState<{isOpen: boolean, title: string, description?: string, fields: SettingsPromptField[], initialValues?: Record<string, string>, onSubmit: (data: any) => void} | null>(null);
  const [confirmConfig, setConfirmConfig] = useState<{isOpen: boolean, title: string, message: string, onConfirm: () => void} | null>(null);

  const fetchData = async (signal?: AbortSignal) => {
    try {
      const res = await fetch(apiUrl('/api/infrastructure'), { signal });
      if (!res.ok) throw new Error("Ma'lumotlarni yuklashda xatolik");
      const json = await res.json();
      setData(json);
      setLoading(false);
    } catch (e: any) {
      if (e.name === 'AbortError') return;
      console.error(e);
      setError(e.message);
      setLoading(false);
    }
  };

  useEffect(() => {
    const controller = new AbortController();
    fetchData(controller.signal);
    return () => controller.abort();
  }, []);

  useEffect(() => {
    if (activeTab !== 'devices') return;
    fetchData();
    const id = setInterval(() => fetchData(), 12_000);
    return () => clearInterval(id);
  }, [activeTab]);

  const closeDialogs = () => {
    setPromptConfig(null);
    setConfirmConfig(null);
    setDeviceFormOpen(false);
    setDeviceFormEditing(null);
    setBedAssignOpen(false);
    setBedAssignDevice(null);
  };

  const addDepartment = () => {
    setPromptConfig({
      isOpen: true,
      title: "Yangi bo'lim qo'shish",
      fields: [{ name: 'name', label: "Bo'lim nomi", placeholder: "Masalan: Reanimatsiya" }],
      onSubmit: async (vals) => {
        if (!vals.name) return closeDialogs();
        try {
          await fetch(apiUrl('/api/departments'), { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ name: vals.name }) });
          closeDialogs();
          fetchData();
        } catch (e) {
          console.error(e);
          setError("Xatolik yuz berdi");
        }
      }
    });
  };

  const deleteDepartment = (id: string) => {
    setConfirmConfig({
      isOpen: true,
      title: "Bo'limni o'chirish",
      message: "Rostdan ham bu bo'limni o'chirmoqchimisiz?",
      onConfirm: async () => {
        try {
          await fetch(apiUrl(`/api/departments/${id}`), { method: 'DELETE' });
          closeDialogs();
          fetchData();
        } catch (e) {
          console.error(e);
          setError("Xatolik yuz berdi");
        }
      }
    });
  };

  const addRoom = (deptId: string) => {
    setPromptConfig({
      isOpen: true,
      title: "Yangi palata qo'shish",
      fields: [{ name: 'name', label: "Palata nomi", placeholder: "Masalan: Palata-1" }],
      onSubmit: async (vals) => {
        if (!vals.name) return closeDialogs();
        try {
          await fetch(apiUrl('/api/rooms'), { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ name: vals.name, departmentId: deptId }) });
          closeDialogs();
          fetchData();
        } catch (e) {
          console.error(e);
          setError("Xatolik yuz berdi");
        }
      }
    });
  };

  const deleteRoom = (id: string) => {
    setConfirmConfig({
      isOpen: true,
      title: "Palatani o'chirish",
      message: "Rostdan ham bu palatani o'chirmoqchimisiz?",
      onConfirm: async () => {
        try {
          await fetch(apiUrl(`/api/rooms/${id}`), { method: 'DELETE' });
          closeDialogs();
          fetchData();
        } catch (e) {
          console.error(e);
          setError("Xatolik yuz berdi");
        }
      }
    });
  };

  const addBed = (roomId: string) => {
    setPromptConfig({
      isOpen: true,
      title: "Yangi joy qo'shish",
      fields: [{ name: 'name', label: "Joy nomi", placeholder: "Masalan: Joy-1" }],
      onSubmit: async (vals) => {
        if (!vals.name) return closeDialogs();
        try {
          await fetch(apiUrl('/api/beds'), { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ name: vals.name, roomId }) });
          closeDialogs();
          fetchData();
        } catch (e) {
          console.error(e);
          setError("Xatolik yuz berdi");
        }
      }
    });
  };

  const deleteBed = (id: string) => {
    setConfirmConfig({
      isOpen: true,
      title: "Joyni o'chirish",
      message: "Rostdan ham bu joyni o'chirmoqchimisiz?",
      onConfirm: async () => {
        try {
          await fetch(apiUrl(`/api/beds/${id}`), { method: 'DELETE' });
          closeDialogs();
          fetchData();
        } catch (e) {
          console.error(e);
          setError("Xatolik yuz berdi");
        }
      }
    });
  };

  const addDevice = () => {
    setDeviceFormEditing(null);
    setDeviceFormOpen(true);
  };

  const editDevice = (device: { id: string; ipAddress?: string; macAddress?: string; model?: string; hl7SendingApplication?: string; bedId?: string | null }) => {
    setDeviceFormEditing(device);
    setDeviceFormOpen(true);
  };

  const assignBedToDevice = (device: { id: string; bedId?: string | null }) => {
    setBedAssignDevice(device);
    setBedAssignOpen(true);
  };

  const deleteDevice = (id: string) => {
    setConfirmConfig({
      isOpen: true,
      title: "Qurilmani o'chirish",
      message: "Rostdan ham bu qurilmani o'chirmoqchimisiz?",
      onConfirm: async () => {
        try {
          await fetch(apiUrl(`/api/devices/${id}`), { method: 'DELETE' });
          closeDialogs();
          fetchData();
        } catch (e) {
          console.error(e);
          setError("Xatolik yuz berdi");
        }
      }
    });
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-zinc-900/40 backdrop-blur-sm p-4">
      
      {showAdmitPatient && (
        <AdmitPatientModal
          onClose={() => setShowAdmitPatient(false)}
        />
      )}
      <DeviceFormModal
        open={deviceFormOpen}
        editingDevice={deviceFormEditing}
        infra={{
          departments: data.departments,
          rooms: data.rooms,
          beds: data.beds,
        }}
        onClose={() => {
          setDeviceFormOpen(false);
          setDeviceFormEditing(null);
        }}
        onSaved={() => void fetchData()}
        onError={(msg) => setError(msg)}
      />
      <DeviceBedAssignModal
        open={bedAssignOpen}
        device={bedAssignDevice}
        infra={{
          departments: data.departments,
          rooms: data.rooms,
          beds: data.beds,
        }}
        onClose={() => {
          setBedAssignOpen(false);
          setBedAssignDevice(null);
        }}
        onSaved={() => void fetchData()}
        onError={(msg) => setError(msg)}
      />
      {promptConfig && <CustomPrompt {...promptConfig} onCancel={closeDialogs} />}
      {confirmConfig && <CustomConfirm {...confirmConfig} onCancel={closeDialogs} />}

      <div className="bg-white border border-zinc-200 rounded-2xl w-full max-w-5xl max-h-[90vh] flex flex-col shadow-2xl overflow-hidden">
        
        {/* Header */}
        <div className="flex items-center justify-between p-6 border-b border-zinc-200 bg-zinc-50">
          <div className="flex items-center space-x-3">
            <div className="p-2 bg-emerald-100 rounded-lg border border-emerald-200">
              <Server className="w-6 h-6 text-emerald-600" />
            </div>
            <div>
              <h2 className="text-xl font-bold text-zinc-900">Tizim Sozlamalari</h2>
              <p className="text-sm text-zinc-500">Infratuzilma, qurilmalar va integratsiya</p>
            </div>
          </div>
          <button onClick={onClose} className="p-2 text-zinc-500 hover:text-zinc-900 hover:bg-zinc-100 rounded-lg transition-colors">
            <X className="w-6 h-6" />
          </button>
        </div>

        <div className="flex flex-1 overflow-hidden">
          {/* Sidebar */}
          <div className="w-64 border-r border-zinc-200 bg-zinc-50 p-4 space-y-2">
            <button
              onClick={() => setActiveTab('structure')}
              className={`w-full flex items-center space-x-3 px-4 py-3 rounded-xl transition-colors ${activeTab === 'structure' ? 'bg-emerald-50 text-emerald-600 border border-emerald-200' : 'text-zinc-600 hover:bg-zinc-100 hover:text-zinc-900'}`}
            >
              <Building2 className="w-5 h-5" />
              <span className="font-medium">Tuzilma</span>
            </button>
            <button
              onClick={() => setActiveTab('devices')}
              className={`w-full flex items-center space-x-3 px-4 py-3 rounded-xl transition-colors ${activeTab === 'devices' ? 'bg-emerald-50 text-emerald-600 border border-emerald-200' : 'text-zinc-600 hover:bg-zinc-100 hover:text-zinc-900'}`}
            >
              <MonitorSmartphone className="w-5 h-5" />
              <span className="font-medium">Qurilmalar</span>
            </button>
            <button
              onClick={() => setActiveTab('patients')}
              className={`w-full flex items-center space-x-3 px-4 py-3 rounded-xl transition-colors ${activeTab === 'patients' ? 'bg-emerald-50 text-emerald-600 border border-emerald-200' : 'text-zinc-600 hover:bg-zinc-100 hover:text-zinc-900'}`}
            >
              <Users className="w-5 h-5" />
              <span className="font-medium">Bemorlar</span>
            </button>
            <button
              onClick={() => setActiveTab('integration')}
              className={`w-full flex items-center space-x-3 px-4 py-3 rounded-xl transition-colors ${activeTab === 'integration' ? 'bg-emerald-50 text-emerald-600 border border-emerald-200' : 'text-zinc-600 hover:bg-zinc-100 hover:text-zinc-900'}`}
            >
              <Info className="w-5 h-5" />
              <span className="font-medium">Integratsiya</span>
            </button>
          </div>

          {/* Content */}
          <div className="flex-1 overflow-y-auto p-6 bg-white">
            {error && (
              <div className="mb-6 bg-red-50 border border-red-200 text-red-600 p-4 rounded-xl flex items-center">
                <AlertTriangle className="w-5 h-5 mr-3" />
                {error}
              </div>
            )}
            {loading ? (
              <div className="flex items-center justify-center h-full text-zinc-500">Yuklanmoqda...</div>
            ) : (
              <>
                {/* Structure Tab */}
                {activeTab === 'structure' && (
                  <div className="space-y-6">
                    <div className="flex items-center justify-between">
                      <h3 className="text-lg font-medium text-zinc-900">Kasalxona Tuzilmasi</h3>
                      <button onClick={addDepartment} className="flex items-center px-3 py-1.5 bg-emerald-100 text-emerald-600 rounded-lg hover:bg-emerald-200 transition-colors text-sm">
                        <Plus className="w-4 h-4 mr-1" /> Bo'lim qo'shish
                      </button>
                    </div>
                    
                    <div className="space-y-4">
                      {data.departments.map((dept: any) => (
                        <div key={dept.id} className="bg-zinc-50 border border-zinc-200 rounded-xl p-4">
                          <div className="flex items-center justify-between mb-4">
                            <h4 className="text-md font-bold text-emerald-600">{dept.name} (ID: {dept.id})</h4>
                            <div className="flex space-x-2">
                              <button onClick={() => addRoom(dept.id)} className="p-1.5 text-zinc-500 hover:text-emerald-600 bg-white border border-zinc-200 rounded-md"><Plus className="w-4 h-4" /></button>
                              <button onClick={() => deleteDepartment(dept.id)} className="p-1.5 text-zinc-500 hover:text-red-600 bg-white border border-zinc-200 rounded-md"><Trash2 className="w-4 h-4" /></button>
                            </div>
                          </div>
                          
                          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                            {data.rooms.filter((r: any) => r.departmentId === dept.id).map((room: any) => (
                              <div key={room.id} className="bg-white border border-zinc-200 rounded-lg p-3 shadow-sm">
                                <div className="flex items-center justify-between mb-2">
                                  <span className="font-medium text-zinc-900">{room.name}</span>
                                  <div className="flex space-x-2">
                                    <button onClick={() => addBed(room.id)} className="p-1 text-zinc-500 hover:text-emerald-600"><Plus className="w-3 h-3" /></button>
                                    <button onClick={() => deleteRoom(room.id)} className="p-1 text-zinc-500 hover:text-red-600"><Trash2 className="w-3 h-3" /></button>
                                  </div>
                                </div>
                                <div className="flex flex-wrap gap-2">
                                  {data.beds.filter((b: any) => b.roomId === room.id).map((bed: any) => (
                                    <div key={bed.id} className="flex items-center px-2 py-1 bg-zinc-50 rounded text-xs text-zinc-600 border border-zinc-200">
                                      {bed.name} (ID: {bed.id})
                                      <button onClick={() => deleteBed(bed.id)} className="ml-2 text-zinc-500 hover:text-red-600"><X className="w-3 h-3" /></button>
                                    </div>
                                  ))}
                                  {data.beds.filter((b: any) => b.roomId === room.id).length === 0 && (
                                    <span className="text-xs text-zinc-500 italic">Joylar yo'q</span>
                                  )}
                                </div>
                              </div>
                            ))}
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>
                )}

                {/* Devices Tab */}
                {activeTab === 'devices' && (
                  <div className="space-y-6">
                    <div className="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
                      <div>
                        <h3 className="text-lg font-medium text-zinc-900">Bemor Monitorlari</h3>
                        <p className="text-xs text-zinc-500 mt-1">
                          Joyni «Tuzilma»da yarating, keyin qurilma qo&apos;shganda yoki «Joyga biriktirish» bilan tanlang.
                        </p>
                      </div>
                      <button onClick={addDevice} className="flex items-center px-3 py-1.5 bg-emerald-100 text-emerald-600 rounded-lg hover:bg-emerald-200 transition-colors text-sm shrink-0">
                        <Plus className="w-4 h-4 mr-1" /> Qurilma qo'shish
                      </button>
                    </div>

                    <div className="overflow-x-auto">
                      <table className="w-full text-sm text-left text-zinc-600">
                        <thead className="text-xs text-zinc-500 uppercase bg-zinc-50 border-b border-zinc-200">
                          <tr>
                            <th className="px-4 py-3">ID / Model</th>
                            <th className="px-4 py-3">Tarmoq (IP / MAC / NAT)</th>
                            <th className="px-4 py-3">HL7 ID</th>
                            <th className="px-4 py-3">Biriktirilgan joy</th>
                            <th className="px-4 py-3">Holati</th>
                            <th className="px-4 py-3 text-right">Amallar</th>
                          </tr>
                        </thead>
                        <tbody>
                          {data.devices.map((device: any) => (
                            <tr key={device.id} className="border-b border-zinc-100 hover:bg-zinc-50">
                              <td className="px-4 py-3">
                                <div className="font-medium text-zinc-900">{device.model}</div>
                                <div className="text-xs font-mono text-zinc-500">{device.id}</div>
                              </td>
                              <td className="px-4 py-3 font-mono text-xs">
                                <div>{device.ipAddress}</div>
                                <div className="text-zinc-500">{device.macAddress}</div>
                                {device.hl7NatSourceIp ? (
                                  <div className="text-emerald-700 mt-0.5" title="HL7 peer = router tashqi IP">
                                    NAT: {device.hl7NatSourceIp}
                                  </div>
                                ) : null}
                              </td>
                              <td className="px-4 py-3 text-xs font-mono text-zinc-600 max-w-[140px] truncate" title={device.hl7SendingApplication || ''}>
                                {device.hl7SendingApplication || '—'}
                              </td>
                              <td className="px-4 py-3 max-w-[min(280px,36vw)]">
                                {device.bedId ? (
                                  <div className="flex flex-col gap-1 items-start">
                                    <span
                                      className="text-sm text-zinc-800 leading-snug"
                                      title={device.bedId}
                                    >
                                      {formatBedLocationLine(
                                        device.bedId,
                                        data.beds || [],
                                        data.rooms || [],
                                        data.departments || []
                                      )}
                                    </span>
                                    <span className="text-[10px] font-mono text-zinc-400">ID: {device.bedId}</span>
                                    <button
                                      type="button"
                                      onClick={() => assignBedToDevice(device)}
                                      className="text-xs text-blue-600 hover:underline"
                                    >
                                      Boshqa joyga
                                    </button>
                                  </div>
                                ) : (
                                  <div className="flex flex-col gap-1 items-start max-w-[200px]">
                                    <span className="text-zinc-500 italic text-xs">Biriktirilmagan</span>
                                    <button
                                      type="button"
                                      onClick={() => assignBedToDevice(device)}
                                      className="text-xs font-medium text-emerald-600 bg-emerald-50 border border-emerald-200 rounded-md px-2 py-1 hover:bg-emerald-100"
                                    >
                                      Joyga biriktirish
                                    </button>
                                  </div>
                                )}
                              </td>
                              <td className="px-4 py-3">
                                <div className="flex items-center">
                                  <div className={`w-2 h-2 rounded-full mr-2 shrink-0 ${device.status === 'online' ? 'bg-emerald-500' : 'bg-red-500'}`}></div>
                                  <div>
                                    <span className="text-zinc-700">
                                      {device.status === 'online' ? 'Onlayn' : 'Oflayn'}
                                    </span>
                                    <div className="text-[10px] text-zinc-400 font-mono mt-0.5">
                                      {device.status === 'online'
                                        ? formatLastSeenRelative(device.lastSeen)
                                        : device.lastSeen != null
                                          ? `oxirgi: ${formatLastSeenRelative(device.lastSeen)}`
                                          : 'hech qachon'}
                                    </div>
                                  </div>
                                </div>
                              </td>
                              <td className="px-4 py-3 text-right space-x-2 whitespace-nowrap">
                                <button onClick={() => editDevice(device)} className="p-1.5 text-zinc-500 hover:text-emerald-600 bg-white border border-zinc-200 rounded-md" title="Tahrirlash"><Edit2 className="w-4 h-4" /></button>
                                <button onClick={() => assignBedToDevice(device)} className="p-1.5 text-zinc-500 hover:text-blue-600 bg-white border border-zinc-200 rounded-md" title="Joyga biriktirish (tanlash)"><Link2 className="w-4 h-4" /></button>
                                <button onClick={() => deleteDevice(device.id)} className="p-1.5 text-zinc-500 hover:text-red-600 bg-white border border-zinc-200 rounded-md" title="O'chirish"><Trash2 className="w-4 h-4" /></button>
                              </td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  </div>
                )}

                {/* Patients Tab */}
                {activeTab === 'patients' && (
                  <div className="space-y-6">
                    <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
                      <div>
                        <h3 className="text-lg font-medium text-zinc-900">Faol Bemorlar</h3>
                        <p className="text-sm text-zinc-500">
                          Bemor qabul qilish yoki asosiy ekrandagi «Bemor qabul» tugmasi — ikkalasi ham bir xil.
                        </p>
                      </div>
                      <div className="flex flex-wrap gap-2 justify-end">
                        <button
                          type="button"
                          onClick={() => setShowAdmitPatient(true)}
                          className="inline-flex items-center px-4 py-2 bg-emerald-600 text-white rounded-lg hover:bg-emerald-500 transition-colors text-sm font-medium shadow-sm"
                        >
                          <UserPlus className="w-4 h-4 mr-2" />
                          Bemor qo&apos;shish
                        </button>
                        <button
                          type="button"
                          onClick={() => {
                            useStore.getState().setAllSchedules(60000);
                            closeDialogs();
                          }}
                          className="px-4 py-2 bg-emerald-50 text-emerald-600 rounded-lg hover:bg-emerald-100 transition-colors text-sm border border-emerald-200"
                        >
                          Barchasiga 1 daqiqalik tekshiruv
                        </button>
                      </div>
                    </div>

                    <div className="grid grid-cols-1 gap-4">
                      {Object.values(patients).length === 0 && (
                        <div className="text-center py-12 px-4 bg-zinc-50 border border-dashed border-zinc-200 rounded-xl text-zinc-500 text-sm">
                          <p className="mb-4">Hozircha faol bemor yo&apos;q.</p>
                          <button
                            type="button"
                            onClick={() => setShowAdmitPatient(true)}
                            className="inline-flex items-center px-4 py-2 bg-emerald-600 text-white rounded-lg hover:bg-emerald-500 transition-colors text-sm font-medium"
                          >
                            <UserPlus className="w-4 h-4 mr-2" />
                            Bemor qo&apos;shish
                          </button>
                        </div>
                      )}
                      {Object.values(patients).map((patient: any) => (
                        <div key={patient.id} className="flex items-center justify-between p-4 bg-zinc-50 border border-zinc-200 rounded-xl">
                          <div>
                            <h4 className="font-bold text-zinc-900">{patient.name} <span className="text-xs font-mono text-zinc-500 ml-2">({patient.id})</span></h4>
                            <p className="text-sm text-zinc-600">{patient.room} • {patient.diagnosis}</p>
                          </div>
                          <button 
                            onClick={() => {
                              setConfirmConfig({
                                isOpen: true,
                                title: "Bemorni chiqarish",
                                message: "Rostdan ham bu bemorni chiqarib yubormoqchimisiz?",
                                onConfirm: () => {
                                  dischargePatient(patient.id);
                                  closeDialogs();
                                }
                              });
                            }}
                            className="px-3 py-1.5 bg-red-50 text-red-600 rounded-lg hover:bg-red-100 transition-colors text-sm border border-red-200"
                          >
                            Chiqarish
                          </button>
                        </div>
                      ))}
                    </div>
                  </div>
                )}

                {/* Integration Tab */}
                {activeTab === 'integration' && (
                  <div className="space-y-6 text-zinc-700">
                    <h3 className="text-lg font-medium text-zinc-900">Qurilmalarni Tizimga Ulash (Integratsiya)</h3>
                    
                    <div className="p-4 bg-blue-50 border border-blue-200 rounded-xl">
                      <h4 className="font-bold text-blue-600 mb-2">Qurilmalar qanday ishlaydi?</h4>
                      <p className="text-sm leading-relaxed text-zinc-700">
                        Bemor monitorlari (Mindray, Philips, Nihon Kohden va boshqalar) kasalxonaning lokal tarmog'iga (LAN/Wi-Fi) ulanadi. 
                        Har bir qurilma o'zining statik <strong>IP manziliga</strong> ega bo'lishi kerak. 
                        Tizim ma'lumotlarni qabul qilishi uchun monitorlar HL7 (Health Level Seven) protokoli yoki to'g'ridan-to'g'ri TCP/IP soketlar orqali ma'lumot jo'natishga sozlanadi.
                      </p>
                    </div>

                    <div className="space-y-4">
                      <h4 className="font-bold text-zinc-900">1-qadam: Tarmoqqa ulash</h4>
                      <p className="text-sm text-zinc-600">Monitorni tarmoqqa ulang va unga statik IP manzil bering (Masalan: <code className="bg-zinc-100 px-1 py-0.5 rounded text-zinc-800">192.168.1.105</code>). Bu IP manzilni "Qurilmalar" bo'limidan tizimga kiriting.</p>

                      <h4 className="font-bold text-zinc-900">Mindray HL7 (tavsiya etiladi)</h4>
                      <p className="text-sm text-zinc-600">
                        Monitor menyusida «Интернет» bo'limida <strong>HL7 protocol</strong> yoqilgan bo'lsin. Server sifatida shu tizimning ochiq TCP manzilini kiriting:
                      </p>
                      <div className="bg-emerald-50 p-4 rounded-lg border border-emerald-200 font-mono text-sm text-emerald-900">
                        {hl7ServerDisplay()}
                      </div>
                      <p className="text-sm text-zinc-600">
                        Standart port <code className="bg-zinc-100 px-1 rounded">6006</code> (MLLP). Bulut serverda <code className="bg-zinc-100 px-1 rounded">6006/tcp</code> ochiq bo‘lishi kerak (nginx emas — to‘g‘ridan-to‘g‘ri VPSga). Repoda <code className="bg-zinc-100 px-1 rounded">deploy/open-hl7-port.sh</code> yordamida ufw tekshiriladi.
                      </p>
                      <div className="p-3 bg-blue-50 border border-blue-200 rounded-lg text-sm text-zinc-800">
                        <strong>NAT:</strong> monitor lokal (192.168…) qoladi; server HL7 ulanishda ko‘radigan manzil — klinikaning <strong>tashqi IP</strong>si. «Qurilma» formasida <strong>NAT tashqi IP</strong> maydonini shu manzil bilan to‘ldiring yoki har bir monitor uchun <strong>HL7 MSH-3</strong>ni Mindray xabari bilan bir xil qiling (bir tashqi IPdan bir nechta monitor).
                      </div>
                      <p className="text-sm text-zinc-600">
                        <code className="bg-zinc-100 px-1 rounded">GET /api/health</code> javobida <code className="bg-zinc-100 px-1 rounded">hl7.listenPort</code> va <code className="bg-zinc-100 px-1 rounded">deviceOfflineAfterSec</code> ko‘rinadi (diagnostika).
                      </p>

                      <h4 className="font-bold text-zinc-900 mt-6">REST API (alternativa)</h4>
                      <p className="text-sm text-zinc-600">LANdagi gateway HTTPS orqali yuborsa — IP emas, qurilma ID bilan:</p>
                      
                      <div className="bg-zinc-50 p-4 rounded-lg border border-zinc-200 font-mono text-sm space-y-3">
                        <div>
                          <div className="text-emerald-600 font-bold">POST /api/devices/[QURILMA_ID]/vitals</div>
                          <div className="text-zinc-500 text-xs mt-1">Masalan dev1775… — sozlamalar jadvalidagi ID</div>
                        </div>
                        <div>
                          <div className="text-emerald-600 font-bold">POST /api/device/[LOKAL_IP]/vitals</div>
                          <div className="text-zinc-500 text-xs mt-1">Ro‘yxatdagi lokal IP bilan mos kelishi kerak</div>
                        </div>
                        <div className="text-zinc-500">Content-Type: application/json</div>
                        <div className="text-zinc-700">
                          {`{
  "hr": 75,
  "spo2": 98,
  "nibpSys": 120,
  "nibpDia": 80,
  "rr": 16,
  "temp": 36.6
}`}
                        </div>
                      </div>

                      <h4 className="font-bold text-zinc-900">3-qadam: Bemorga biriktirish</h4>
                      <p className="text-sm text-zinc-600">
                        Qurilma tizimga qo'shilgandan so'ng, uni ma'lum bir "Joy"ga (Bed) biriktirasiz. 
                        Bemor shu joyga yotqizilganda, tizim avtomatik ravishda qurilmadan kelayotgan ma'lumotlarni bemor profiliga bog'laydi.
                      </p>
                    </div>
                  </div>
                )}
              </>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
