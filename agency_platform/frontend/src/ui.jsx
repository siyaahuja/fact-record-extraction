export const cn = (...c) => c.filter(Boolean).join(' ')

export function Button({ variant = 'default', size = 'md', className, ...p }) {
  const v = {
    default: 'bg-zinc-900 text-white hover:bg-zinc-800 shadow-sm',
    outline: 'border border-zinc-200 bg-white hover:bg-zinc-100 shadow-xs',
    ghost: 'hover:bg-zinc-100',
    success: 'bg-emerald-600 text-white hover:bg-emerald-700 shadow-sm',
    secondary: 'bg-zinc-100 hover:bg-zinc-200 text-zinc-900',
  }[variant]
  const s = { sm: 'h-8 px-3 text-xs', md: 'h-9 px-4 text-sm' }[size]
  return (
    <button
      className={cn('inline-flex items-center justify-center gap-1.5 rounded-md font-medium transition-colors cursor-pointer disabled:pointer-events-none disabled:opacity-50 whitespace-nowrap', v, s, className)}
      {...p}
    />
  )
}

export function Card({ className, ...p }) {
  return <div className={cn('rounded-xl border border-zinc-200 bg-white shadow-sm', className)} {...p} />
}

const BADGE = {
  default: 'bg-zinc-900 text-white border-transparent',
  outline: 'border-zinc-200 text-zinc-700',
  green: 'bg-emerald-50 text-emerald-700 border-emerald-200',
  amber: 'bg-amber-50 text-amber-800 border-amber-200',
  red: 'bg-red-50 text-red-700 border-red-200',
  blue: 'bg-sky-50 text-sky-700 border-sky-200',
  violet: 'bg-violet-50 text-violet-700 border-violet-200',
  zinc: 'bg-zinc-100 text-zinc-600 border-zinc-200',
}
export function Badge({ tone = 'outline', className, ...p }) {
  return <span className={cn('inline-flex items-center gap-1 rounded-md border px-2 py-0.5 text-xs font-medium whitespace-nowrap', BADGE[tone], className)} {...p} />
}

export function Switch({ checked, onChange, disabled }) {
  return (
    <button
      role="switch"
      aria-checked={checked}
      disabled={disabled}
      onClick={(e) => { e.stopPropagation(); onChange(!checked) }}
      className={cn('relative inline-flex h-5 w-9 shrink-0 cursor-pointer items-center rounded-full transition-colors disabled:opacity-50', checked ? 'bg-emerald-600' : 'bg-zinc-300')}
    >
      <span className={cn('inline-block h-4 w-4 rounded-full bg-white shadow transition-transform', checked ? 'translate-x-4.5' : 'translate-x-0.5')} />
    </button>
  )
}

export function Tabs({ tabs, value, onChange }) {
  return (
    <div className="inline-flex h-10 items-center rounded-lg bg-zinc-100 p-1 text-zinc-500">
      {tabs.map((t) => (
        <button
          key={t.value}
          onClick={() => onChange(t.value)}
          className={cn('inline-flex h-8 cursor-pointer items-center gap-2 rounded-md px-3 text-sm font-medium transition-all',
            value === t.value ? 'bg-white text-zinc-950 shadow-sm' : 'hover:text-zinc-900')}
        >
          {t.icon}{t.label}
          {t.count != null && <span className={cn('rounded px-1.5 text-xs', value === t.value ? 'bg-zinc-100' : 'bg-zinc-200/70')}>{t.count}</span>}
        </button>
      ))}
    </div>
  )
}

export function Stat({ label, value, hint, tone }) {
  return (
    <Card className="p-4">
      <div className="text-xs font-medium uppercase tracking-wide text-zinc-500">{label}</div>
      <div className={cn('mt-1 text-2xl font-semibold tabular-nums', tone)}>{value}</div>
      {hint && <div className="mt-0.5 text-xs text-zinc-500">{hint}</div>}
    </Card>
  )
}

export const STATUS_TONE = { verified: 'green', pending: 'amber', conflicting: 'red', superseded: 'zinc', rejected: 'zinc' }
export const TIER_TONE = { 1: 'violet', 2: 'violet', 3: 'blue', 4: 'blue', 5: 'amber', 6: 'zinc' }
