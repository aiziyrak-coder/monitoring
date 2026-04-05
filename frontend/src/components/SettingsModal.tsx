import { useState, useEffect } from 'react';
import { X, Server, Building2, MonitorSmartphone, Users, Plus, Trash2, Edit2, Info, AlertTriangle, Link2 } from 'lucide-react';
import { apiUrl, hl7ServerDisplay } from '../lib/api';
import { useStore } from '../store';

interface SettingsModalProps {
  onClose: () => void;
}

// Custom Dialogs to replace prompt/confirm in iframe
function CustomPrompt({ isOpen, title, fields, initialValues, onSubmit, onCancel }: { isOpen: boolean, title: string, fields: {name: string, label: string, placeholder?: string}[], initialValues?: Record<string, string>, onSubmit: (data: any) => void, onCancel: () => void }) {
  const [values, setValues] = useState<Record<string, string>>({});
  
  useEffect(() => {
    if (isOpen) setValues(initialValues ? { ...initialValues } : {});
  }, [isOpen, initialValues]);

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-[60] flex items-center justify-center bg-zinc-900/40 backdrop-blur-sm p-4">
      <div className="bg-white border border-zinc-200 rounded-xl w-full max-w-md p-6 shadow-2xl">
        <h3 className="text-lg font-bold text-zinc-900 mb-4">{title}</h3>
        <form onSubmit={(e) => { e.preventDefault(); onSubmit(values); }}>
          <div className="space-y-4 mb-6">
            {fields.map(f => (
              <div key={f.name}>
                <label className="block text-sm text-zinc-600 mb-1">{f.label}</label>
                <input 
                  type="text" 
                  value={values[f.name] || ''}
                  onChange={e => setValues({...values, [f.name]: e.target.value})}
                  placeholder={f.placeholder}
                  className="w-full bg-zinc-50 border border-zinc-200 rounded-lg p-2 text-zinc-900 focus:border-emerald-500 outline-none"
                  autoFocus={fields[0].name === f.name}
                />
              </div>
            ))}
          </div>
          <div className="flex justify-end space-x-3">
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

  // Dialog states
  const [promptConfig, setPromptConfig] = useState<{isOpen: boolean, title: string, fields: any[], initialValues?: Record<string, string>, onSubmit: (data: any) => void} | null>(null);
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

  const closeDialogs = () => {
    setPromptConfig(null);
    setConfirmConfig(null);
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
    setPromptConfig({
      isOpen: true,
      title: "Yangi qurilma qo'shish",
      fields: [
        { name: 'ipAddress', label: "Lokal IP (LAN)", placeholder: "192.168.0.228" },
        { name: 'macAddress', label: "MAC Manzil", placeholder: "00:1A:2B:3C:4D:5E" },
        { name: 'model', label: "Model", placeholder: "Mindray uMEC10" },
        { name: 'hl7SendingApplication', label: "HL7 MSH-3 (ixtiyoriy, bir routerdan bir nechta monitor)", placeholder: "Masalan: uMEC10-1" },
      ],
      onSubmit: async (vals) => {
        if (!vals.ipAddress) return closeDialogs();
        try {
          await fetch(apiUrl('/api/devices'), { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(vals) });
          closeDialogs();
          fetchData();
        } catch (e) {
          console.error(e);
          setError("Xatolik yuz berdi");
        }
      }
    });
  };

  const editDevice = (device: { id: string; ipAddress?: string; macAddress?: string; model?: string; hl7SendingApplication?: string }) => {
    setPromptConfig({
      isOpen: true,
      title: "Qurilmani tahrirlash",
      initialValues: {
        ipAddress: device.ipAddress ?? '',
        macAddress: device.macAddress ?? '',
        model: device.model ?? '',
        hl7SendingApplication: device.hl7SendingApplication ?? '',
      },
      fields: [
        { name: 'ipAddress', label: "Lokal IP (LAN)", placeholder: "192.168.0.228" },
        { name: 'macAddress', label: "MAC Manzil", placeholder: "" },
        { name: 'model', label: "Model", placeholder: "" },
        { name: 'hl7SendingApplication', label: "HL7 MSH-3 (ixtiyoriy)", placeholder: "" },
      ],
      onSubmit: async (vals) => {
        try {
          await fetch(apiUrl(`/api/devices/${device.id}`), {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
              ipAddress: vals.ipAddress,
              macAddress: vals.macAddress,
              model: vals.model,
              hl7SendingApplication: vals.hl7SendingApplication || '',
            }),
          });
          closeDialogs();
          fetchData();
        } catch (e) {
          console.error(e);
          setError("Xatolik yuz berdi");
        }
      },
    });
  };

  const assignBedToDevice = (deviceId: string) => {
    setPromptConfig({
      isOpen: true,
      title: "Qurilmani joyga biriktirish",
      fields: [{ name: 'bedId', label: "Joy ID si", placeholder: "Masalan: b1" }],
      onSubmit: async (vals) => {
        if (!vals.bedId) return closeDialogs();
        try {
          await fetch(apiUrl(`/api/devices/${deviceId}`), { method: 'PUT', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ bedId: vals.bedId }) });
          closeDialogs();
          fetchData();
        } catch (e) {
          console.error(e);
          setError("Xatolik yuz berdi");
        }
      }
    });
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
                    <div className="flex items-center justify-between">
                      <h3 className="text-lg font-medium text-zinc-900">Bemor Monitorlari</h3>
                      <button onClick={addDevice} className="flex items-center px-3 py-1.5 bg-emerald-100 text-emerald-600 rounded-lg hover:bg-emerald-200 transition-colors text-sm">
                        <Plus className="w-4 h-4 mr-1" /> Qurilma qo'shish
                      </button>
                    </div>

                    <div className="overflow-x-auto">
                      <table className="w-full text-sm text-left text-zinc-600">
                        <thead className="text-xs text-zinc-500 uppercase bg-zinc-50 border-b border-zinc-200">
                          <tr>
                            <th className="px-4 py-3">ID / Model</th>
                            <th className="px-4 py-3">Tarmoq (IP / MAC)</th>
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
                              </td>
                              <td className="px-4 py-3 text-xs font-mono text-zinc-600 max-w-[140px] truncate" title={device.hl7SendingApplication || ''}>
                                {device.hl7SendingApplication || '—'}
                              </td>
                              <td className="px-4 py-3">
                                {device.bedId ? (
                                  <span className="px-2 py-1 bg-blue-50 text-blue-600 rounded border border-blue-200">{device.bedId}</span>
                                ) : (
                                  <span className="text-zinc-500 italic">Biriktirilmagan</span>
                                )}
                              </td>
                              <td className="px-4 py-3">
                                <div className="flex items-center">
                                  <div className={`w-2 h-2 rounded-full mr-2 ${device.status === 'online' ? 'bg-emerald-500' : 'bg-red-500'}`}></div>
                                  <span className="text-zinc-700">{device.status === 'online' ? 'Onlayn' : 'Oflayn'}</span>
                                </div>
                              </td>
                              <td className="px-4 py-3 text-right space-x-2">
                                <button onClick={() => editDevice(device)} className="p-1.5 text-zinc-500 hover:text-emerald-600 bg-white border border-zinc-200 rounded-md" title="Tahrirlash"><Edit2 className="w-4 h-4" /></button>
                                <button onClick={() => assignBedToDevice(device.id)} className="p-1.5 text-zinc-500 hover:text-blue-600 bg-white border border-zinc-200 rounded-md" title="Joyga biriktirish"><Link2 className="w-4 h-4" /></button>
                                <button onClick={() => deleteDevice(device.id)} className="p-1.5 text-zinc-500 hover:text-red-600 bg-white border border-zinc-200 rounded-md"><Trash2 className="w-4 h-4" /></button>
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
                    <div className="flex items-center justify-between">
                      <div>
                        <h3 className="text-lg font-medium text-zinc-900">Faol Bemorlar</h3>
                        <p className="text-sm text-zinc-500">Yangi bemor qo'shish uchun asosiy ekrandagi tugmadan foydalaning.</p>
                      </div>
                      <button
                        onClick={() => {
                          useStore.getState().setAllSchedules(60000);
                          closeDialogs();
                        }}
                        className="px-4 py-2 bg-emerald-50 text-emerald-600 rounded-lg hover:bg-emerald-100 transition-colors text-sm border border-emerald-200"
                      >
                        Barchasiga 1 daqiqalik tekshiruv
                      </button>
                    </div>

                    <div className="grid grid-cols-1 gap-4">
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
                        Standart port <code className="bg-zinc-100 px-1 rounded">6006</code> (MLLP). Bulut serverda xavfsizlik guruhida <code className="bg-zinc-100 px-1 rounded">6006/tcp</code> ochiq bo'lishi kerak. Qurilmani tizimga <strong>lokal IP</strong> bilan qo'shing (masalan 192.168.0.228). Bitta router orqali bir nechta monitor bo'lsa, ixtiyoriy <strong>HL7 MSH-3</strong> maydonini to'ldirib, xabardagi yuboruvchi bilan moslang.
                      </p>

                      <h4 className="font-bold text-zinc-900 mt-6">REST API (alternativa)</h4>
                      <p className="text-sm text-zinc-600">Agar qurilma yoki gateway REST orqali yuborsa:</p>
                      
                      <div className="bg-zinc-50 p-4 rounded-lg border border-zinc-200 font-mono text-sm">
                        <div className="text-emerald-600 mb-2 font-bold">POST /api/device/[IP_MANZIL]/vitals</div>
                        <div className="text-zinc-500">Content-Type: application/json</div>
                        <br/>
                        <div className="text-zinc-700">
                          {`{
  "hr": 75,
  "spo2": 98,
  "nibpSys": 120,
  "nibpDia": 80,
  "rr": 16,
  "temp": 36.6,
  "ecg": [0.1, 0.2, 1.5, -0.3, ...] // 250Hz ma'lumot
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
