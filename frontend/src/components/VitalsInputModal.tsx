/**
 * VitalsInputModal — hamshira/shifokor uchun qo'lda vitals kiritish modali.
 * Kiritilgan qiymatlar REST API orqali backendga yuboriladi.
 */
import React, { useState, useEffect } from 'react';
import { X, Activity, Loader2, CheckCircle2, AlertCircle } from 'lucide-react';

interface VitalsInputModalProps {
  patientId: string;
  patientName: string;
  deviceId: string | null;
  onClose: () => void;
}

interface VitalsForm {
  hr: string;
  spo2: string;
  nibpSys: string;
  nibpDia: string;
  rr: string;
  temp: string;
}

const EMPTY_FORM: VitalsForm = {
  hr: '',
  spo2: '',
  nibpSys: '',
  nibpDia: '',
  rr: '',
  temp: '',
};

const API_BASE = import.meta.env.VITE_API_URL ?? '';

export const VitalsInputModal: React.FC<VitalsInputModalProps> = ({
  patientId,
  patientName,
  deviceId,
  onClose,
}) => {
  const [form, setForm] = useState<VitalsForm>(EMPTY_FORM);
  const [status, setStatus] = useState<'idle' | 'loading' | 'success' | 'error'>('idle');
  const [errorMsg, setErrorMsg] = useState('');

  useEffect(() => {
    const handleKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onClose();
    };
    window.addEventListener('keydown', handleKey);
    return () => window.removeEventListener('keydown', handleKey);
  }, [onClose]);

  const handleChange = (field: keyof VitalsForm) => (e: React.ChangeEvent<HTMLInputElement>) => {
    const val = e.target.value.replace(/[^0-9.]/g, '');
    setForm(prev => ({ ...prev, [field]: val }));
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setStatus('loading');
    setErrorMsg('');

    const payload: Record<string, number> = {};
    const toNum = (v: string) => (v.trim() !== '' ? parseFloat(v) : null);

    const hr = toNum(form.hr);
    const spo2 = toNum(form.spo2);
    const nibpSys = toNum(form.nibpSys);
    const nibpDia = toNum(form.nibpDia);
    const rr = toNum(form.rr);
    const temp = toNum(form.temp);

    if (hr !== null) payload.hr = hr;
    if (spo2 !== null) payload.spo2 = spo2;
    if (nibpSys !== null) payload.nibpSys = nibpSys;
    if (nibpDia !== null) payload.nibpDia = nibpDia;
    if (rr !== null) payload.rr = rr;
    if (temp !== null) payload.temp = temp;

    if (Object.keys(payload).length === 0) {
      setStatus('error');
      setErrorMsg('Kamida bitta qiymat kiriting');
      return;
    }

    // Agar device bog'langan bo'lsa — device endpoint, aks holda patient endpoint
    const url = deviceId
      ? `${API_BASE}/api/devices/${deviceId}/vitals`
      : `${API_BASE}/api/patients/${patientId}/vitals`;

    try {
      const res = await fetch(url, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      });
      if (!res.ok) {
        const text = await res.text();
        throw new Error(`Server xato: ${res.status} — ${text.slice(0, 100)}`);
      }
      setStatus('success');
      setTimeout(() => onClose(), 1500);
    } catch (err) {
      setStatus('error');
      setErrorMsg(err instanceof Error ? err.message : 'Noma\'lum xato');
    }
  };

  const fields: { key: keyof VitalsForm; label: string; unit: string; placeholder: string; color: string }[] = [
    { key: 'hr', label: 'YUCh (Puls)', unit: 'ur/min', placeholder: '60–100', color: 'emerald' },
    { key: 'spo2', label: 'SpO₂', unit: '%', placeholder: '95–100', color: 'cyan' },
    { key: 'nibpSys', label: 'AQB Sistolik', unit: 'mmHg', placeholder: '90–140', color: 'zinc' },
    { key: 'nibpDia', label: 'AQB Diastolik', unit: 'mmHg', placeholder: '60–90', color: 'zinc' },
    { key: 'rr', label: 'Nafas tezligi', unit: '/min', placeholder: '12–20', color: 'orange' },
    { key: 'temp', label: 'Harorat', unit: '°C', placeholder: '36.0–37.5', color: 'red' },
  ];

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm p-4"
      onClick={(e) => { if (e.target === e.currentTarget) onClose(); }}
    >
      <div className="bg-white rounded-2xl shadow-2xl w-full max-w-md overflow-hidden">
        {/* Header */}
        <div className="flex items-center justify-between px-5 py-4 border-b border-zinc-100 bg-gradient-to-r from-emerald-50 to-cyan-50">
          <div className="flex items-center gap-2">
            <Activity className="w-5 h-5 text-emerald-600" />
            <div>
              <h2 className="text-base font-semibold text-zinc-900">Vitals kiritish</h2>
              <p className="text-xs text-zinc-500 truncate max-w-[220px]">{patientName}</p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="p-1.5 rounded-lg hover:bg-zinc-100 text-zinc-500 hover:text-zinc-800 transition-colors"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        {/* Form */}
        <form onSubmit={handleSubmit} className="p-5">
          <div className="grid grid-cols-2 gap-3 mb-4">
            {fields.map(({ key, label, unit, placeholder }) => (
              <div key={key}>
                <label className="block text-xs font-medium text-zinc-600 mb-1">
                  {label}
                  <span className="text-zinc-400 ml-1 font-normal">{unit}</span>
                </label>
                <input
                  type="text"
                  inputMode="decimal"
                  value={form[key]}
                  onChange={handleChange(key)}
                  placeholder={placeholder}
                  className="w-full px-3 py-2 text-sm border border-zinc-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-emerald-400 focus:border-transparent bg-zinc-50 font-mono"
                  disabled={status === 'loading' || status === 'success'}
                />
              </div>
            ))}
          </div>

          {/* Status messages */}
          {status === 'error' && (
            <div className="flex items-center gap-2 text-red-600 text-xs bg-red-50 border border-red-200 rounded-lg px-3 py-2 mb-3">
              <AlertCircle className="w-4 h-4 shrink-0" />
              <span>{errorMsg}</span>
            </div>
          )}
          {status === 'success' && (
            <div className="flex items-center gap-2 text-emerald-700 text-xs bg-emerald-50 border border-emerald-200 rounded-lg px-3 py-2 mb-3">
              <CheckCircle2 className="w-4 h-4 shrink-0" />
              <span>Vitals muvaffaqiyatli saqlandi!</span>
            </div>
          )}

          {/* Buttons */}
          <div className="flex gap-2">
            <button
              type="button"
              onClick={onClose}
              className="flex-1 px-4 py-2.5 text-sm font-medium text-zinc-700 bg-zinc-100 hover:bg-zinc-200 rounded-xl transition-colors"
              disabled={status === 'loading'}
            >
              Bekor qilish
            </button>
            <button
              type="submit"
              className="flex-1 px-4 py-2.5 text-sm font-semibold text-white bg-emerald-600 hover:bg-emerald-700 rounded-xl transition-colors flex items-center justify-center gap-2 disabled:opacity-60"
              disabled={status === 'loading' || status === 'success'}
            >
              {status === 'loading' ? (
                <>
                  <Loader2 className="w-4 h-4 animate-spin" />
                  Saqlanmoqda...
                </>
              ) : status === 'success' ? (
                <>
                  <CheckCircle2 className="w-4 h-4" />
                  Saqlandi!
                </>
              ) : (
                'Saqlash'
              )}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};
