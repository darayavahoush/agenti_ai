import { useState, useCallback } from 'react'
import Cropper from 'react-easy-crop'
import { X, Check } from 'lucide-react'
import { getCroppedImageBlob } from '../../lib/cropImage'

// Full-screen crop step between picking a file and uploading it.
// imageSrc is a local object URL (see MyAccount.jsx's handlePhotoUpload) --
// nothing is sent to the server until the kid confirms the crop.
export default function PhotoCropModal({ imageSrc, onCancel, onConfirm, saving }) {
  const [crop, setCrop] = useState({ x: 0, y: 0 })
  const [zoom, setZoom] = useState(1)
  const [croppedAreaPixels, setCroppedAreaPixels] = useState(null)
  const [cropping, setCropping] = useState(false)
  const [cropError, setCropError] = useState(null)

  const onCropComplete = useCallback((_, pixels) => {
    setCroppedAreaPixels(pixels)
  }, [])

  async function handleConfirm() {
    // Guard against rapid double-taps starting a second crop+confirm
    // before the first one finishes -- without this, onConfirm(blob)
    // could fire twice concurrently for one tap-happy kid.
    if (!croppedAreaPixels || cropping || saving) return
    setCropError(null)
    setCropping(true)
    try {
      const blob = await getCroppedImageBlob(imageSrc, croppedAreaPixels)
      onConfirm(blob)
    } catch (err) {
      console.error('Failed to crop image', err)
      setCropError("Couldn't process that photo — try again.")
    } finally {
      setCropping(false)
    }
  }

  return (
    <div className="fixed inset-0 z-50 flex flex-col bg-black/90">
      <div className="relative flex-1">
        <Cropper
          image={imageSrc}
          crop={crop}
          zoom={zoom}
          aspect={1}
          cropShape="round"
          showGrid={false}
          onCropChange={setCrop}
          onZoomChange={setZoom}
          onCropComplete={onCropComplete}
        />
      </div>

      <div className="bg-black/95 px-6 py-5 flex flex-col gap-4">
        <div className="flex items-center gap-3 max-w-sm mx-auto w-full">
          <span className="text-white/40 text-xs">Zoom</span>
          <input
            type="range"
            min={1}
            max={3}
            step={0.01}
            value={zoom}
            onChange={(e) => setZoom(Number(e.target.value))}
            className="flex-1 accent-brand-green"
          />
        </div>

        {cropError && (
          <p className="text-center text-sm text-red-400 max-w-sm mx-auto w-full">{cropError}</p>
        )}

        <div className="flex items-center justify-center gap-4">
          <button
            onClick={onCancel}
            disabled={saving || cropping}
            className="flex items-center gap-1.5 px-5 py-2.5 rounded-full text-white/60 hover:text-white
                       hover:bg-white/10 transition-colors text-sm font-medium"
          >
            <X size={16} /> Cancel
          </button>
          <button
            onClick={handleConfirm}
            disabled={saving || cropping || !croppedAreaPixels}
            className="flex items-center gap-1.5 px-5 py-2.5 rounded-full bg-brand-green text-ink
                       hover:bg-brand-green/90 transition-colors text-sm font-semibold disabled:opacity-50"
          >
            <Check size={16} /> {saving ? 'Saving…' : cropping ? 'Processing…' : 'Use this photo'}
          </button>
        </div>
      </div>
    </div>
  )
}
