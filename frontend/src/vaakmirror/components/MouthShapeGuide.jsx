// A real illustrated reference photo/drawing of each target mouth shape,
// shown next to the letter so the child has something to visually copy —
// not just a text instruction. It still animates in a way that mimics the
// actual articulatory motion for that sound's manner (a quick pop for
// plosives, a shimmer for fricatives, etc.) and the surrounding ring/glow
// still reflects live match quality once the camera starts scoring — we
// just swapped the abstract line-art for real mouth-shape illustrations.

import lipsClosedImg from '../assets/mouth-shapes/lips-closed.png'
import lipTeethImg from '../assets/mouth-shapes/lip-teeth.png'
import wideNarrowImg from '../assets/mouth-shapes/wide-narrow.png'
import tongueTipUpImg from '../assets/mouth-shapes/tongue-tip-up.png'
import roundForwardImg from '../assets/mouth-shapes/round-forward.png'
import openWideImg from '../assets/mouth-shapes/open-wide.png'
import tongueBetweenTeethImg from '../assets/mouth-shapes/tongue-between-teeth.png'
import neutralOpenImg from '../assets/mouth-shapes/neutral-open.png'

const SHAPE_IMAGES = {
  'lips-closed': lipsClosedImg,
  'lip-teeth': lipTeethImg,
  'wide-narrow': wideNarrowImg,
  'tongue-tip-up': tongueTipUpImg,
  'round-forward': roundForwardImg,
  'open-wide': openWideImg,
  'tongue-between-teeth': tongueBetweenTeethImg,
  'neutral-open': neutralOpenImg,
}

const TIER_COLOR = {
  idle: '#FBF7EE55',
  green: '#2FB8A6',
  yellow: '#F4B942',
  red: '#F0604A',
}

// animation name -> keyframe CSS + duration, keyed by manner of articulation
const MOTION = {
  Plosive: { name: 'mgPop', duration: '1.6s' },
  Affricate: { name: 'mgPopShimmer', duration: '1.8s' },
  Fricative: { name: 'mgShimmer', duration: '0.6s' },
  Nasal: { name: 'mgBreathe', duration: '2.2s' },
  Approximant: { name: 'mgSettle', duration: '2.4s' },
  'Lateral Approximant': { name: 'mgSettle', duration: '2.4s' },
}

export default function MouthShapeGuide({ shape, manner, tier = 'idle', className = '' }) {
  const color = TIER_COLOR[tier] ?? TIER_COLOR.idle
  const motion = MOTION[manner]
  const src = SHAPE_IMAGES[shape]

  return (
    <div
      className={className}
      style={{
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        position: 'relative',
      }}
    >
      <div
        style={{
          width: '100%',
          height: '100%',
          borderRadius: '9999px',
          boxShadow: `0 0 0 3px ${color}`,
          transition: 'box-shadow 150ms ease',
          overflow: 'hidden',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          background: '#FBF7EE',
          transformOrigin: '50% 50%',
          animation: motion ? `${motion.name} ${motion.duration} ease-in-out infinite` : undefined,
        }}
      >
        {src ? (
          <img
            src={src}
            alt={`Mouth shape reference for ${shape.replace(/-/g, ' ')}`}
            style={{ width: '85%', height: '85%', objectFit: 'contain' }}
            draggable={false}
          />
        ) : null}
      </div>
      <style>{`
        @keyframes mgPop {
          0%   { transform: scale(0.9); opacity: 0.65; }
          14%  { transform: scale(1.05); opacity: 1; }
          30%  { transform: scale(0.9); opacity: 0.65; }
          100% { transform: scale(0.9); opacity: 0.65; }
        }
        @keyframes mgPopShimmer {
          0%   { transform: scale(0.9) translateX(0); opacity: 0.65; }
          12%  { transform: scale(1.05) translateX(0); opacity: 1; }
          28%  { transform: scale(1) translateX(0); }
          42%  { transform: scale(1) translateX(-2px); }
          56%  { transform: scale(1) translateX(2px); }
          70%  { transform: scale(1) translateX(-1px); }
          85%  { transform: scale(0.95) translateX(0); opacity: 0.8; }
          100% { transform: scale(0.9) translateX(0); opacity: 0.65; }
        }
        @keyframes mgShimmer {
          0%, 100% { transform: translateX(0); }
          25%      { transform: translateX(-1.5px); }
          75%      { transform: translateX(1.5px); }
        }
        @keyframes mgBreathe {
          0%, 100% { transform: scale(1); opacity: 0.85; }
          50%      { transform: scale(1.045); opacity: 1; }
        }
        @keyframes mgSettle {
          0%, 100% { transform: scale(0.98) translateY(0); }
          50%      { transform: scale(1.015) translateY(-1px); }
        }
        @media (prefers-reduced-motion: reduce) {
          div { animation: none !important; }
        }
      `}</style>
    </div>
  )
}
