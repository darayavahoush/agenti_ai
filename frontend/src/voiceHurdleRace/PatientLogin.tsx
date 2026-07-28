import { useState, useEffect } from 'react';
import { useAuth } from '../breathquest/context/AuthContext';
import { authAPI } from '../breathquest/api/client';
import { voiceHurdleRaceApi } from '../api/voiceHurdleRaceApi';
import { Button, Card, Input, Badge, StarRating, Avatar, Spinner, PageLoader } from '../breathquest/components/ui';

const AVATARS = ['chick', 'dragon', 'cloud', 'star', 'rocket', 'fish'];
const AVATAR_EMOJIS: Record<string, string> = { chick: '🐥', dragon: '🐉', cloud: '☁️', star: '⭐', rocket: '🚀', fish: '🐠' };

interface PatientLoginProps {
  onLogin: (name: string, dateOfBirth: string) => void;
  onRegister: (data: any) => void;
  error: string | null;
}

export default function PatientLogin({ onLogin, onRegister, error: propError }: PatientLoginProps) {
  const { loginKid, registerKid, loginTherapist, logout, therapist, isTherapist } = useAuth();
  
  // Views: landing | kid-choose | kid-register | kid-login | therapist-login | therapist-dashboard
  const [view, setView] = useState<'landing' | 'kid-choose' | 'kid-register' | 'kid-login' | 'therapist-login'>('landing');
  
  // Kid States
  const [avatar, setAvatar] = useState('chick');
  const [selectedPatientId, setSelectedPatientId] = useState('');
  const [patients, setPatients] = useState<any[]>([]);
  const [playerName, setPlayerName] = useState('');
  const [pin, setPin] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [registered, setRegistered] = useState<{ player_code: string; first_name: string } | null>(null);

  // Therapist States
  const [therapistEmail, setTherapistEmail] = useState('');
  const [therapistPassword, setTherapistPassword] = useState('');
  const [therapistPatients, setTherapistPatients] = useState<any[]>([]);
  const [selectedTherapistPatient, setSelectedTherapistPatient] = useState<any | null>(null);
  const [patientSessions, setPatientSessions] = useState<any[]>([]);
  const [leaderboard, setLeaderboard] = useState<any[]>([]);
  const [loadingTherapistData, setLoadingTherapistData] = useState(false);
  const [loadingSessions, setLoadingSessions] = useState(false);

  // Fetch kid candidates when opening register
  useEffect(() => {
    if (view === 'kid-register') {
      authAPI.kidCandidates()
        .then(({ data }) => setPatients(data))
        .catch(() => setError('Unable to load registered children. Please try again.'));
    }
  }, [view]);

  // Load therapist dashboard data
  useEffect(() => {
    if (isTherapist) {
      setLoadingTherapistData(true);
      Promise.all([
        authAPI.kidCandidates().then(({ data }) => setTherapistPatients(data)),
        voiceHurdleRaceApi.getVoiceHurdleRaceLeaderboard().then((data) => setLeaderboard(data))
      ])
        .catch((err) => console.error('Error fetching therapist data:', err))
        .finally(() => setLoadingTherapistData(false));
    }
  }, [isTherapist]);

  // Load selected patient sessions
  useEffect(() => {
    if (selectedTherapistPatient) {
      setLoadingSessions(true);
      voiceHurdleRaceApi.getVoiceHurdleRaceSessions(selectedTherapistPatient.id)
        .then((data) => setPatientSessions(data))
        .catch((err) => console.error('Error fetching sessions:', err))
        .finally(() => setLoadingSessions(false));
    } else {
      setPatientSessions([]);
    }
  }, [selectedTherapistPatient]);

  const handlePin = (digit: string) => {
    if (pin.length < 4) setPin((p) => p + digit);
  };
  const deletePin = () => setPin((p) => p.slice(0, -1));

  const handleKidRegister = async () => {
    if (!selectedPatientId) {
      setError('Choose a registered child');
      return;
    }
    if (pin.length < 4) {
      setError('Choose a 4-digit PIN');
      return;
    }
    setError(null);
    setLoading(true);
    try {
      const data = await registerKid(selectedPatientId, avatar, pin);
      setRegistered({ player_code: data.player_code, first_name: data.first_name });
    } catch (e: any) {
      setError(e.response?.data?.detail || 'Something went wrong');
    } finally {
      setLoading(false);
    }
  };

  const handleKidLogin = async () => {
    if (!playerName.trim()) {
      setError('Enter your registered name');
      return;
    }
    if (pin.length < 4) {
      setError('Enter your PIN');
      return;
    }
    setError(null);
    setLoading(true);
    try {
      await loginKid(playerName.trim(), pin);
      // Main component's auth check will handle redirecting to game
    } catch {
      setError('Wrong name or PIN — try again!');
      setPin('');
    } finally {
      setLoading(false);
    }
  };

  const handleTherapistLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!therapistEmail.trim() || !therapistPassword) {
      setError('Enter your email and password');
      return;
    }
    setError(null);
    setLoading(true);
    try {
      await loginTherapist(therapistEmail.trim(), therapistPassword);
    } catch (e: any) {
      setError(e.response?.data?.detail || 'Invalid email or password');
    } finally {
      setLoading(false);
    }
  };

  // Show player code after register
  if (registered) {
    return (
      <div className="min-h-screen flex flex-col items-center justify-center p-6 text-center"
           style={{ background: 'radial-gradient(ellipse at 50% 0%, #1a3a2a 0%, #12122A 60%)' }}>
        <div className="text-7xl mb-4 animate-bounce">{AVATAR_EMOJIS[avatar]}</div>
        <h1 className="font-display text-4xl font-black text-white mb-2">You're in! 🎉</h1>
        <p className="text-white/50 mb-8">Write this down so you can log back in:</p>
        <div className="bg-brand-card border-2 border-brand-green rounded-2xl p-8 mb-6 w-full max-w-xs">
          <p className="text-white/40 text-sm mb-1">Your Player Code</p>
          <p className="font-display text-4xl font-black text-brand-green tracking-widest mb-4">
            {registered.player_code}
          </p>
          <p className="text-white/40 text-sm mb-1">Your PIN</p>
          <p className="font-display text-3xl font-bold text-brand-amber tracking-widest">
            {'•'.repeat(pin.length)}
          </p>
        </div>
        <p className="text-white/30 text-xs mb-8">Show this to your therapist too!</p>
        <Button size="lg" onClick={() => window.location.reload()}>Let's Play! 🚀</Button>
      </div>
    );
  }

  // --- THERAPIST DASHBOARD ---
  if (isTherapist) {
    return (
      <div className="min-h-screen bg-brand-dark text-white flex flex-col">
        {/* Nav Bar */}
        <nav className="border-b border-white/10 px-6 py-4 flex items-center justify-between sticky top-0 bg-brand-dark/95 backdrop-blur z-10">
          <div className="flex items-center gap-3">
            <span className="text-2xl">🐶</span>
            <span className="font-display text-xl font-bold text-white">
              VoiceHurdle<span className="text-brand-green">Race</span>
            </span>
            <span className="text-xs bg-brand-teal/20 text-brand-teal px-2.5 py-0.5 rounded-full font-semibold border border-brand-teal/30">
              Therapist Portal
            </span>
          </div>
          <div className="flex items-center gap-4">
            <span className="text-white/50 text-sm">{therapist?.full_name}</span>
            <Button variant="ghost" size="sm" onClick={() => { logout(); setView('landing'); }}>Sign out</Button>
          </div>
        </nav>

        {loadingTherapistData ? (
          <div className="flex-1 flex items-center justify-center">
            <Spinner size="lg" />
          </div>
        ) : (
          <div className="max-w-6xl mx-auto px-6 py-8 w-full flex-1 grid grid-cols-1 md:grid-cols-3 gap-6">
            {/* Left Column: Patient List & Leaderboard */}
            <div className="md:col-span-1 flex flex-col gap-6">
              {/* Patient List Card */}
              <Card className="flex flex-col gap-4">
                <h2 className="text-lg font-bold text-white border-b border-white/10 pb-2">Active Patients</h2>
                <div className="flex flex-col gap-2 max-h-64 overflow-y-auto pr-1">
                  {therapistPatients.length === 0 ? (
                    <p className="text-white/45 text-sm">No active patients found.</p>
                  ) : (
                    therapistPatients.map((p) => (
                      <button
                        key={p.id}
                        onClick={() => setSelectedTherapistPatient(p)}
                        className={`w-full text-left px-3 py-2.5 rounded-xl transition-all border text-sm flex items-center gap-3
                          ${selectedTherapistPatient?.id === p.id 
                            ? 'bg-brand-green/20 border-brand-green text-brand-green font-bold' 
                            : 'bg-white/5 border-white/5 text-white/70 hover:bg-white/10'}`}
                      >
                        <span className="text-lg">👶</span>
                        <span className="truncate">{p.name}</span>
                      </button>
                    ))
                  )}
                </div>
              </Card>

              {/* Leaderboard Card */}
              <Card className="flex flex-col gap-4">
                <h2 className="text-lg font-bold text-brand-amber border-b border-white/10 pb-2">VHR Leaderboard 🏆</h2>
                <div className="flex flex-col gap-3">
                  {leaderboard.length === 0 ? (
                    <p className="text-white/45 text-sm">No sessions recorded yet.</p>
                  ) : (
                    leaderboard.map((item, idx) => (
                      <div key={item.session_id} className="flex items-center justify-between text-sm bg-white/5 p-2 rounded-lg border border-white/5">
                        <div className="flex items-center gap-2 min-w-0">
                          <span className="font-bold text-white/30 text-xs w-4">#{idx + 1}</span>
                          <span className="font-semibold text-white/80 truncate">{item.patient_name}</span>
                        </div>
                        <div className="flex items-center gap-2 flex-shrink-0">
                          <span className="text-brand-amber font-semibold">{item.stars}★</span>
                          <span className="text-xs text-white/40">{item.accuracy}%</span>
                        </div>
                      </div>
                    ))
                  )}
                </div>
              </Card>
            </div>

            {/* Right Column: Selected Patient Sessions */}
            <div className="md:col-span-2">
              {selectedTherapistPatient ? (
                <Card className="h-full flex flex-col gap-4">
                  <div className="flex items-center justify-between border-b border-white/10 pb-2">
                    <div>
                      <h2 className="text-xl font-bold text-white">{selectedTherapistPatient.name}</h2>
                      <p className="text-white/40 text-xs mt-0.5">Session Logs for Voice Hurdle Race</p>
                    </div>
                    <Button variant="ghost" size="sm" onClick={() => setSelectedTherapistPatient(null)}>Close</Button>
                  </div>

                  {loadingSessions ? (
                    <div className="flex-1 flex items-center justify-center py-12">
                      <Spinner />
                    </div>
                  ) : patientSessions.length === 0 ? (
                    <div className="flex-1 flex flex-col items-center justify-center text-center py-16">
                      <div className="text-5xl mb-3">🏃</div>
                      <p className="text-white/50 text-sm">No Voice Hurdle Race sessions played by this child yet.</p>
                    </div>
                  ) : (
                    <div className="flex-1 overflow-y-auto max-h-[500px] flex flex-col gap-3 pr-2">
                      {patientSessions.map((session) => (
                        <div key={session.id} className="bg-white/5 border border-white/10 rounded-xl p-4 flex flex-col sm:flex-row sm:items-center justify-between gap-4">
                          <div>
                            <div className="flex items-center gap-2">
                              <span className="font-semibold text-white">{session.target_word}</span>
                              <span className="text-xs text-white/30">{session.spoken_word}</span>
                            </div>
                            <div className="text-xs text-white/40 mt-1">
                              Played on {new Date(session.created_at).toLocaleDateString()} at {new Date(session.created_at).toLocaleTimeString([], {hour: '2-digit', minute:'2-digit'})}
                            </div>
                          </div>
                          <div className="flex items-center gap-4 flex-wrap sm:flex-nowrap">
                            <div className="text-center bg-white/5 px-3 py-1.5 rounded-lg border border-white/5">
                              <div className="text-[10px] text-white/40 font-bold uppercase">Accuracy</div>
                              <div className="text-sm font-semibold text-brand-green">{session.accuracy}%</div>
                            </div>
                            <div className="text-center bg-white/5 px-3 py-1.5 rounded-lg border border-white/5">
                              <div className="text-[10px] text-white/40 font-bold uppercase">Duration</div>
                              <div className="text-sm font-semibold text-brand-teal">{Math.round(session.duration)}s</div>
                            </div>
                            <div className="flex items-center bg-brand-amber/10 border border-brand-amber/20 px-3 py-2 rounded-lg">
                              <span className="text-brand-amber font-bold text-sm">
                                {Array.from({ length: 3 }, (_, i) => (
                                  <span key={i} className={i < session.stars ? 'text-brand-amber' : 'text-white/20'}>★</span>
                                ))}
                              </span>
                            </div>
                          </div>
                        </div>
                      ))}
                    </div>
                  )}
                </Card>
              ) : (
                <Card className="h-full flex flex-col items-center justify-center text-center py-24">
                  <div className="text-6xl mb-4 animate-float">🩺</div>
                  <h2 className="text-xl font-bold text-white">Select a Patient</h2>
                  <p className="text-white/40 text-sm max-w-sm mt-1">
                    Click a patient from the list on the left to see their session history, target accuracy, and stars earned.
                  </p>
                </Card>
              )}
            </div>
          </div>
        )}
      </div>
    );
  }

  // --- PORTAL LOGIN SCREENS ---
  return (
    <div className="min-h-screen flex flex-col items-center justify-center p-6 w-full"
         style={{
           background: view === 'landing' || view === 'therapist-login'
             ? 'radial-gradient(ellipse at 50% 0%, #1D3A6A 0%, #12122A 60%)'
             : 'radial-gradient(ellipse at 50% 0%, #2a1a4a 0%, #12122A 60%)'
         }}>
      
      {/* Floating Orbs */}
      <div className="absolute top-20 left-20 w-64 h-64 bg-brand-green/5 rounded-full blur-3xl pointer-events-none" />
      <div className="absolute bottom-20 right-20 w-64 h-64 bg-brand-purple/5 rounded-full blur-3xl pointer-events-none" />

      {/* Back button */}
      {view !== 'landing' && (
        <button
          onClick={() => { setView('landing'); setError(null); setPin(''); setPlayerName(''); }}
          className="absolute top-6 left-6 text-white/30 hover:text-white/60 text-sm flex items-center gap-1 transition-colors"
        >
          ← Back
        </button>
      )}

      {/* --- 1. LANDING PORTAL SELECT --- */}
      {view === 'landing' && (
        <div className="w-full max-w-lg text-center">
          <div className="text-7xl mb-4 animate-float">🐶</div>
          <h1 className="font-display text-5xl font-black text-white mb-2">
            VoiceHurdle<span className="text-brand-green">Race</span>
          </h1>
          <p className="text-white/50 text-lg mb-12">A voice-activated sports running game</p>

          <div className="flex flex-col sm:flex-row gap-6">
            {/* Kid portal */}
            <button
              onClick={() => setView('kid-choose')}
              className="flex-1 group relative overflow-hidden rounded-3xl p-8 text-center
                         bg-gradient-to-br from-brand-amber/20 to-brand-coral/20
                         border-2 border-brand-amber/30 hover:border-brand-amber/60
                         transition-all duration-300 hover:scale-105 hover:shadow-2xl
                         hover:shadow-brand-amber/20 text-white"
            >
              <div className="text-6xl mb-3 group-hover:animate-bounce">🐥</div>
              <h2 className="font-display text-2xl font-bold text-brand-amber mb-1">I'm a Kid!</h2>
              <p className="text-white/50 text-sm">Run and jump</p>
              <div className="absolute inset-0 bg-gradient-to-br from-brand-amber/5 to-transparent
                              opacity-0 group-hover:opacity-100 transition-opacity" />
            </button>

            {/* Therapist portal */}
            <button
              onClick={() => setView('therapist-login')}
              className="flex-1 group relative overflow-hidden rounded-3xl p-8 text-center
                         bg-gradient-to-br from-brand-green/20 to-brand-teal/20
                         border-2 border-brand-green/30 hover:border-brand-green/60
                         transition-all duration-300 hover:scale-105 hover:shadow-2xl
                         hover:shadow-brand-green/20 text-white"
            >
              <div className="text-6xl mb-3 group-hover:animate-bounce">🩺</div>
              <h2 className="font-display text-2xl font-bold text-brand-green mb-1">Therapist</h2>
              <p className="text-white/50 text-sm">View logs & progress</p>
              <div className="absolute inset-0 bg-gradient-to-br from-brand-green/5 to-transparent
                              opacity-0 group-hover:opacity-100 transition-opacity" />
            </button>
          </div>
        </div>
      )}

      {/* --- 2. KID CHOOSE FLOW --- */}
      {view === 'kid-choose' && (
        <div className="text-center w-full max-w-sm">
          <div className="text-7xl mb-4 animate-float">🎮</div>
          <h1 className="font-display text-4xl font-black text-white mb-2">VoiceHurdleRace</h1>
          <p className="text-white/40 mb-10">Ready to play?</p>
          <div className="flex flex-col gap-4">
            <button
              onClick={() => setView('kid-register')}
              className="p-6 rounded-2xl bg-gradient-to-br from-brand-amber/20 to-brand-coral/20
                         border-2 border-brand-amber/40 hover:border-brand-amber
                         transition-all hover:scale-105 text-left text-white"
            >
              <div className="text-3xl mb-2">✨</div>
              <p className="font-display text-xl font-bold text-white">Set Up PIN</p>
              <p className="text-white/40 text-sm">Choose a registered child</p>
            </button>
            <button
              onClick={() => setView('kid-login')}
              className="p-6 rounded-2xl bg-gradient-to-br from-brand-green/20 to-brand-teal/20
                         border-2 border-brand-green/40 hover:border-brand-green
                         transition-all hover:scale-105 text-left text-white"
            >
              <div className="text-3xl mb-2">🔑</div>
              <p className="font-display text-xl font-bold text-white">I have a code</p>
              <p className="text-white/40 text-sm">Log back in</p>
            </button>
          </div>
        </div>
      )}

      {/* --- 3. KID SETUP PIN / REGISTER --- */}
      {view === 'kid-register' && (
        <div className="w-full max-w-sm">
          <h1 className="font-display text-3xl font-black text-white mb-6 text-center">Set Up Game PIN</h1>

          {/* Registered child */}
          <div className="mb-4 flex flex-col gap-1.5">
            <label className="text-sm text-white/50 block">Choose a registered child</label>
            <select
              className="w-full bg-white/5 border border-white/15 rounded-xl px-4 py-3 text-white focus:outline-none focus:border-brand-green transition-colors text-lg"
              value={selectedPatientId}
              onChange={(e) => setSelectedPatientId(e.target.value)}
            >
              <option value="" className="bg-brand-dark">Select a child</option>
              {patients.map((patient) => (
                <option key={patient.id} value={patient.id} className="bg-brand-dark">
                  {patient.name}
                </option>
              ))}
            </select>
            {patients.length === 0 && (
              <p className="text-white/40 text-xs mt-1">No children found. Register the child in Assessment first.</p>
            )}
          </div>

          {/* Avatar selection */}
          <label className="text-sm text-white/50 block mb-2">Pick your character</label>
          <div className="grid grid-cols-6 gap-2 mb-6">
            {AVATARS.map((av) => (
              <button
                key={av}
                onClick={() => setAvatar(av)}
                className={`h-12 rounded-xl text-2xl transition-all border-2 flex items-center justify-center
                  ${avatar === av ? 'border-brand-green bg-brand-green/20 scale-110' : 'border-white/10 bg-white/5'}`}
              >
                {AVATAR_EMOJIS[av]}
              </button>
            ))}
          </div>

          {/* PIN keypad */}
          <label className="text-sm text-white/50 block mb-2 text-center">Choose a 4-digit PIN</label>
          <div className="flex justify-center gap-3 mb-4">
            {[0, 1, 2, 3].map((i) => (
              <div
                key={i}
                className={`w-5 h-5 rounded-full border-2 transition-all
                  ${pin.length > i ? 'bg-brand-green border-brand-green scale-110 shadow-lg shadow-brand-green/30' : 'border-white/30'}`}
              />
            ))}
          </div>

          <div className="grid grid-cols-3 gap-2 mb-4">
            {[1, 2, 3, 4, 5, 6, 7, 8, 9, '', 0, '⌫'].map((d, i) => (
              <button
                key={i}
                onClick={() => (d === '⌫' ? deletePin() : d !== '' ? handlePin(String(d)) : null)}
                disabled={d === ''}
                className={`h-14 rounded-xl font-display text-xl font-bold transition-all active:scale-95 text-white
                  ${d === '' ? 'invisible' : d === '⌫' ? 'bg-white/5 text-white/50 hover:bg-white/10' : 'bg-white/10 text-white hover:bg-brand-green/20 hover:text-brand-green'}`}
              >
                {d}
              </button>
            ))}
          </div>

          {error && <p className="text-brand-coral text-sm text-center mb-3">{error}</p>}
          <Button className="w-full" size="lg" onClick={handleKidRegister} disabled={loading}>
            {loading ? 'Saving…' : 'Save PIN & Play! 🎉'}
          </Button>
        </div>
      )}

      {/* --- 4. KID LOGIN ("I have a code") --- */}
      {view === 'kid-login' && (
        <div className="w-full max-w-sm">
          <h1 className="font-display text-3xl font-black text-white mb-6 text-center">Welcome Back!</h1>

          <div className="mb-4">
            <Input
              label="Your registered name or player code"
              placeholder="e.g. Alex or P01A2B3C4"
              value={playerName}
              onChange={(e: any) => setPlayerName(e.target.value)}
              className="text-center text-xl font-bold font-display"
            />
          </div>

          <label className="text-sm text-white/50 block mb-2 text-center">Your PIN</label>
          <div className="flex justify-center gap-3 mb-4">
            {[0, 1, 2, 3].map((i) => (
              <div
                key={i}
                className={`w-5 h-5 rounded-full border-2 transition-all
                  ${pin.length > i ? 'bg-brand-green border-brand-green scale-110 shadow-lg shadow-brand-green/30' : 'border-white/30'}`}
              />
            ))}
          </div>

          <div className="grid grid-cols-3 gap-2 mb-4">
            {[1, 2, 3, 4, 5, 6, 7, 8, 9, '', 0, '⌫'].map((d, i) => (
              <button
                key={i}
                onClick={() => (d === '⌫' ? deletePin() : d !== '' ? handlePin(String(d)) : null)}
                disabled={d === ''}
                className={`h-14 rounded-xl font-display text-xl font-bold transition-all active:scale-95 text-white
                  ${d === '' ? 'invisible' : d === '⌫' ? 'bg-white/5 text-white/50 hover:bg-white/10' : 'bg-white/10 text-white hover:bg-brand-green/20 hover:text-brand-green'}`}
              >
                {d}
              </button>
            ))}
          </div>

          {error && <p className="text-brand-coral text-sm text-center mb-3">{error}</p>}
          <Button className="w-full" size="lg" onClick={handleKidLogin} disabled={loading}>
            {loading ? 'Checking…' : "Let's Play! 🚀"}
          </Button>
        </div>
      )}

      {/* --- 5. THERAPIST LOGIN --- */}
      {view === 'therapist-login' && (
        <Card className="w-full max-w-sm flex flex-col gap-6">
          <div className="text-center">
            <h1 className="font-display text-3xl font-bold text-white">Therapist Portal</h1>
            <p className="text-white/40 text-sm mt-1">Access Voice Hurdle Race Dashboard</p>
          </div>

          <form onSubmit={handleTherapistLogin} className="flex flex-col gap-4">
            <Input
              label="Email Address"
              type="email"
              placeholder="therapist@clinic.com"
              value={therapistEmail}
              onChange={(e: any) => setTherapistEmail(e.target.value)}
              required
            />

            <Input
              label="Password"
              type="password"
              placeholder="••••••••"
              value={therapistPassword}
              onChange={(e: any) => setTherapistPassword(e.target.value)}
              required
            />

            {error && <p className="text-brand-coral text-sm text-center">{error}</p>}

            <Button type="submit" className="w-full mt-2" size="lg" disabled={loading}>
              {loading ? 'Signing in…' : 'Sign In'}
            </Button>
          </form>
        </Card>
      )}
    </div>
  );
}
