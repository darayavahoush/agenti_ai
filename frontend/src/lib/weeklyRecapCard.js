// Renders a shareable PNG summarizing a kid's week, drawn from the exact
// same weekly_summary data ParentDashboard.jsx already displays -- no new
// backend endpoint. Plain <canvas>, no image/chart library: this only ever
// runs once per click, so the dependency weight of a canvas library isn't
// worth it for one drawing.
//
// Point of the feature: parents already screenshot the dashboard to send
// to the other parent/a grandparent. This gives them one designed image
// instead of a cropped screenshot with a "How we write this" tooltip in
// the corner.

// Kept in sync by hand with Creatures.jsx's CREATURE_ACCENTS keys (chick,
// dragon, bunny, fox, rocket, fish) -- canvas text can render an emoji
// directly, so there's no need to rasterize the actual SVG creature for
// something this size. NOT the same map as AddPatientModal.jsx's
// AVATAR_EMOJIS, which is stale (still has old species cloud/star instead
// of bunny/fox) -- that's a pre-existing bug elsewhere, left alone here.
const SPECIES_EMOJI = { chick: '🐥', dragon: '🐉', bunny: '🐰', fox: '🦊', rocket: '🚀', fish: '🐠' }

const WIDTH = 1080
const HEIGHT = 1350

function roundRect(ctx, x, y, w, h, r) {
  ctx.beginPath()
  ctx.moveTo(x + r, y)
  ctx.arcTo(x + w, y, x + w, y + h, r)
  ctx.arcTo(x + w, y + h, x, y + h, r)
  ctx.arcTo(x, y + h, x, y, r)
  ctx.arcTo(x, y, x + w, y, r)
  ctx.closePath()
}

function formatWeekRange(weekStartIso, weekEndIso) {
  const opts = { month: 'short', day: 'numeric' }
  const start = new Date(weekStartIso).toLocaleDateString('en', opts)
  const end = new Date(weekEndIso).toLocaleDateString('en', opts)
  return `${start} – ${end}`
}

/**
 * @param {object} data - the same object ParentDashboard.jsx renders from
 *   (child_first_name, avatar, weekly_summary: {stats, highlights, week_start, week_end})
 * @returns {Promise<Blob>} PNG blob, ready to share or download
 */
export function generateWeeklyRecapCard(data) {
  const canvas = document.createElement('canvas')
  canvas.width = WIDTH
  canvas.height = HEIGHT
  const ctx = canvas.getContext('2d')

  // Background -- same coral/mint/ink family as the parent app itself, so
  // a shared image still reads as "from this app" rather than a generic
  // stock gradient.
  const bg = ctx.createLinearGradient(0, 0, 0, HEIGHT)
  bg.addColorStop(0, '#1B1836')
  bg.addColorStop(0.5, '#3A2A4D')
  bg.addColorStop(1, '#5C3550')
  ctx.fillStyle = bg
  ctx.fillRect(0, 0, WIDTH, HEIGHT)

  const stats = data.weekly_summary?.stats || {}
  const practiceDays = stats.home_practice_days ?? 0
  const emoji = SPECIES_EMOJI[data.avatar] || '⭐'

  // Avatar circle
  ctx.beginPath()
  ctx.arc(WIDTH / 2, 190, 90, 0, Math.PI * 2)
  ctx.fillStyle = 'rgba(255,255,255,0.08)'
  ctx.fill()
  ctx.font = '96px serif'
  ctx.textAlign = 'center'
  ctx.textBaseline = 'middle'
  ctx.fillText(emoji, WIDTH / 2, 200)

  // Title
  ctx.fillStyle = '#FFFFFF'
  ctx.font = 'bold 56px "Segoe UI", Helvetica, Arial, sans-serif'
  ctx.fillText(`${data.child_first_name || 'This'}'s Week`, WIDTH / 2, 340)

  if (data.weekly_summary?.week_start && data.weekly_summary?.week_end) {
    ctx.fillStyle = 'rgba(255,255,255,0.45)'
    ctx.font = '32px "Segoe UI", Helvetica, Arial, sans-serif'
    ctx.fillText(formatWeekRange(data.weekly_summary.week_start, data.weekly_summary.week_end), WIDTH / 2, 395)
  }

  // Big practice-days number, the headline stat
  roundRect(ctx, 90, 460, WIDTH - 180, 260, 32)
  ctx.fillStyle = 'rgba(255,255,255,0.06)'
  ctx.fill()

  ctx.fillStyle = '#8FE3B8' // mint
  ctx.font = 'bold 160px "Segoe UI", Helvetica, Arial, sans-serif'
  ctx.fillText(`${practiceDays}/7`, WIDTH / 2, 570)
  ctx.fillStyle = 'rgba(255,255,255,0.6)'
  ctx.font = '34px "Segoe UI", Helvetica, Arial, sans-serif'
  ctx.fillText('days practised this week', WIDTH / 2, 660)

  // Secondary stat row
  const secondary = [
    [stats.home_practice_minutes ?? 0, 'minutes logged'],
    [stats.assignments_completed ?? 0, 'assignments done'],
    [stats.goals_achieved_total ?? 0, 'goals achieved'],
  ]
  const colW = (WIDTH - 180) / 3
  secondary.forEach(([value, label], i) => {
    const cx = 90 + colW * i + colW / 2
    ctx.fillStyle = '#FFFFFF'
    ctx.font = 'bold 64px "Segoe UI", Helvetica, Arial, sans-serif'
    ctx.fillText(String(value), cx, 830)
    ctx.fillStyle = 'rgba(255,255,255,0.45)'
    ctx.font = '26px "Segoe UI", Helvetica, Arial, sans-serif'
    // Manual two-line wrap -- these three labels are short and known in
    // advance, so a real text-wrapping pass would be overkill here.
    const words = label.split(' ')
    const mid = Math.ceil(words.length / 2)
    ctx.fillText(words.slice(0, mid).join(' '), cx, 875)
    ctx.fillText(words.slice(mid).join(' '), cx, 910)
  })

  // One highlight chip, if there is one -- these are already short,
  // punchy, chip-style facts (see WeeklySummaryOut.highlights), which is
  // exactly what a recap image wants over the full narrative paragraph.
  const highlight = data.weekly_summary?.highlights?.[0]
  if (highlight) {
    ctx.font = '600 34px "Segoe UI", Helvetica, Arial, sans-serif'
    const padding = 40
    const textWidth = ctx.measureText(highlight).width
    const chipWidth = Math.min(WIDTH - 160, textWidth + padding * 2)
    const chipX = (WIDTH - chipWidth) / 2
    roundRect(ctx, chipX, 990, chipWidth, 90, 45)
    ctx.fillStyle = 'rgba(143,227,184,0.18)'
    ctx.fill()
    ctx.strokeStyle = 'rgba(143,227,184,0.4)'
    ctx.lineWidth = 2
    ctx.stroke()
    ctx.fillStyle = '#8FE3B8'
    ctx.fillText(highlight, WIDTH / 2, 1038)
  }

  // Footer wordmark
  ctx.fillStyle = 'rgba(255,255,255,0.35)'
  ctx.font = '30px "Segoe UI", Helvetica, Arial, sans-serif'
  ctx.fillText('Vaak Games', WIDTH / 2, HEIGHT - 70)

  return new Promise((resolve, reject) => {
    canvas.toBlob((blob) => (blob ? resolve(blob) : reject(new Error('canvas.toBlob returned null'))), 'image/png')
  })
}

/**
 * Native share sheet when available (so it can go straight to Messages/
 * WhatsApp/etc. on mobile, which is the actual point of "shareable"), a
 * plain download otherwise -- e.g. desktop browsers, or a mobile browser
 * that doesn't implement the Web Share API's file-sharing (canShare).
 */
export async function shareOrDownloadRecapCard(blob, filename) {
  const file = new File([blob], filename, { type: 'image/png' })

  if (navigator.canShare?.({ files: [file] })) {
    try {
      await navigator.share({ files: [file], title: filename })
      return 'shared'
    } catch (err) {
      // AbortError just means the person closed the share sheet -- not a
      // failure worth falling back from into an unwanted download.
      if (err?.name === 'AbortError') return 'cancelled'
      // Any other share failure: fall through to download below.
    }
  }

  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = filename
  document.body.appendChild(a)
  a.click()
  a.remove()
  URL.revokeObjectURL(url)
  return 'downloaded'
}
