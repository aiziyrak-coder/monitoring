import { create } from 'zustand';
import { io, Socket } from 'socket.io-client';
import { socketIoUrl } from './lib/api';

export interface VitalSigns {
  hr: number;
  spo2: number;
  nibpSys: number;
  nibpDia: number;
  rr: number;
  temp: number;
  nibpTime?: number;
}

export interface AlarmLimits {
  hr: { low: number; high: number };
  spo2: { low: number; high: number };
  nibpSys: { low: number; high: number };
  nibpDia: { low: number; high: number };
  rr: { low: number; high: number };
  temp: { low: number; high: number };
}

export interface AlarmState {
  level: 'none' | 'blue' | 'yellow' | 'red' | 'purple';
  message?: string;
  patientId?: string;
}

export interface VitalHistory {
  timestamp: number;
  hr: number;
  spo2: number;
  nibpSys: number;
  nibpDia: number;
  rr: number;
  temp: number;
}

export interface Medication {
  id: string;
  name: string;
  dose: string;
  rate?: string;
}

export interface LabResult {
  id: string;
  name: string;
  value: string;
  unit: string;
  time: number;
  isAbnormal: boolean;
}

export interface ClinicalNote {
  id: string;
  text: string;
  author: string;
  time: number;
}

export interface PatientData {
  id: string;
  name: string;
  room: string;
  diagnosis: string;
  doctor: string;
  assignedNurse: string;
  deviceBattery: number;
  admissionDate: number;
  vitals: VitalSigns;
  alarm: AlarmState;
  alarmLimits: AlarmLimits;
  scheduledCheck?: {
    intervalMs: number;
    nextCheckTime: number;
  };
  history: VitalHistory[];
  news2Score: number;
  isPinned: boolean;
  medications: Medication[];
  labs: LabResult[];
  notes: ClinicalNote[];
}

/** Server `vitals_update` payload (one row per patient). */
export interface VitalsUpdatePayload {
  id: string;
  vitals: VitalSigns;
  alarm: AlarmState;
  alarmLimits: AlarmLimits;
  scheduledCheck?: PatientData['scheduledCheck'];
  deviceBattery: number;
  news2Score: number;
  isPinned: boolean;
  medications: Medication[];
  labs: LabResult[];
  notes: ClinicalNote[];
  history?: VitalHistory[];
}

interface AppState {
  patients: Record<string, PatientData>;
  socket: Socket | null;
  privacyMode: boolean;
  searchQuery: string;
  selectedPatientId: string | null;
  isAudioMuted: boolean;
  togglePrivacyMode: () => void;
  setSearchQuery: (q: string) => void;
  setSelectedPatientId: (id: string | null) => void;
  toggleAudioMute: () => void;
  togglePinPatient: (patientId: string) => void;
  addClinicalNote: (patientId: string, note: Omit<ClinicalNote, 'id' | 'time'>) => void;
  acknowledgeAlarm: (patientId: string) => void;
  setSchedule: (patientId: string, intervalMs: number) => void;
  setAllSchedules: (intervalMs: number) => void;
  clearAlarm: (patientId: string) => void;
  updateLimits: (patientId: string, limits: Partial<AlarmLimits>) => void;
  measureNibp: (patientId: string) => void;
  admitPatient: (data: Partial<PatientData>) => void;
  dischargePatient: (patientId: string) => void;
  connect: () => void;
  disconnect: () => void;
}

export const useStore = create<AppState>((set, get) => ({
  patients: {},
  socket: null,
  privacyMode: false,
  searchQuery: '',
  selectedPatientId: null,
  isAudioMuted: false,
  
  togglePrivacyMode: () => set((state) => ({ privacyMode: !state.privacyMode })),
  setSearchQuery: (q) => set({ searchQuery: q }),
  setSelectedPatientId: (id) => set({ selectedPatientId: id }),
  toggleAudioMute: () => set((state) => ({ isAudioMuted: !state.isAudioMuted })),
  
  togglePinPatient: (patientId) => {
    const socket = get().socket;
    if (socket) socket.emit('toggle_pin', { patientId });
  },
  addClinicalNote: (patientId, note) => {
    const socket = get().socket;
    if (socket) socket.emit('add_note', { patientId, note });
  },
  acknowledgeAlarm: (patientId) => {
    const socket = get().socket;
    if (socket) socket.emit('acknowledge_alarm', { patientId });
  },

  setSchedule: (patientId, intervalMs) => {
    const socket = get().socket;
    if (socket) {
      socket.emit('set_schedule', { patientId, intervalMs });
    }
  },
  setAllSchedules: (intervalMs) => {
    const socket = get().socket;
    if (socket) {
      socket.emit('set_all_schedules', { intervalMs });
    }
  },
  clearAlarm: (patientId) => {
    const socket = get().socket;
    if (socket) {
      socket.emit('clear_alarm', { patientId });
    }
  },
  updateLimits: (patientId, limits) => {
    const socket = get().socket;
    if (socket) {
      socket.emit('update_limits', { patientId, limits });
    }
  },
  measureNibp: (patientId) => {
    const socket = get().socket;
    if (socket) {
      socket.emit('measure_nibp', { patientId });
    }
  },
  admitPatient: (data) => {
    const socket = get().socket;
    if (socket) {
      socket.emit('admit_patient', data);
    }
  },
  dischargePatient: (patientId) => {
    const socket = get().socket;
    if (socket) {
      socket.emit('discharge_patient', { patientId });
    }
  },
  connect: () => {
    if (get().socket) return;
    
    const socket = io(socketIoUrl(), {
      path: '/socket.io',
      // Avval polling, keyin WebSocket (server AsyncServer bilan mos)
      transports: ['polling', 'websocket'],
    });
    
    socket.on('initial_state', (data: PatientData[]) => {
      const patientsMap = data.reduce((acc, p) => {
        acc[p.id] = p;
        return acc;
      }, {} as Record<string, PatientData>);
      set({ patients: patientsMap });
    });

    socket.on('vitals_update', (updates: VitalsUpdatePayload[]) => {
      set((state) => {
        const newPatients = { ...state.patients };
        updates.forEach((update) => {
          if (newPatients[update.id]) {
            const p = newPatients[update.id];
            newPatients[update.id] = {
              ...p,
              vitals: update.vitals,
              alarm: update.alarm,
              alarmLimits: update.alarmLimits ?? p.alarmLimits,
              scheduledCheck: update.scheduledCheck,
              deviceBattery: update.deviceBattery ?? p.deviceBattery,
              history: update.history ?? p.history,
              news2Score: update.news2Score ?? p.news2Score,
              isPinned: update.isPinned ?? p.isPinned,
              medications: update.medications ?? p.medications,
              labs: update.labs ?? p.labs,
              notes: update.notes ?? p.notes
            };
          }
        });
        return { patients: newPatients };
      });
    });

    socket.on('patient_admitted', (patient: PatientData) => {
      set((state) => ({
        patients: { ...state.patients, [patient.id]: patient }
      }));
    });

    socket.on('patient_discharged', (patientId: string) => {
      set((state) => {
        const newPatients = { ...state.patients };
        delete newPatients[patientId];
        return { 
          patients: newPatients,
          selectedPatientId: state.selectedPatientId === patientId ? null : state.selectedPatientId
        };
      });
    });

    socket.on('connect_error', (error) => {
      console.error('Socket connection error:', error);
    });

    socket.on('disconnect', (reason) => {
      console.warn('Socket disconnected:', reason);
      if (reason === 'io server disconnect') {
        // the disconnection was initiated by the server, you need to reconnect manually
        socket.connect();
      }
    });

    set({ socket });
  },
  disconnect: () => {
    const socket = get().socket;
    if (socket) {
      socket.disconnect();
      set({ socket: null });
    }
  }
}));
