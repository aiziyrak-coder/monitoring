import { Heart, Clock, X, Battery, UserCircle, Droplets, Pin } from 'lucide-react';
import { PatientData, useStore } from '../store';
import { clsx, type ClassValue } from 'clsx';
import { twMerge } from 'tailwind-merge';
import React, { useState, useEffect } from 'react';
import { formatDistanceToNow } from 'date-fns';
import { uz } from 'date-fns/locale';

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

interface PatientMonitorProps {
  key?: React.Key;
  patient: PatientData;
  size?: 'large' | 'medium' | 'small';
}

export const PatientMonitor = React.memo(function PatientMonitor({ patient, size = 'large' }: PatientMonitorProps) {
  const { vitals, alarm, alarmLimits, scheduledCheck, deviceBattery, doctor } = patient;
  const hasLiveVitals =
    patient.lastRealVitalsMs != null && patient.lastRealVitalsMs > 0;
  const privacyMode = useStore(state => state.privacyMode);
  const setSchedule = useStore(state => state.setSchedule);
  const clearAlarm = useStore(state => state.clearAlarm);
  const setSelectedPatientId = useStore(state => state.setSelectedPatientId);
  const togglePinPatient = useStore(state => state.togglePinPatient);
  
  const [showScheduleMenu, setShowScheduleMenu] = useState(false);
  const [timeLeft, setTimeLeft] = useState<number | null>(null);

  const nextCheckTime = scheduledCheck?.nextCheckTime;

  useEffect(() => {
    if (!nextCheckTime) {
      setTimeLeft(null);
      return;
    }
    
    const interval = setInterval(() => {
      const remaining = Math.max(0, Math.ceil((nextCheckTime - Date.now()) / 1000));
      setTimeLeft(remaining);
    }, 1000);
    
    // Initial call
    const remaining = Math.max(0, Math.ceil((nextCheckTime - Date.now()) / 1000));
    setTimeLeft(remaining);
    
    return () => clearInterval(interval);
  }, [nextCheckTime]);

  const alarmStyles = {
    none: 'border-zinc-200 bg-white/80 hover:bg-zinc-50/90 backdrop-blur-md shadow-sm',
    blue: 'border-blue-300 bg-blue-50/80 animate-pulse hover:bg-blue-100/90 backdrop-blur-md shadow-[0_0_10px_rgba(59,130,246,0.1)]',
    yellow: 'border-yellow-300 bg-yellow-50/80 animate-pulse hover:bg-yellow-100/90 backdrop-blur-md shadow-[0_0_10px_rgba(234,179,8,0.1)]',
    red: 'border-red-400 bg-red-50/90 animate-pulse shadow-[0_0_20px_rgba(239,68,68,0.2)] hover:bg-red-100/90 backdrop-blur-md',
    purple: 'border-purple-300 bg-purple-50/80 animate-pulse shadow-[0_0_20px_rgba(168,85,247,0.2)] hover:bg-purple-100/90 backdrop-blur-md',
  };

  const maskedName = privacyMode ? patient.name.replace(/([A-Z]\.\s[A-Z]).*/, '$1***') : patient.name;

  const handleSetSchedule = (e: React.MouseEvent, seconds: number) => {
    e.stopPropagation();
    setSchedule(patient.id, seconds * 1000);
    setShowScheduleMenu(false);
  };

  // Define sizes
  const isSmall = size === 'small';
  const isMedium = size === 'medium';
  const isLarge = size === 'large';

  return (
    <div 
      onClick={() => setSelectedPatientId(patient.id)}
      className={cn(
        "relative flex flex-col rounded-xl border transition-all duration-300 cursor-pointer group",
        alarmStyles[alarm.level],
        isSmall ? "p-1 h-[120px]" : isMedium ? "p-1.5 h-[180px]" : "p-2 h-[240px]"
      )}
    >
      {/* Header */}
      <div className={cn("flex justify-between items-start shrink-0", isSmall ? "mb-0.5" : "mb-1.5")}>
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-1">
            <h3 className={cn(
              "font-semibold text-zinc-900 group-hover:text-emerald-600 transition-colors truncate",
              isSmall ? "text-[10px]" : isMedium ? "text-xs" : "text-sm"
            )}>
              {maskedName}
            </h3>
            {patient.isPinned && (
              <Pin className="w-3 h-3 text-emerald-500 shrink-0 fill-emerald-500" />
            )}
          </div>
          {!isSmall && (
            <div className="flex items-center space-x-1 mt-0.5">
              <p className="text-[8px] text-zinc-700 font-mono bg-zinc-100 px-1 py-0.5 rounded truncate">{patient.room}</p>
              {isLarge && (
                <div className="flex items-center text-[9px] text-zinc-700 min-w-0" title="Mas'ul shifokor / Hamshira">
                  <UserCircle className="w-2.5 h-2.5 mr-1 shrink-0" />
                  <span className="truncate">{doctor} / {patient.assignedNurse}</span>
                </div>
              )}
            </div>
          )}
          {isSmall && <p className="text-[8px] text-zinc-700 truncate">{patient.room}</p>}
        </div>
        
        <div className="flex flex-col items-end space-y-0.5 ml-1 shrink-0 max-w-[50%]">
          {alarm.level !== 'none' && (
            <div className={cn(
              "rounded-full font-bold uppercase tracking-wider flex items-center max-w-full",
              isSmall ? "px-1 text-[7px]" : "px-1.5 py-0.5 text-[8px]",
              alarm.level === 'red' ? 'bg-red-500 text-white' :
              alarm.level === 'yellow' ? 'bg-yellow-500 text-black' :
              alarm.level === 'purple' ? 'bg-purple-500 text-white' :
              'bg-blue-500 text-white'
            )}>
              {!isSmall && (
                <span className="truncate">{alarm.message || 'DIQQAT'}</span>
              )}
              {isSmall && '!'}
              {alarm.level === 'purple' && !isSmall && (
                <button 
                  onClick={(e) => { e.stopPropagation(); clearAlarm(patient.id); }} 
                  className="ml-1 hover:text-zinc-800 shrink-0"
                >
                  <X className="w-2.5 h-2.5" />
                </button>
              )}
            </div>
          )}
          
          {!isSmall && (
            <div className="flex space-x-1 items-center mt-0.5">
              <div className={cn(
                "flex items-center justify-center rounded px-1.5 py-0.5 border text-[9px] font-bold",
                !hasLiveVitals ? "bg-zinc-100 border-zinc-200 text-zinc-500" :
                patient.news2Score >= 7 ? "bg-red-100 border-red-200 text-red-600" :
                patient.news2Score >= 5 ? "bg-orange-100 border-orange-200 text-orange-600" :
                patient.news2Score >= 1 ? "bg-yellow-100 border-yellow-200 text-yellow-700" :
                "bg-emerald-100 border-emerald-200 text-emerald-600"
              )} title={hasLiveVitals ? "NEWS2 Bali" : "Jonli qabul kutilmoqda"}>
                N: {hasLiveVitals ? patient.news2Score : "—"}
              </div>
              <button
                onClick={(e) => { e.stopPropagation(); togglePinPatient(patient.id); }}
                className="opacity-0 group-hover:opacity-100 transition-opacity p-1 hover:bg-zinc-200 rounded text-zinc-600 hover:text-zinc-900"
                title={patient.isPinned ? "Qadashni bekor qilish" : "Qadab qo'yish"}
              >
                <Pin className={cn("w-3 h-3", patient.isPinned && "fill-emerald-500 text-emerald-500 opacity-100")} />
              </button>
              <div className="flex items-center text-zinc-600" title={`Quvvat: ${Math.round(deviceBattery)}%`}>
                <Battery className={cn("w-2.5 h-2.5", deviceBattery < 20 ? "text-red-500 animate-pulse" : "")} />
              </div>
              <div className="relative flex items-center">
                {timeLeft !== null && (
                  <span className="text-[10px] text-purple-600 mr-1 font-mono">
                    {Math.floor(timeLeft / 60)}:{(timeLeft % 60).toString().padStart(2, '0')}
                  </span>
                )}
                <button 
                  onClick={(e) => { e.stopPropagation(); setShowScheduleMenu(!showScheduleMenu); }}
                  className={cn(
                    "text-zinc-600 hover:text-purple-700 transition-colors",
                    scheduledCheck ? "text-purple-600" : ""
                  )} 
                  title="Rejali tekshiruv"
                >
                  <Clock className="w-2.5 h-2.5" />
                </button>
                
                {showScheduleMenu && (
                  <div className="absolute right-0 mt-2 w-32 bg-white border border-zinc-200 rounded-md shadow-lg z-20 overflow-hidden">
                    <div className="px-3 py-2 text-xs font-semibold text-zinc-700 border-b border-zinc-200">Interval</div>
                    <button onClick={(e) => handleSetSchedule(e, 10)} className="w-full text-left px-3 py-2 text-sm text-zinc-700 hover:bg-zinc-50">10 soniya</button>
                    <button onClick={(e) => handleSetSchedule(e, 30)} className="w-full text-left px-3 py-2 text-sm text-zinc-700 hover:bg-zinc-50">30 soniya</button>
                    <button onClick={(e) => handleSetSchedule(e, 60)} className="w-full text-left px-3 py-2 text-sm text-zinc-700 hover:bg-zinc-50">1 daqiqa</button>
                    <button onClick={(e) => handleSetSchedule(e, 0)} className="w-full text-left px-3 py-2 text-sm text-red-500 hover:bg-zinc-50 border-t border-zinc-200">O'chirish</button>
                  </div>
                )}
              </div>
            </div>
          )}
        </div>
      </div>

      {!isSmall && !hasLiveVitals && (
        <p className="text-[9px] text-amber-800 bg-amber-50 border border-amber-200 rounded px-1.5 py-0.5 mt-1 leading-tight">
          Jonli qabul kutilmoqda
        </p>
      )}

      {/* Numerics Grid */}
      <div className={cn(
        "flex-1 grid gap-0.5 min-h-0 mt-1",
        isSmall ? "grid-cols-2" : isMedium ? "grid-cols-2 grid-rows-2" : "grid-cols-3 grid-rows-2"
      )}>
        
        {/* HR */}
        <div className={cn(
          "bg-zinc-50 rounded flex flex-col justify-between border border-emerald-200 overflow-hidden",
          isSmall ? "p-0.5" : "p-1.5",
          isLarge && "col-span-1 row-span-2"
        )}>
          <div className="flex justify-between items-start shrink-0">
            <span className={cn("text-emerald-800 font-bold truncate pr-1", isSmall ? "text-[7px]" : "text-[9px]")}>YUCh</span>
            {!isSmall && (
              <Heart
                className={cn(
                  "w-2.5 h-2.5 text-emerald-700 shrink-0",
                  hasLiveVitals && vitals.hr > 0 ? "animate-pulse" : ""
                )}
              />
            )}
          </div>
          <div className="flex items-baseline justify-end flex-1 min-h-0 items-center">
            <span className={cn(
              "font-bold text-emerald-800 font-mono tracking-tighter truncate leading-none",
              isSmall ? "text-sm" : isMedium ? "text-xl" : "text-3xl"
            )}>
              {!hasLiveVitals || vitals.hr === 0 ? '—' : vitals.hr}
            </span>
          </div>
          {!isSmall && (
            <div className="flex justify-between text-[8px] text-emerald-800/70 font-mono shrink-0">
              <span>{alarmLimits?.hr.low}</span>
              <span>{alarmLimits?.hr.high}</span>
            </div>
          )}
        </div>

        {/* SpO2 */}
        <div className={cn(
          "bg-zinc-50 rounded flex flex-col justify-between border border-cyan-200 overflow-hidden",
          isSmall ? "p-0.5" : "p-1.5",
          isLarge && "col-span-1 row-span-2"
        )}>
          <div className="flex justify-between items-start shrink-0">
            <span className={cn("text-cyan-800 font-bold truncate pr-1", isSmall ? "text-[7px]" : "text-[9px]")}>SpO2%</span>
            {!isSmall && <Droplets className="w-2.5 h-2.5 text-cyan-700 shrink-0" />}
          </div>
          <div className="flex items-baseline justify-end flex-1 min-h-0 items-center">
            <span className={cn(
              "font-bold text-cyan-800 font-mono tracking-tighter truncate leading-none",
              isSmall ? "text-sm" : isMedium ? "text-xl" : "text-3xl"
            )}>
              {!hasLiveVitals || vitals.spo2 === 0 ? '—' : vitals.spo2}
            </span>
          </div>
          {!isSmall && (
            <div className="flex justify-between text-[8px] text-cyan-800/70 font-mono shrink-0">
              <span>{alarmLimits?.spo2.low}</span>
              <span>{alarmLimits?.spo2.high}</span>
            </div>
          )}
        </div>

        {/* NIBP */}
        <div className={cn(
          "bg-zinc-50 rounded flex flex-col justify-between border border-zinc-200 overflow-hidden",
          isSmall ? "p-0.5 col-span-2" : "p-1.5",
          isMedium && "col-span-2",
          isLarge && "col-span-1 row-span-1"
        )}>
          <div className="flex justify-between items-start shrink-0">
            <span className={cn("text-zinc-800 font-bold truncate pr-1", isSmall ? "text-[7px]" : "text-[9px]")}>AQB</span>
          </div>
          <div className="flex flex-col items-end justify-center flex-1 min-h-0 overflow-hidden">
            <div className="flex items-baseline truncate max-w-full">
              <span className={cn(
                "font-bold text-zinc-950 font-mono tracking-tighter truncate leading-none",
                isSmall ? "text-xs" : isMedium ? "text-lg" : "text-xl"
              )}>
                {!hasLiveVitals || vitals.nibpSys === 0 ? '—' : vitals.nibpSys}
              </span>
              <span className="text-zinc-600 mx-0.5 shrink-0 text-xs">/</span>
              <span className={cn(
                "font-bold text-zinc-950 font-mono tracking-tighter truncate leading-none",
                isSmall ? "text-xs" : isMedium ? "text-lg" : "text-xl"
              )}>
                {!hasLiveVitals || vitals.nibpDia === 0 ? '—' : vitals.nibpDia}
              </span>
            </div>
            {!isSmall && (
              <span className="text-[8px] text-zinc-600 mt-0.5 truncate max-w-full shrink-0">
                {!hasLiveVitals
                  ? "O'lchanmagan"
                  : vitals.nibpTime
                    ? formatDistanceToNow(vitals.nibpTime, { addSuffix: true, locale: uz })
                    : "O'lchanmagan"}
              </span>
            )}
          </div>
        </div>

        {/* RR & Temp (Only for Large) */}
        {isLarge && (
          <div className="flex gap-0.5 col-span-1 row-span-1 min-h-0">
            <div className="flex-1 bg-zinc-50 rounded p-1 flex flex-col justify-between border border-yellow-300 overflow-hidden">
              <span className="text-yellow-800 font-bold text-[9px] shrink-0 truncate">NCh</span>
              <div className="flex items-baseline justify-end flex-1 min-h-0 items-center">
                <span className="text-lg font-bold text-yellow-800 font-mono tracking-tighter truncate leading-none">
                  {!hasLiveVitals || vitals.rr === 0 ? '—' : vitals.rr}
                </span>
              </div>
            </div>
            <div className="flex-1 bg-zinc-50 rounded p-1 flex flex-col justify-between border border-orange-300 overflow-hidden">
              <span className="text-orange-800 font-bold text-[9px] shrink-0 truncate">Harorat</span>
              <div className="flex items-baseline justify-end flex-1 min-h-0 items-center">
                <span className="text-lg font-bold text-orange-800 font-mono tracking-tighter truncate leading-none">
                  {!hasLiveVitals || !Number.isFinite(vitals.temp) || vitals.temp === 0
                    ? '—'
                    : vitals.temp.toFixed(1)}
                </span>
              </div>
            </div>
          </div>
        )}

      </div>
    </div>
  );
});
