export default function BreathQuestLanding({ setPage }) {
  return (
    <div className="min-h-screen flex flex-col items-center justify-center p-6"
         style={{ background: 'radial-gradient(ellipse at 50% 0%, #1D3A6A 0%, #12122A 60%)' }}>

      {/* Floating orbs */}
      <div className="absolute top-20 left-20 w-64 h-64 bg-green-400/10 rounded-full blur-3xl pointer-events-none" />
      <div className="absolute bottom-20 right-20 w-64 h-64 bg-purple-400/10 rounded-full blur-3xl pointer-events-none" />

      {/* Logo */}
      <div className="text-center mb-16" style={{ animation: 'float 3s ease-in-out infinite' }}>
        <div className="text-7xl mb-4">💨</div>
        <h1 className="text-5xl font-black text-white mb-2" style={{ fontFamily: 'sans-serif' }}>
          Breath<span className="text-green-400">Quest</span>
        </h1>
        <p className="text-white/50 text-lg">A breath-training adventure for kids</p>
      </div>

      {/* Two portals */}
      <div className="flex flex-col sm:flex-row gap-6 w-full max-w-lg">

        {/* Kid portal */}
        <button
          onClick={() => setPage('breathquest-play')}
          className="flex-1 group relative overflow-hidden rounded-3xl p-8 text-center
                     bg-gradient-to-br from-amber-400/20 to-orange-400/20
                     border-2 border-amber-400/30 hover:border-amber-400/60
                     transition-all duration-300 hover:scale-105 hover:shadow-2xl
                     hover:shadow-amber-400/20"
        >
          <div className="text-6xl mb-3 group-hover:animate-bounce">🐥</div>
          <h2 className="text-2xl font-bold text-amber-400 mb-1" style={{ fontFamily: 'sans-serif' }}>I'm a Kid!</h2>
          <p className="text-white/50 text-sm">Play the game</p>
          <div className="absolute inset-0 bg-gradient-to-br from-amber-400/5 to-transparent
                          opacity-0 group-hover:opacity-100 transition-opacity" />
        </button>

        {/* Therapist portal */}
        <button
          onClick={() => setPage('breathquest-therapist-login')}
          className="flex-1 group relative overflow-hidden rounded-3xl p-8 text-center
                     bg-gradient-to-br from-green-400/20 to-teal-400/20
                     border-2 border-green-400/30 hover:border-green-400/60
                     transition-all duration-300 hover:scale-105 hover:shadow-2xl
                     hover:shadow-green-400/20"
        >
          <div className="text-6xl mb-3 group-hover:animate-bounce">🩺</div>
          <h2 className="text-2xl font-bold text-green-400 mb-1" style={{ fontFamily: 'sans-serif' }}>Therapist</h2>
          <p className="text-white/50 text-sm">View dashboard</p>
          <div className="absolute inset-0 bg-gradient-to-br from-green-400/5 to-transparent
                          opacity-0 group-hover:opacity-100 transition-opacity" />
        </button>
      </div>

      {/* Back to therapy */}
      <button 
        onClick={() => setPage('therapy')}
        className="mt-12 text-white/30 hover:text-white/60 text-sm transition-colors"
      >
        ← Back to Therapy
      </button>

      <p className="mt-4 text-white/20 text-xs">BreathQuest © 2025</p>

      <style>{`
        @keyframes float {
          0%, 100% { transform: translateY(0); }
          50% { transform: translateY(-10px); }
        }
      `}</style>
    </div>
  )
}
