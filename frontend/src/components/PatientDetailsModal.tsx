import React, { useState, useMemo, useEffect, ErrorInfo, ReactNode } from 'react';
import { useStore, AlarmLimits } from '../store';
import { apiUrl } from '../lib/api';
import { openClinicSettings } from '../lib/openSettings';
import { fetchPatientById, mergePatientsIntoStore } from '../lib/patientSync';
import { X, Download, Activity, Heart, Battery, UserCircle, Calendar, Stethoscope, UserMinus, Settings2, LineChart as ChartIcon, Save, AlertTriangle } from 'lucide-react';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Area, Legend } from 'recharts';
import { format, formatDistanceToNow } from 'date-fns';
import { uz } from 'date-fns/locale';

function msAgoLabel(ms: number | null | undefined): string {
  if (ms == null || ms <= 0) return '—';
  try {
    return formatDistanceToNow(ms, { addSuffix: true, locale: uz });
  } catch {
    return '—';
  }
}
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

  const deviceOnlineModal =
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
      (deviceOnlineModal && hasDbVitalsModal));

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


  /** Socket o‘tkazib yuborsa ham DB dagi holatni REST bilan yangilash. */
  useEffect(() => {
    let cancelled = false;
    const sync = async () => {
      const snap = await fetchPatientById(patientId);
      if (cancelled || !snap) return;
      mergePatientsIntoStore([snap]);
    };
    sync();
    const ms = hasLiveVitals ? 40_000 : 12_000;
    const t = window.setInterval(sync, ms);
    return () => {
      cancelled = true;
      window.clearInterval(t);
    };
  }, [patientId, hasLiveVitals]);

  const chartData = useMemo(() => {
    if (!patient) return [];
    const v = patient.vitals || { hr: 0, spo2: 0, nibpSys: 0, nibpDia: 0, rr: 0, temp: 0, nibpTime: 0 };
    const sorted = [...(patient.history || [])].sort(
      (a, b) => (a.timestamp ?? 0) - (b.timestamp ?? 0)
    );
    const fromHist = sorted.map(h => ({
      time: h.timestamp ? format(new Date(h.timestamp), 'HH:mm:ss') : '',
      ts: h.timestamp ?? 0,
      hr: Math.round(h.hr),
      spo2: Math.round(h.spo2),
    }));
    if (fromHist.length > 0) return fromHist;
    if (hasLiveVitals && (v.hr > 0 || v.spo2 > 0)) {
      return [{
        time: format(new Date(), 'HH:mm:ss'),
        ts: Date.now(),
        hr: Math.round(v.hr),
        spo2: Math.round(v.spo2),
      }];
    }
    return [];
  }, [patient, patient?.history, hasLiveVitals]);

  const hrDomain = useMemo((): [number, number] => {
    if (chartData.length === 0) return [50, 120];
    const hrs = chartData.map(d => d.hr);
    const lo = Math.min(...hrs);
    const hi = Math.max(...hrs);
    const pad = Math.max(3, Math.round((hi - lo) * 0.15));
    return [Math.max(40, lo - pad), Math.min(160, hi + pad)];
  }, [chartData]);

  const spo2Domain = useMemo((): [number, number] => {
    if (chartData.length === 0) return [92, 100];
    const vals = chartData.map(d => d.spo2);
    const lo = Math.min(...vals);
    const hi = Math.max(...vals);
    const pad = Math.max(1, Math.ceil((hi - lo) * 0.2) || 1);
    return [Math.max(88, lo - pad), Math.min(100, hi + pad)];
  }, [chartData]);

  if (!patient) return null;

  const maskedName = privacyMode ? (patient.name || '').replace(/([A-Z]\.\s[A-Z]).*/, '$1***') : (patient.name || 'Noma\'lum');
  const vitals = patient.vitals || { hr: 0, spo2: 0, nibpSys: 0, nibpDia: 0, rr: 0, temp: 0, nibpTime: 0 };
  const alarm = patient.alarm || { level: 'none' };

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
              <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
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

              {/* Device connection status */}
              {patient.linkedDeviceId && (
                <DeviceStatusBadge
                  hasLiveVitals={hasLiveVitals}
                  lastRealVitalsMs={patient.lastRealVitalsMs}
                  linkedDeviceLastSeenMs={patient.linkedDeviceLastSeenMs}
                />
              )}

              {/* Charts */}
              <div className="bg-zinc-50 p-5 rounded-xl border border-zinc-200">
                <h3 className="text-lg font-semibold text-zinc-900 mb-4 flex items-center">
                  <Heart className="w-5 h-5 mr-2 text-emerald-600" />
                  Tarixiy Trendlar (oxirgi ~5 daqiqa)
                </h3>
                <div className="h-72 w-full">
                  {chartData.length > 0 ? (
                    <ResponsiveContainer width="100%" height="100%">
                      <LineChart data={chartData} margin={{ top: 8, right: 28, bottom: 8, left: 4 }}>
                        <defs>
                          <linearGradient id="hrAreaGradient" x1="0" y1="0" x2="0" y2="1">
                            <stop offset="0%" stopColor="#059669" stopOpacity={0.2} />
                            <stop offset="100%" stopColor="#059669" stopOpacity={0} />
                          </linearGradient>
                        </defs>
                        <CartesianGrid strokeDasharray="3 3" stroke="#e4e4e7" vertical={false} />
                        <XAxis dataKey="time" stroke="#71717a" fontSize={11} tickMargin={8} minTickGap={28} />
                        <YAxis
                          yAxisId="left"
                          stroke="#059669"
                          fontSize={11}
                          domain={hrDomain}
                          tickCount={5}
                          width={44}
                        />
                        <YAxis
                          yAxisId="right"
                          orientation="right"
                          stroke="#0891b2"
                          fontSize={11}
                          domain={spo2Domain}
                          tickCount={5}
                          width={40}
                        />
                        <Tooltip
                          contentStyle={{
                            backgroundColor: '#fafafa',
                            borderColor: '#d4d4d8',
                            borderRadius: '10px',
                            boxShadow: '0 10px 40px -12px rgb(0 0 0 / 0.18)',
                          }}
                          itemStyle={{ fontWeight: 600 }}
                          labelStyle={{ color: '#52525b', fontSize: 12 }}
                        />
                        <Legend
                          wrapperStyle={{ paddingTop: 12 }}
                          formatter={(value) => (
                            <span className="text-zinc-700 text-xs font-medium">{value}</span>
                          )}
                        />
                        <Area
                          yAxisId="left"
                          type="monotone"
                          dataKey="hr"
                          name="YUCh (min⁻¹)"
                          stroke="none"
                          fill="url(#hrAreaGradient)"
                          legendType="none"
                          isAnimationActive={false}
                        />
                        <Line
                          yAxisId="left"
                          type="monotone"
                          dataKey="hr"
                          name="YUCh (min⁻¹)"
                          stroke="#059669"
                          strokeWidth={2.25}
                          dot={false}
                          activeDot={{ r: 5, strokeWidth: 2, stroke: '#fff' }}
                          isAnimationActive={false}
                        />
                        <Line
                          yAxisId="right"
                          type="monotone"
                          dataKey="spo2"
                          name="SpO2 (%)"
                          stroke="#0e7490"
                          strokeWidth={2.25}
                          dot={false}
                          activeDot={{ r: 5, strokeWidth: 2, stroke: '#fff' }}
                          isAnimationActive={false}
                        />
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
