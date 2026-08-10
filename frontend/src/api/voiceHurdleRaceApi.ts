const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';

export interface Patient {
  id: string;
  name: string;
  age?: number;
  date_of_birth?: string;
  language?: string;
  gender?: string;
  diagnosis?: string;
  therapist_name?: string;
  parent_name?: string;
  parent_contact?: string;
  email?: string;
  is_active: boolean;
  created_at: string;
}

export interface PatientLoginData {
  name: string;
  date_of_birth: string;
}

export interface PatientCreateData {
  name: string;
  age?: number;
  date_of_birth?: string;
  language?: string;
  gender?: string;
  diagnosis?: string;
  therapist_name?: string;
  parent_name?: string;
  parent_contact?: string;
  email?: string;
}

export interface VoiceHurdleRaceSession {
  patient_id: string;
  level_id: number;
  level_name: string;
  score: number;
  time_remaining: number;
  pitch_accuracy: number;
  loudness_accuracy: number;
  stars: number;
  session_type: string;
}

export interface Session {
  id: string;
  patient_id: string;
  target_word?: string;
  spoken_word?: string;
  accuracy?: number;
  feedback?: string;
  stars?: number;
  pitch?: number;
  loudness?: number;
  duration?: number;
  created_at: string;
}

class VoiceHurdleRaceApi {
  private baseUrl: string;

  constructor(baseUrl: string = API_BASE_URL) {
    this.baseUrl = baseUrl;
  }

  private async request<T>(
    endpoint: string,
    options: RequestInit = {}
  ): Promise<T> {
    const url = `${this.baseUrl}${endpoint}`;
    const response = await fetch(url, {
      headers: {
        'Content-Type': 'application/json',
        ...options.headers,
      },
      ...options,
    });

    if (!response.ok) {
      const error = await response.json().catch(() => ({ message: 'Request failed' }));
      throw new Error(error.message || error.detail || 'Request failed');
    }

    return response.json();
  }

  // Patient Authentication
  async loginPatient(data: PatientLoginData): Promise<Patient> {
    return this.request<Patient>('/patients/login', {
      method: 'POST',
      body: JSON.stringify(data),
    });
  }

  async createPatient(data: PatientCreateData): Promise<Patient> {
    return this.request<Patient>('/patients/', {
      method: 'POST',
      body: JSON.stringify(data),
    });
  }

  async getPatient(patientId: string): Promise<Patient> {
    return this.request<Patient>(`/patients/${patientId}`);
  }

  // Session Management
  async createVoiceHurdleRaceSession(sessionData: VoiceHurdleRaceSession): Promise<Session> {
    return this.request<Session>('/api/v1/voicehurdlerace/sessions', {
      method: 'POST',
      body: JSON.stringify(sessionData),
    });
  }

  async getVoiceHurdleRaceSessions(patientId: string): Promise<Session[]> {
    return this.request<Session[]>(`/api/v1/voicehurdlerace/patients/${patientId}/sessions`);
  }

  async getVoiceHurdleRaceLeaderboard(): Promise<any[]> {
    return this.request<any[]>('/api/v1/voicehurdlerace/leaderboard');
  }

  async getPatientSessions(patientId: string): Promise<Session[]> {
    return this.request<Session[]>(`/patients/${patientId}/sessions`);
  }

  async getAllSessions(): Promise<Session[]> {
    return this.request<Session[]>('/patients/sessions/all');
  }
}

export const voiceHurdleRaceApi = new VoiceHurdleRaceApi();
