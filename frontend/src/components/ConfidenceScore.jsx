const styles = {
  high: 'border-emerald-200 bg-emerald-50 text-emerald-700',
  medium: 'border-amber-200 bg-amber-50 text-amber-700',
  low: 'border-red-200 bg-red-50 text-red-700',
}

export default function ConfidenceScore({ confidence }) {
  const level = (confidence || 'low').toLowerCase()
  const label = level.charAt(0).toUpperCase() + level.slice(1)

  return (
    <span
      className={`inline-flex min-w-[76px] items-center justify-center rounded-md border px-2.5 py-1 text-xs font-semibold ${styles[level] || styles.low}`}
    >
      {label}
    </span>
  )
}
