/**
 * Level Selection Page for Voice Hurdle Race
 * Displays all levels with unlock status and star ratings
 */

import { useEffect, useState } from 'react';
import { LEVELS, LevelProgress, getLevelProgress } from './levels';

interface LevelSelectionProps {
  onSelectLevel: (levelId: number) => void;
  onBack: () => void;
}

export default function LevelSelection({ onSelectLevel, onBack }: LevelSelectionProps) {
  const [levelProgress, setLevelProgress] = useState<LevelProgress[]>([]);

  useEffect(() => {
    setLevelProgress(getLevelProgress());
  }, []);

  const renderStars = (stars: number) => {
    return (
      <div style={{ display: 'flex', gap: '4px' }}>
        {[1, 2, 3].map((star) => (
          <span key={star} style={{ 
            fontSize: '1.5rem',
            opacity: star <= stars ? 1 : 0.3
          }}>
            ⭐
          </span>
        ))}
      </div>
    );
  };

  return (
    <div style={{
      width: '100vw',
      height: '100vh',
      background: 'linear-gradient(180deg, #fffaf2 0%, #f7f3ff 52%, #eefbff 100%)',
      position: 'fixed',
      top: 0,
      left: 0,
      overflow: 'auto',
      padding: '40px 20px',
      display: 'flex',
      flexDirection: 'column',
      alignItems: 'center'
    }}>
      <h1 style={{
        fontSize: '2.5rem',
        color: '#5b21b6',
        marginBottom: '10px',
        fontFamily: 'Comic Sans MS, cursive, sans-serif'
      }}>
        🐶 Voice Hurdle Race 🏁
      </h1>
      
      <p style={{
        fontSize: '1.2rem',
        color: '#64748b',
        marginBottom: '30px'
      }}>
        Select a level to play!
      </p>

      <div style={{
        display: 'grid',
        gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))',
        gap: '20px',
        maxWidth: '1200px',
        width: '100%',
        marginBottom: '30px'
      }}>
        {LEVELS.map((level) => {
          const progress = levelProgress.find(p => p.levelId === level.id) || {
            stars: 0,
            unlocked: false,
            completed: false
          };

          return (
            <div
              key={level.id}
              onClick={() => progress.unlocked && onSelectLevel(level.id)}
              style={{
                background: progress.unlocked 
                  ? 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)'
                  : 'linear-gradient(135deg, #9ca3af 0%, #6b7280 100%)',
                borderRadius: '20px',
                padding: '25px',
                color: 'white',
                cursor: progress.unlocked ? 'pointer' : 'not-allowed',
                boxShadow: progress.unlocked
                  ? '0 10px 30px rgba(102, 126, 234, 0.3)'
                  : '0 10px 30px rgba(107, 114, 128, 0.2)',
                transition: 'transform 0.2s, box-shadow 0.2s',
                opacity: progress.unlocked ? 1 : 0.6,
                border: progress.completed ? '3px solid #fbbf24' : 'none'
              }}
              onMouseEnter={(e) => {
                if (progress.unlocked) {
                  e.currentTarget.style.transform = 'translateY(-5px)';
                  e.currentTarget.style.boxShadow = '0 15px 40px rgba(102, 126, 234, 0.4)';
                }
              }}
              onMouseLeave={(e) => {
                e.currentTarget.style.transform = 'translateY(0)';
                e.currentTarget.style.boxShadow = progress.unlocked
                  ? '0 10px 30px rgba(102, 126, 234, 0.3)'
                  : '0 10px 30px rgba(107, 114, 128, 0.2)';
              }}
            >
              <div style={{
                display: 'flex',
                justifyContent: 'space-between',
                alignItems: 'center',
                marginBottom: '15px'
              }}>
                <h2 style={{
                  fontSize: '1.5rem',
                  margin: 0,
                  fontWeight: 'bold'
                }}>
                  {level.name}
                </h2>
                {!progress.unlocked && (
                  <span style={{ fontSize: '2rem' }}>🔒</span>
                )}
              </div>

              <p style={{
                fontSize: '1rem',
                marginBottom: '15px',
                opacity: 0.9
              }}>
                {level.description}
              </p>

              <div style={{
                display: 'flex',
                flexDirection: 'column',
                gap: '8px',
                fontSize: '0.9rem',
                marginBottom: '15px',
                opacity: 0.85
              }}>
                <div>⏱️ Time: {level.duration}s</div>
                <div>🏃 Hurdles: {level.numHurdles}</div>
                <div>🎯 Pitch: {level.targetPitch}Hz ±{level.pitchTolerance}Hz</div>
                <div>🔊 Loudness: {level.targetLoudness}dB ±{level.loudnessTolerance}dB</div>
              </div>

              {progress.completed && (
                <div style={{
                  marginTop: '15px',
                  padding: '10px',
                  background: 'rgba(255, 255, 255, 0.2)',
                  borderRadius: '10px',
                  textAlign: 'center'
                }}>
                  <div style={{ fontSize: '0.9rem', marginBottom: '5px' }}>
                    Stars Earned:
                  </div>
                  {renderStars(progress.stars)}
                </div>
              )}

              {!progress.unlocked && (
                <div style={{
                  marginTop: '15px',
                  padding: '10px',
                  background: 'rgba(0, 0, 0, 0.2)',
                  borderRadius: '10px',
                  textAlign: 'center',
                  fontSize: '0.9rem'
                }}>
                  Complete previous level to unlock
                </div>
              )}
            </div>
          );
        })}
      </div>

      <button
        onClick={onBack}
        style={{
          padding: '15px 40px',
          fontSize: '1.2rem',
          fontWeight: 'bold',
          borderRadius: '50px',
          border: 'none',
          background: 'linear-gradient(90deg, #f59e0b, #f97316)',
          color: 'white',
          cursor: 'pointer',
          boxShadow: '0 8px 18px rgba(245, 158, 11, 0.28)',
          marginTop: '20px'
        }}
      >
        ← Back to Menu
      </button>
    </div>
  );
}
