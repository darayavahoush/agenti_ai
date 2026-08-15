// Converts a react-easy-crop pixel-crop selection into a Blob, by drawing
// the cropped region of the source image onto an offscreen canvas.
export async function getCroppedImageBlob(imageSrc, cropPixels, mimeType = 'image/jpeg') {
  const image = await loadImage(imageSrc)
  const canvas = document.createElement('canvas')
  canvas.width = cropPixels.width
  canvas.height = cropPixels.height
  const ctx = canvas.getContext('2d')

  ctx.drawImage(
    image,
    cropPixels.x, cropPixels.y, cropPixels.width, cropPixels.height,
    0, 0, cropPixels.width, cropPixels.height,
  )

  return new Promise((resolve, reject) => {
    canvas.toBlob((blob) => {
      if (blob) resolve(blob)
      else reject(new Error('Canvas is empty'))
    }, mimeType, 0.92)
  })
}

function loadImage(src) {
  return new Promise((resolve, reject) => {
    const img = new Image()
    img.addEventListener('load', () => resolve(img))
    img.addEventListener('error', reject)
    img.crossOrigin = 'anonymous'
    img.src = src
  })
}
