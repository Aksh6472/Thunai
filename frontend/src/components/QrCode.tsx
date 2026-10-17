import { encode } from 'uqr'

// Rendered as SVG rects from the matrix: no innerHTML (SECURITY T-10).
export function QrCode({
  value,
  label,
  size = 192,
}: {
  value: string
  label: string
  size?: number
}) {
  const { data } = encode(value, { ecc: 'M', border: 2 })
  const n = data.length
  const rects: string[] = []
  data.forEach((row, y) => row.forEach((on, x) => on && rects.push(`M${x} ${y}h1v1h-1z`)))
  return (
    <svg
      role="img"
      aria-label={label}
      width={size}
      height={size}
      viewBox={`0 0 ${n} ${n}`}
      shapeRendering="crispEdges"
      className="shrink-0 rounded"
    >
      <rect width={n} height={n} style={{ fill: 'var(--color-qr-light)' }} />
      <path d={rects.join('')} style={{ fill: 'var(--color-qr-dark)' }} />
    </svg>
  )
}
