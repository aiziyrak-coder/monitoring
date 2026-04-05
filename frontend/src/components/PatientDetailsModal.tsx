import React, { useState, useMemo, ErrorInfo, ReactNode } from 'react';
import { useStore, AlarmLimits } from '../store';
import { X, Download, Activity, Heart, Battery, UserCircle, Calendar, Stethoscope, UserMinus, Settings2, LineChart as ChartIcon, Save, AlertTriangle } from 'lucide-react';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts';
import { format } from 'date-fns';

function CustomConfirm({ isOpen, title, message, onConfirm, onCancel }: { isOpen: boolean, title: string, message: string, onConfirm: () => void, onCancel: () => void }) {
  if (!isOpen) return null;
  return (
    <div className="fixed inset-0 z-[110] flex items-center justify-center bg-zinc-900/40 backdrop-blur-sm p-4">
      <div className="bg-white border border-zinc-200 rounded-xl w-full max-w-sm p-6 shadow-2xl">
        <div className="flex items-center space-x-3 mb-4 text-red-600">
          <AlertTriangle className="w-6 h-6" />
          <h3 className="text-lg font-bold">{title}</h3>
        </div>
        <p className="text-zinc-600 mb-6">{message}</p>
        <div className="flex justify-end space-x-3">
          <button onClick={onCancel} className="px-4 py-2 text-zinc-600 hover:text-zinc-900 transition-colors">Yo'q</button>
          <button onClick={onConfirm} className="px-4 py-2 bg-red-500 text-white rounded-lg hover:bg-red-600 transition-colors">Ha, chiqarish</button>
        </div>
      </div>
    </div>
  );
}

class ErrorBoundary extends React.Component<{ children: ReactNode }, { hasError: boolean, error: Error | null }> {
  state: { hasError: boolean, error: Error | null } = { hasError: false, error: null };
  declare props: { children: ReactNode };

  constructor(props: { children: ReactNode }) {
    super(props);
  }

  static getDerivedStateFromError(error: Error) {
    return { hasError: true, error };
  }

  componentDidCatch(error: Error, errorInfo: ErrorInfo) {
    console.error("PatientDetailsModal Error:", error, errorInfo);
  }

  render() {
    if (this.state.hasError) {
      return (
        <div className="fixed inset-0 z-[100] flex items-center justify-center bg-zinc-900/40 backdrop-blur-sm p-4">
          <div className="bg-white border border-red-500 rounded-xl w-full max-w-lg p-6 shadow-2xl">
            <h2 className="text-red-600 text-xl font-bold mb-4">Xatolik yuz berdi</h2>
            <p className="text-zinc-600 mb-4">Bemor ma'lumotlarini yuklashda xatolik yuz berdi.</p>
            <pre className="bg-zinc-100 p-4 rounded text-red-600 text-xs overflow-auto max-h-40">
              {this.state.error?.toString()}
            </pre>
            <div className="mt-6 flex justify-end">
              <button 
                onClick={() => window.location.reload()} 
                className="px-4 py-2 bg-zinc-100 text-zinc-900 rounded hover:bg-zinc-200"
              >
                Sahifani yangilash
              </button>
            </div>
          </div>
        </div>
      );
    }

    return this.props.children;
  }
}

export function PatientDetailsModal() {
  const selectedPatientId = useStore(state => state.selectedPatientId);
  const patients = useStore(state => state.patients);
  const patient = selectedPatientId ? patients[selectedPatientId] : null;

  if (!selectedPatientId || !patient) return null;

  return (
    <ErrorBoundary>
      <PatientDetailsModalContent patientId={selectedPatientId} />
    </ErrorBoundary>
  );
}

function PatientDetailsModalContent({ patientId }: { patientId: string }) {
  const setSelectedPatientId = useStore(state => state.setSelectedPatientId);
  const dischargePatient = useStore(state => state.dischargePatient);
  const updateLimits = useStore(state => state.updateLimits);
  const patients = useStore(state => state.patients);
  const privacyMode = useStore(state => state.privacyMode);

  const [activeTab, setActiveTab] = useState<'overview' | 'limits'>('overview');
  const [localLimits, setLocalLimits] = useState<AlarmLimits | null>(null);
  const [confirmOpen, setConfirmOpen] = useState(false);

  const patient = patients[patientId];

  React.useEffect(() => {
    setLocalLimits(null);
  }, [patientId]);

  React.useEffect(() => {
    if (patient && activeTab === 'limits' && !localLimits && patient.alarmLimits) {
      try {
        setLocalLimits(JSON.parse(JSON.stringify(patient.alarmLimits)));
      } catch (e) {
        console.error("Failed to parse alarmLimits", e);
      }
    }
  }, [activeTab, patient, localLimits]);

  const chartData = useMemo(() => {
    if (!patient) return [];
    return (patient.history || []).map(h => ({
      time: h.timestamp ? format(new Date(h.timestamp), 'HH:mm:ss') : '',
      hr: Math.round(h.hr),
      spo2: Math.round(h.spo2)
    }));
  }, [patient?.history]);

  if (!patient) return null;

  const maskedName = privacyMode ? (patient.name || '').replace(/([A-Z]\.\s[A-Z]).*/, '$1***') : (patient.name || 'Noma\'lum');
  const vitals = patient.vitals || { hr: 0, spo2: 0, nibpSys: 0, nibpDia: 0, rr: 0, temp: 0, nibpTime: 0 };
  const alarm = patient.alarm || { level: 'none' };
  const hasLiveVitals =
    patient.lastRealVitalsMs != null && patient.lastRealVitalsMs > 0;

  const handleExport = () => {
    const csvContent = "data:text/csv;charset=utf-8," 
      + "Vaqt,YUCh,SpO2,AQB Sys,AQB Dia,Nafas,Harorat\n"
      + (patient.history || []).map(h => `${new Date(h.timestamp).toISOString()},${h.hr.toFixed(0)},${h.spo2.toFixed(0)},${h.nibpSys.toFixed(0)},${h.nibpDia.toFixed(0)},${(h.rr || 0).toFixed(0)},${(h.temp || 0).toFixed(1)}`).join("\n");
    
    const encodedUri = encodeURI(csvContent);
    const link = document.createElement("a");
    link.setAttribute("href", encodedUri);
    link.setAttribute("download", `bemor_${patient.id}_tarix.csv`);
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  };

  const handleDischarge = () => {
    setConfirmOpen(true);
  };

  const confirmDischarge = () => {
    dischargePatient(patient.id);
    setSelectedPatientId(null);
    setConfirmOpen(false);
  };

  const handleSaveLimits = () => {
    if (localLimits) {
      updateLimits(patient.id, localLimits);
      setActiveTab('overview');
    }
  };

  const handleLimitChange = (param: keyof AlarmLimits, bound: 'low' | 'high', value: string) => {
    if (!localLimits) return;
    const num = param === 'temp' ? parseFloat(value) : parseInt(value, 10);
    if (Number.isNaN(num)) return;

    setLocalLimits({
      ...localLimits,
      [param]: {
        ...localLimits[param],
        [bound]: num
      }
    });
  };

  return (
    <div className="fixed inset-0 z-[100] flex items-center justify-center bg-zinc-900/40 backdrop-blur-sm p-4">
      <CustomConfirm 
        isOpen={confirmOpen}
        title="Bemorni chiqarish"
        message="Haqiqatan ham ushbu bemorni kasalxonadan chiqarib yubormoqchimisiz?"
        onConfirm={confirmDischarge}
        onCancel={() => setConfirmOpen(false)}
      />
      <div className="bg-white border border-zinc-200 rounded-2xl w-full max-w-4xl max-h-[90vh] overflow-y-auto shadow-2xl">
        
        {/* Header */}
        <div className="flex items-center justify-between p-6 border-b border-zinc-200 sticky top-0 bg-white/90 backdrop-blur z-10">
          <div className="flex items-center space-x-4">
            <div className="w-12 h-12 rounded-full bg-emerald-100 flex items-center justify-center text-emerald-600">
              <UserCircle className="w-8 h-8" />
            </div>
            <div>
              <h2 className="text-2xl font-bold text-zinc-900">{maskedName}</h2>
              <div className="flex items-center space-x-3 text-sm text-zinc-600 mt-1">
                <span className="flex items-center"><Activity className="w-4 h-4 mr-1" /> ID: {patient.id}</span>
                <span className="flex items-center"><Calendar className="w-4 h-4 mr-1" /> Qabul: {patient.admissionDate ? format(new Date(patient.admissionDate), 'dd.MM.yyyy HH:mm') : 'Noma\'lum'}</span>
              </div>
              {alarm.level !== 'none' && (
                <div className={`mt-2 inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${
                  alarm.level === 'red' ? 'bg-red-100 text-red-600 border border-red-200' :
                  alarm.level === 'yellow' ? 'bg-yellow-100 text-yellow-600 border border-yellow-200' :
                  alarm.level === 'purple' ? 'bg-purple-100 text-purple-600 border border-purple-200' :
                  'bg-blue-100 text-blue-600 border border-blue-200'
                }`}>
                  <span className={`w-2 h-2 rounded-full mr-2 animate-pulse ${
                    alarm.level === 'red' ? 'bg-red-500' :
                    alarm.level === 'yellow' ? 'bg-yellow-500' :
                    alarm.level === 'purple' ? 'bg-purple-500' :
                    'bg-blue-500'
                  }`} />
                  {alarm.message || 'DIQQAT'} {alarm.patientId ? `(ID: ${alarm.patientId})` : ''}
                </div>
              )}
            </div>
          </div>
          <div className="flex items-center space-x-3">
            <button onClick={handleDischarge} className="flex items-center px-4 py-2 bg-red-50 hover:bg-red-100 text-red-600 rounded-lg transition-colors text-sm font-medium border border-red-200">
              <UserMinus className="w-4 h-4 mr-2" />
              Javob berish
            </button>
            <button onClick={handleExport} className="flex items-center px-4 py-2 bg-zinc-100 hover:bg-zinc-200 text-zinc-800 rounded-lg transition-colors text-sm font-medium">
              <Download className="w-4 h-4 mr-2" />
              Eksport (CSV)
            </button>
            <button onClick={() => setSelectedPatientId(null)} className="p-2 text-zinc-600 hover:text-zinc-900 bg-zinc-100 hover:bg-red-100 hover:text-red-600 rounded-lg transition-colors">
              <X className="w-5 h-5" />
            </button>
          </div>
        </div>

        {/* Content */}
        <div className="flex border-b border-zinc-200 overflow-x-auto">
          <button 
            onClick={() => setActiveTab('overview')}
            className={`px-6 py-3 text-sm font-medium flex items-center whitespace-nowrap transition-colors ${activeTab === 'overview' ? 'text-emerald-600 border-b-2 border-emerald-500 bg-emerald-50' : 'text-zinc-600 hover:text-zinc-900 hover:bg-zinc-50'}`}
          >
            <ChartIcon className="w-4 h-4 mr-2" />
            Umumiy & Trendlar
          </button>
          <button 
            onClick={() => setActiveTab('limits')}
            className={`px-6 py-3 text-sm font-medium flex items-center whitespace-nowrap transition-colors ${activeTab === 'limits' ? 'text-emerald-600 border-b-2 border-emerald-500 bg-emerald-50' : 'text-zinc-600 hover:text-zinc-900 hover:bg-zinc-50'}`}
          >
            <Settings2 className="w-4 h-4 mr-2" />
            Signal Chegaralari
          </button>
        </div>

        <div className="p-6 space-y-6">
          
          {activeTab === 'overview' ? (
            <>
              {/* Info Cards */}
              <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
                <div className="bg-zinc-50 p-4 rounded-xl border border-zinc-200">
                  <div className="flex items-center text-zinc-600 mb-2">
                    <Stethoscope className="w-4 h-4 mr-2" />
                    <span className="text-xs font-semibold uppercase tracking-wider">Tashxis</span>
                  </div>
                  <p className="text-zinc-900 font-medium">{patient.diagnosis}</p>
                </div>
                <div className="bg-zinc-50 p-4 rounded-xl border border-zinc-200">
                  <div className="flex items-center text-zinc-600 mb-2">
                    <UserCircle className="w-4 h-4 mr-2" />
                    <span className="text-xs font-semibold uppercase tracking-wider">Shifokor / Hamshira</span>
                  </div>
                  <p className="text-zinc-900 font-medium">{patient.doctor} <br/><span className="text-sm text-zinc-600">{patient.assignedNurse}</span></p>
                </div>
                <div className="bg-zinc-50 p-4 rounded-xl border border-zinc-200">
                  <div className="flex items-center text-zinc-600 mb-2">
                    <Activity className="w-4 h-4 mr-2" />
                    <span className="text-xs font-semibold uppercase tracking-wider">NEWS2 Bali</span>
                  </div>
                  <p className={`text-2xl font-bold ${
                    !hasLiveVitals ? 'text-zinc-400' :
                    (patient.news2Score || 0) >= 7 ? 'text-red-600' :
                    (patient.news2Score || 0) >= 5 ? 'text-orange-500' :
                    (patient.news2Score || 0) >= 1 ? 'text-yellow-600' :
                    'text-emerald-600'
                  }`}>{hasLiveVitals ? patient.news2Score || 0 : '—'}</p>
                </div>
                <div className="bg-zinc-50 p-4 rounded-xl border border-zinc-200">
                  <div className="flex items-center text-zinc-500 mb-2">
                    <Battery className="w-4 h-4 mr-2" />
                    <span className="text-xs font-semibold uppercase tracking-wider">Qurilma Quvvati</span>
                  </div>
                  <div className="flex items-center">
                    <div className="w-full bg-zinc-200 rounded-full h-2.5 mr-3">
                      <div className={`h-2.5 rounded-full ${(patient.deviceBattery || 0) > 20 ? 'bg-emerald-500' : 'bg-red-500'}`} style={{ width: `${patient.deviceBattery || 0}%` }}></div>
                    </div>
                    <span className="text-zinc-900 font-mono text-sm">{Math.round(patient.deviceBattery || 0)}%</span>
                  </div>
                </div>
              </div>

              {!hasLiveVitals && (
                <div className="p-3 rounded-xl border border-amber-200 bg-amber-50 text-sm text-amber-950">
                  <strong>Jonli vitallar hali yozilmagan.</strong> Qurilma onlayn bo‘lishi mumkin, lekin
                  bemor kartasiga raqamlar faqat HL7 xabarida <strong>OBX</strong> (masalan, YUCh, SpO2)
                  kelganda tushadi. Mindrayda HL7 <strong>ORU / vitallar yuborish</strong> yoqilganini va
                  monitor tizim vaqtini tekshiring; NAT / HL7 ID mos kelishi ulanish uchun yetarli.
                </div>
              )}

              {/* Charts */}
              <div className="bg-zinc-50 p-5 rounded-xl border border-zinc-200">
                <h3 className="text-lg font-semibold text-zinc-900 mb-4 flex items-center">
                  <Heart className="w-5 h-5 mr-2 text-emerald-600" />
                  Tarixiy Trendlar (Oxirgi 5 daqiqa)
                </h3>
                <div className="h-64 w-full">
                  {chartData.length > 0 ? (
                    <ResponsiveContainer width="100%" height="100%">
                      <LineChart data={chartData} margin={{ top: 5, right: 20, bottom: 5, left: 0 }}>
                        <CartesianGrid strokeDasharray="3 3" stroke="#e4e4e7" vertical={false} />
                        <XAxis dataKey="time" stroke="#71717a" fontSize={12} tickMargin={10} />
                        <YAxis yAxisId="left" stroke="#059669" fontSize={12} domain={['auto', 'auto']} />
                        <YAxis yAxisId="right" orientation="right" stroke="#0891b2" fontSize={12} domain={[80, 100]} />
                        <Tooltip 
                          contentStyle={{ backgroundColor: '#ffffff', borderColor: '#e4e4e7', borderRadius: '8px' }}
                          itemStyle={{ fontWeight: 500 }}
                        />
                        <Line yAxisId="left" type="monotone" dataKey="hr" name="YUCh" stroke="#059669" strokeWidth={2} dot={false} activeDot={{ r: 6 }} />
                        <Line yAxisId="right" type="monotone" dataKey="spo2" name="SpO2" stroke="#0891b2" strokeWidth={2} dot={false} activeDot={{ r: 6 }} />
                      </LineChart>
                    </ResponsiveContainer>
                  ) : (
                    <div className="w-full h-full flex items-center justify-center text-zinc-500">
                      Ma'lumot yo'q
                    </div>
                  )}
                </div>
              </div>
            </>
          ) : activeTab === 'limits' ? (
            <div className="bg-zinc-50 p-6 rounded-xl border border-zinc-200">
              <h3 className="text-lg font-semibold text-zinc-900 mb-6 flex items-center">
                <Settings2 className="w-5 h-5 mr-2 text-emerald-600" />
                Signal Chegaralarini Sozlash
              </h3>
              
              {localLimits && (
                <div className="space-y-6">
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                    
                    {/* HR Limits */}
                    <div className="bg-white p-4 rounded-lg border border-zinc-200">
                      <div className="flex items-center text-emerald-600 mb-4">
                        <Heart className="w-4 h-4 mr-2" />
                        <span className="font-medium">Yurak Urib Turishi (YUCh)</span>
                      </div>
                      <div className="flex items-center space-x-4">
                        <div className="flex-1">
                          <label className="block text-xs text-zinc-500 mb-1">Pastki chegara</label>
                          <input type="number" value={localLimits.hr.low} onChange={(e) => handleLimitChange('hr', 'low', e.target.value)} className="w-full bg-zinc-50 border border-zinc-200 rounded px-3 py-2 text-zinc-900 focus:outline-none focus:border-emerald-500" />
                        </div>
                        <div className="flex-1">
                          <label className="block text-xs text-zinc-500 mb-1">Yuqori chegara</label>
                          <input type="number" value={localLimits.hr.high} onChange={(e) => handleLimitChange('hr', 'high', e.target.value)} className="w-full bg-zinc-50 border border-zinc-200 rounded px-3 py-2 text-zinc-900 focus:outline-none focus:border-emerald-500" />
                        </div>
                      </div>
                    </div>

                    {/* SpO2 Limits */}
                    <div className="bg-white p-4 rounded-lg border border-zinc-200">
                      <div className="flex items-center text-cyan-600 mb-4">
                        <Activity className="w-4 h-4 mr-2" />
                        <span className="font-medium">Saturatsiya (SpO2)</span>
                      </div>
                      <div className="flex items-center space-x-4">
                        <div className="flex-1">
                          <label className="block text-xs text-zinc-500 mb-1">Pastki chegara</label>
                          <input type="number" value={localLimits.spo2.low} onChange={(e) => handleLimitChange('spo2', 'low', e.target.value)} className="w-full bg-zinc-50 border border-zinc-200 rounded px-3 py-2 text-zinc-900 focus:outline-none focus:border-cyan-500" />
                        </div>
                        <div className="flex-1">
                          <label className="block text-xs text-zinc-500 mb-1">Yuqori chegara</label>
                          <input type="number" value={localLimits.spo2.high} onChange={(e) => handleLimitChange('spo2', 'high', e.target.value)} className="w-full bg-zinc-50 border border-zinc-200 rounded px-3 py-2 text-zinc-900 focus:outline-none focus:border-cyan-500" />
                        </div>
                      </div>
                    </div>

                    {/* NIBP Sys Limits */}
                    <div className="bg-white p-4 rounded-lg border border-zinc-200">
                      <div className="flex items-center text-zinc-600 mb-4">
                        <Activity className="w-4 h-4 mr-2" />
                        <span className="font-medium">Sistolik Qon Bosimi</span>
                      </div>
                      <div className="flex items-center space-x-4">
                        <div className="flex-1">
                          <label className="block text-xs text-zinc-500 mb-1">Pastki chegara</label>
                          <input type="number" value={localLimits.nibpSys.low} onChange={(e) => handleLimitChange('nibpSys', 'low', e.target.value)} className="w-full bg-zinc-50 border border-zinc-200 rounded px-3 py-2 text-zinc-900 focus:outline-none focus:border-zinc-500" />
                        </div>
                        <div className="flex-1">
                          <label className="block text-xs text-zinc-500 mb-1">Yuqori chegara</label>
                          <input type="number" value={localLimits.nibpSys.high} onChange={(e) => handleLimitChange('nibpSys', 'high', e.target.value)} className="w-full bg-zinc-50 border border-zinc-200 rounded px-3 py-2 text-zinc-900 focus:outline-none focus:border-zinc-500" />
                        </div>
                      </div>
                    </div>

                    {/* NIBP Dia Limits */}
                    <div className="bg-white p-4 rounded-lg border border-zinc-200">
                      <div className="flex items-center text-zinc-500 mb-4">
                        <Activity className="w-4 h-4 mr-2" />
                        <span className="font-medium">Diastolik Qon Bosimi</span>
                      </div>
                      <div className="flex items-center space-x-4">
                        <div className="flex-1">
                          <label className="block text-xs text-zinc-500 mb-1">Pastki chegara</label>
                          <input type="number" value={localLimits.nibpDia.low} onChange={(e) => handleLimitChange('nibpDia', 'low', e.target.value)} className="w-full bg-zinc-50 border border-zinc-200 rounded px-3 py-2 text-zinc-900 focus:outline-none focus:border-zinc-500" />
                        </div>
                        <div className="flex-1">
                          <label className="block text-xs text-zinc-500 mb-1">Yuqori chegara</label>
                          <input type="number" value={localLimits.nibpDia.high} onChange={(e) => handleLimitChange('nibpDia', 'high', e.target.value)} className="w-full bg-zinc-50 border border-zinc-200 rounded px-3 py-2 text-zinc-900 focus:outline-none focus:border-zinc-500" />
                        </div>
                      </div>
                    </div>

                    {/* RR Limits */}
                    <div className="bg-white p-4 rounded-lg border border-zinc-200">
                      <div className="flex items-center text-yellow-700 mb-4">
                        <Activity className="w-4 h-4 mr-2" />
                        <span className="font-medium">Nafas chastotasi (NCh)</span>
                      </div>
                      <div className="flex items-center space-x-4">
                        <div className="flex-1">
                          <label className="block text-xs text-zinc-500 mb-1">Pastki chegara</label>
                          <input type="number" value={localLimits.rr.low} onChange={(e) => handleLimitChange('rr', 'low', e.target.value)} className="w-full bg-zinc-50 border border-zinc-200 rounded px-3 py-2 text-zinc-900 focus:outline-none focus:border-yellow-500" />
                        </div>
                        <div className="flex-1">
                          <label className="block text-xs text-zinc-500 mb-1">Yuqori chegara</label>
                          <input type="number" value={localLimits.rr.high} onChange={(e) => handleLimitChange('rr', 'high', e.target.value)} className="w-full bg-zinc-50 border border-zinc-200 rounded px-3 py-2 text-zinc-900 focus:outline-none focus:border-yellow-500" />
                        </div>
                      </div>
                    </div>

                    {/* Temp Limits */}
                    <div className="bg-white p-4 rounded-lg border border-zinc-200">
                      <div className="flex items-center text-orange-700 mb-4">
                        <Activity className="w-4 h-4 mr-2" />
                        <span className="font-medium">Harorat (°C)</span>
                      </div>
                      <div className="flex items-center space-x-4">
                        <div className="flex-1">
                          <label className="block text-xs text-zinc-500 mb-1">Pastki chegara</label>
                          <input type="number" step="0.1" value={localLimits.temp.low} onChange={(e) => handleLimitChange('temp', 'low', e.target.value)} className="w-full bg-zinc-50 border border-zinc-200 rounded px-3 py-2 text-zinc-900 focus:outline-none focus:border-orange-500" />
                        </div>
                        <div className="flex-1">
                          <label className="block text-xs text-zinc-500 mb-1">Yuqori chegara</label>
                          <input type="number" step="0.1" value={localLimits.temp.high} onChange={(e) => handleLimitChange('temp', 'high', e.target.value)} className="w-full bg-zinc-50 border border-zinc-200 rounded px-3 py-2 text-zinc-900 focus:outline-none focus:border-orange-500" />
                        </div>
                      </div>
                    </div>

                  </div>

                  <div className="flex justify-end pt-4 border-t border-zinc-200">
                    <button 
                      onClick={handleSaveLimits}
                      className="flex items-center px-6 py-2 bg-emerald-600 hover:bg-emerald-500 text-white rounded-lg transition-colors font-medium"
                    >
                      <Save className="w-4 h-4 mr-2" />
                      Saqlash
                    </button>
                  </div>
                </div>
              )}
            </div>
          ) : null}

        </div>
      </div>
    </div>
  );
}
