import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import {
  AlertTriangle, ArrowLeft, Building2, Check, CheckCircle2, ChevronRight, Download, FileText, Layers, Loader2,
  Mic, Quote, RotateCcw, Scale, Send, Upload, X,
} from 'lucide-react'
import { Badge, Button, Card, cn, Stat, STATUS_TONE, Switch, Tabs, TIER_TONE } from './ui.jsx'

const api = async (path, opts) => {
  const r = await fetch(`/api${path}`, opts)
  const d = await r.json()
  if (!r.ok) throw new Error(d.detail || r.statusText)
  return d
}
const post = (path, body) => api(path, { method: 'POST', headers: { 'content-type': 'application/json' }, body: JSON.stringify(body) })

const useHash = () => {
  const [h, setH] = useState(window.location.hash.slice(1))
  useEffect(() => {
    const f = () => setH(window.location.hash.slice(1))
    window.addEventListener('hashchange', f)
    return () => window.removeEventListener('hashchange', f)
  }, [])
  return h
}

const unitLabel = (u) => (u || '').split(':').slice(1).join(':').replace(/ vs .*/, '').replace(/-/g, ' ') || 'development'
const prettyField = (f) => ({ floor_area: 'Floor area', epc_rating: 'EPC rating', transaction_type: 'Transaction', bathroom_fixture: 'Bathroom fittings' }[f] || f.replace(/_/g, ' ').replace(/^./, (c) => c.toUpperCase()))
const qualText = (q) => Object.entries(q || {}).filter(([k]) => k !== 'basis' && k !== 'scope').map(([k, v]) => `${k.replace(/_/g, ' ')}: ${String(v).replace(/_/g, ' ')}`).join(', ')

function download(name, obj) {
  const a = document.createElement('a')
  a.href = URL.createObjectURL(new Blob([JSON.stringify(obj, null, 2)], { type: 'application/json' }))
  a.download = name
  a.click()
}

function Toast({ toast, onClose }) {
  useEffect(() => { if (toast) { const t = setTimeout(onClose, 4500); return () => clearTimeout(t) } }, [toast, onClose])
  if (!toast) return null
  return (
    <div className="fixed bottom-6 right-6 z-50 flex max-w-md items-start gap-3 rounded-xl border border-zinc-200 bg-white p-4 shadow-lg">
      {toast.error ? <AlertTriangle className="mt-0.5 size-4 text-red-600" /> : <CheckCircle2 className="mt-0.5 size-4 text-emerald-600" />}
      <div className="text-sm"><div className="font-medium">{toast.title}</div>{toast.body && <div className="mt-0.5 text-zinc-500">{toast.body}</div>}</div>
    </div>
  )
}

function Shell({ children, right }) {
  return (
    <div className="min-h-screen">
      <header className="sticky top-0 z-30 border-b border-zinc-200 bg-white/80 backdrop-blur">
        <div className="mx-auto flex h-14 max-w-7xl items-center justify-between px-6">
          <a href="#" className="flex items-center gap-2 font-semibold tracking-tight">
            <span className="grid size-7 place-items-center rounded-md bg-zinc-900 text-white"><Scale className="size-4" /></span>
            Agency Review
            <span className="ml-1 hidden text-sm font-normal text-zinc-500 sm:inline">verified property facts</span>
          </a>
          {right}
        </div>
      </header>
      <main className="mx-auto max-w-7xl px-6 py-8">{children}</main>
    </div>
  )
}

function DevelopmentsList({ devs, onCreated }) {
  const [name, setName] = useState('')
  return (
    <>
      <div className="mb-6 flex flex-wrap items-end justify-between gap-4">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight">Developments</h1>
          <p className="mt-1 text-sm text-zinc-500">Review extracted facts, settle contradictions, then publish to the listing site and voice agent.</p>
        </div>
        <form className="flex gap-2" onSubmit={async (e) => { e.preventDefault(); if (!name) return; const d = await post('/developments', { name }); setName(''); onCreated(d.slug) }}>
          <input value={name} onChange={(e) => setName(e.target.value)} placeholder="New development name" className="h-9 w-56 rounded-md border border-zinc-200 bg-white px-3 text-sm outline-none focus:ring-2 focus:ring-zinc-300" />
          <Button type="submit" variant="outline">Add</Button>
        </form>
      </div>
      <div className="grid gap-4 md:grid-cols-2">
        {devs.map((d) => (
          <a key={d.slug} href={`#/d/${d.slug}`} className="group">
            <Card className="p-5 transition-shadow group-hover:shadow-md">
              <div className="flex items-start justify-between">
                <div className="flex items-center gap-3">
                  <span className="grid size-10 place-items-center rounded-lg bg-zinc-100"><Building2 className="size-5 text-zinc-600" /></span>
                  <div>
                    <div className="font-semibold">{d.name}</div>
                    <div className="text-xs text-zinc-500">{d.development_id} · {d.documents} documents</div>
                  </div>
                </div>
                <div className="flex items-center gap-2">
                  {d.published && <Badge tone="green"><Check className="size-3" />Published</Badge>}
                  <ChevronRight className="size-4 text-zinc-400 transition-transform group-hover:translate-x-0.5" />
                </div>
              </div>
              <div className="mt-5 grid grid-cols-3 gap-3 text-sm">
                <div><div className="text-xs text-zinc-500">Facts</div><div className="text-xl font-semibold tabular-nums">{d.facts}</div></div>
                <div><div className="text-xs text-zinc-500">Open contradictions</div><div className={cn('text-xl font-semibold tabular-nums', d.open_contradictions ? 'text-amber-600' : 'text-emerald-600')}>{d.open_contradictions}</div></div>
                <div>
                  <div className="text-xs text-zinc-500">Verified</div>
                  <div className="text-xl font-semibold tabular-nums">{d.verified_pct}%</div>
                  <div className="mt-1 h-1.5 rounded-full bg-zinc-100"><div className="h-1.5 rounded-full bg-emerald-500" style={{ width: `${d.verified_pct}%` }} /></div>
                </div>
              </div>
            </Card>
          </a>
        ))}
      </div>
    </>
  )
}

function DocumentsTab({ slug, docs, onUploaded, notify }) {
  const input = useRef()
  const [busy, setBusy] = useState(false)
  const upload = async (files) => {
    if (!files.length) return
    setBusy(true)
    const fd = new FormData()
    for (const f of files) fd.append('files', f)
    try {
      const r = await fetch(`/api/developments/${slug}/documents`, { method: 'POST', body: fd })
      const d = await r.json()
      if (!r.ok) throw new Error(d.detail)
      notify({ title: `Extracted ${d.uploaded.length} file(s)`, body: `${d.facts} facts, ${d.open_contradictions} open contradictions` })
      onUploaded()
    } catch (e) { notify({ error: true, title: 'Upload failed', body: e.message }) }
    setBusy(false)
    input.current.value = ''
  }
  return (
    <Card>
      <div className="flex items-center justify-between border-b border-zinc-100 p-4">
        <div><div className="font-semibold">Source documents</div><div className="text-xs text-zinc-500">Authority tier: 1 legal · 2 official register · 3 measured/signed · 4 developer · 5 agent particulars · 6 portal/CRM</div></div>
        <input ref={input} type="file" accept="application/pdf" multiple hidden onChange={(e) => upload([...e.target.files])} />
        <Button onClick={() => input.current.click()} disabled={busy}>{busy ? <><Loader2 className="size-4 animate-spin" />Running extractor…</> : <><Upload className="size-4" />Upload PDFs</>}</Button>
      </div>
      <table className="w-full text-sm">
        <thead className="bg-zinc-50 text-left text-xs text-zinc-500">
          <tr>{['Document', 'Type', 'Tier', 'Issuer', 'Date', 'Pages / text', 'Source', ''].map((h) => <th key={h} className="px-4 py-2.5 font-medium">{h}</th>)}</tr>
        </thead>
        <tbody>
          {docs.map((d) => (
            <tr key={d.doc_id} className="border-t border-zinc-100">
              <td className="px-4 py-3"><div className="font-medium">{d.doc_id}</div><div className="max-w-xs truncate text-xs text-zinc-500">{d.file_uri.split('/').pop()}</div></td>
              <td className="px-4 py-3">{d.doc_type.replace(/_/g, ' ')}</td>
              <td className="px-4 py-3"><Badge tone={TIER_TONE[d.authority_tier]}>Tier {d.authority_tier}</Badge></td>
              <td className="px-4 py-3"><div>{d.issuer_org}</div><div className="text-xs text-zinc-500">{(d.issuer_role || '').replace(/_/g, ' ')}</div></td>
              <td className="px-4 py-3 tabular-nums"><div>{d.doc_date || '—'}</div><div className="text-xs text-zinc-500">{(d.doc_date_source || '').replace(/_/g, ' ')}</div></td>
              <td className="px-4 py-3"><div>{d.page_count}</div><div className="text-xs text-zinc-500">{[...new Set(d.text_layer.pages)].join(', ').replace(/_/g, ' ')}</div></td>
              <td className="px-4 py-3"><Badge tone={d.source === 'real' ? 'green' : 'violet'}>{d.source}</Badge></td>
              <td className="px-4 py-3 text-right"><a className="text-xs font-medium text-zinc-600 underline-offset-2 hover:underline" href={`/api/developments/${slug}/documents/${d.doc_id}/file`} target="_blank" rel="noreferrer">Open PDF</a></td>
            </tr>
          ))}
          {!docs.length && <tr><td colSpan={8} className="p-10 text-center text-zinc-500">No documents yet. Upload PDFs to run the extractor.</td></tr>}
        </tbody>
      </table>
    </Card>
  )
}

function PagePreview({ slug, fact, docs, onClose }) {
  if (!fact) return null
  const doc = docs.find((d) => d.doc_id === fact.doc_id) || {}
  const src = `/api/developments/${slug}/documents/${fact.doc_id}/pages/${fact.page}.png?quote=${encodeURIComponent(fact.quote)}`
  return (
    <div className="fixed inset-0 z-40 flex justify-end bg-zinc-950/40" onClick={onClose}>
      <div className="flex h-full w-full max-w-3xl flex-col bg-white shadow-2xl" onClick={(e) => e.stopPropagation()}>
        <div className="flex items-start justify-between border-b border-zinc-200 p-4">
          <div>
            <div className="text-xs text-zinc-500">{doc.issuer_org} · {doc.doc_type?.replace(/_/g, ' ')} · tier {doc.authority_tier} · {doc.doc_date}</div>
            <div className="font-semibold">{fact.doc_id} — page {fact.page}</div>
          </div>
          <Button variant="ghost" size="sm" onClick={onClose}><X className="size-4" /></Button>
        </div>
        <div className="border-b border-zinc-200 bg-amber-50/60 p-4">
          <div className="mb-1 flex items-center gap-2 text-xs font-medium text-amber-800"><Quote className="size-3" />Verbatim quote ({fact.quote_source || 'text'}, match {fact.quote_match || 'exact'})</div>
          <div className="font-serif text-[15px] leading-relaxed">“{fact.quote}”</div>
          <div className="mt-2 text-sm"><span className="text-zinc-500">Extracted:</span> <span className="font-medium">{prettyField(fact.field)} = {fact.display_value}</span></div>
        </div>
        <div className="flex-1 overflow-auto bg-zinc-100 p-4"><img src={src} alt={`${fact.doc_id} page ${fact.page}`} className="mx-auto rounded border border-zinc-200 bg-white shadow" /></div>
      </div>
    </div>
  )
}

function FactsTab({ slug, facts, docs, refresh, reviewer, notify }) {
  const [preview, setPreview] = useState(null)
  const [filter, setFilter] = useState('all')
  const groups = useMemo(() => {
    const g = {}
    for (const f of facts) {
      if (filter !== 'all' && f.status !== filter) continue
      ;(g[f.unit_id] ||= {})
      ;(g[f.unit_id][f.field] ||= []).push(f)
    }
    return Object.entries(g).sort(([a], [b]) => a.localeCompare(b))
  }, [facts, filter])
  const toggle = async (f, accepted) => {
    try {
      await post(`/developments/${slug}/review-actions`, { action: accepted ? 'unreject_fact' : 'reject_fact', fact_id: f.fact_id, reviewer })
      refresh()
    } catch (e) { notify({ error: true, title: 'Action failed', body: e.message }) }
  }
  const counts = facts.reduce((a, f) => ({ ...a, [f.status]: (a[f.status] || 0) + 1 }), {})
  return (
    <>
      <div className="mb-3 flex flex-wrap gap-2">
        {['all', 'verified', 'pending', 'conflicting', 'superseded', 'rejected'].map((s) => (
          <button key={s} onClick={() => setFilter(s)} className={cn('cursor-pointer rounded-full border px-3 py-1 text-xs font-medium', filter === s ? 'border-zinc-900 bg-zinc-900 text-white' : 'border-zinc-200 bg-white text-zinc-600 hover:bg-zinc-50')}>
            {s} {s === 'all' ? facts.length : counts[s] || 0}
          </button>
        ))}
      </div>
      <div className="space-y-4">
        {groups.map(([unit, fields]) => (
          <Card key={unit} className="overflow-hidden">
            <div className="flex items-center gap-2 border-b border-zinc-100 bg-zinc-50/70 px-4 py-2.5">
              <Layers className="size-4 text-zinc-500" /><span className="font-semibold capitalize">{unitLabel(unit)}</span>
              <span className="text-xs text-zinc-500">{unit}</span>
            </div>
            <table className="w-full text-sm">
              <thead className="text-left text-xs text-zinc-500">
                <tr>{['Field', 'Value', 'sq ft / sq m', 'Basis', 'Scope', 'Source', 'Quote', 'Status', 'Accepted'].map((h) => <th key={h} className="px-3 py-2 font-medium">{h}</th>)}</tr>
              </thead>
              <tbody>
                {Object.entries(fields).map(([field, fs]) => fs.map((f, i) => (
                  <tr key={f.fact_id} onClick={() => setPreview(f)} className={cn('cursor-pointer border-t border-zinc-100 hover:bg-zinc-50', f.review_status === 'rejected' && 'opacity-50')}>
                    <td className="px-3 py-2.5 align-top">{i === 0 && <div className="font-medium">{prettyField(field)}</div>}{qualText(f.qualifier) && <div className="text-xs text-zinc-500">{qualText(f.qualifier)}</div>}</td>
                    <td className="px-3 py-2.5 align-top font-medium">{f.display_value}{f.doc_error && <Badge tone="red" className="ml-1">doc error</Badge>}</td>
                    <td className="px-3 py-2.5 align-top tabular-nums text-zinc-600">{f.normalised ? `${f.normalised.sq_ft.toLocaleString()} / ${f.normalised.sq_m}` : '—'}</td>
                    <td className="px-3 py-2.5 align-top">{f.qualifier?.basis ? <Badge tone={f.qualifier.basis === 'unspecified' ? 'amber' : 'outline'}>{f.qualifier.basis}</Badge> : '—'}</td>
                    <td className="px-3 py-2.5 align-top text-xs text-zinc-600">{f.scope}{f.qualifier?.scope ? ` · ${String(f.qualifier.scope).replace(/_/g, ' ')}` : ''}</td>
                    <td className="px-3 py-2.5 align-top whitespace-nowrap"><div className="text-xs font-medium">{f.doc_id}</div><div className="text-xs text-zinc-500">p{f.page} · tier {f.authority_tier}</div></td>
                    <td className="max-w-xs px-3 py-2.5 align-top"><div className="line-clamp-2 font-serif text-[13px] text-zinc-700">“{f.quote}”</div></td>
                    <td className="px-3 py-2.5 align-top"><Badge tone={STATUS_TONE[f.status]}>{f.status}</Badge>{f.open_contradictions?.length > 0 && <div className="mt-1 text-[11px] text-zinc-500">{f.open_contradictions.join(', ')}</div>}</td>
                    <td className="px-3 py-2.5 align-top"><Switch checked={f.review_status !== 'rejected'} onChange={(v) => toggle(f, v)} /></td>
                  </tr>
                )))}
              </tbody>
            </table>
          </Card>
        ))}
      </div>
      <PagePreview slug={slug} fact={preview} docs={docs} onClose={() => setPreview(null)} />
    </>
  )
}

function ContradictionCard({ c, slug, reviewer, refresh, notify, factsById, onPreview }) {
  const [busy, setBusy] = useState(false)
  const act = async (body) => {
    setBusy(true)
    try {
      await post(`/developments/${slug}/review-actions`, { contradiction_id: c.contradiction_id, reviewer, ...body })
      notify({ title: `${c.label || 'Contradiction'} ${body.action === 'reopen_contradiction' ? 'reopened' : 'resolved'}` })
      refresh()
    } catch (e) { notify({ error: true, title: 'Action failed', body: e.message }) }
    setBusy(false)
  }
  const open = c.status === 'open'
  const rec = c.recommended
  const winner = c.resolved_fact_id
  return (
    <Card className={cn('overflow-hidden', !open && 'opacity-90')}>
      <div className="flex flex-wrap items-start justify-between gap-3 border-b border-zinc-100 p-4">
        <div>
          <div className="flex flex-wrap items-center gap-2">
            {c.label && <Badge tone="default">{c.label}</Badge>}
            <span className="font-semibold">{c.field_label}</span>
            <span className="text-sm capitalize text-zinc-500">· {unitLabel(c.unit_id)}</span>
            {c.requires_human && open && <Badge tone="amber">needs sign-off</Badge>}
          </div>
          <div className="mt-1 text-sm text-zinc-700">{c.type_plain}</div>
          <div className="mt-0.5 text-xs text-zinc-400">{c.type.replace(/_/g, ' ')}{c.downstream_action ? ` · next: ${c.downstream_action.replace(/_/g, ' ')}` : ''}</div>
        </div>
        {open ? <Badge tone="amber"><AlertTriangle className="size-3" />Open</Badge>
          : <div className="flex items-center gap-2"><Badge tone="green"><CheckCircle2 className="size-3" />Resolved · {String(c.resolution).replace(/_/g, ' ')}</Badge>
            {c.resolved_by && <span className="text-xs text-zinc-500">{c.resolved_by}</span>}
            {c.resolved_by && <Button variant="ghost" size="sm" onClick={() => act({ action: 'reopen_contradiction' })}><RotateCcw className="size-3" />Reopen</Button>}</div>}
      </div>
      <div className="grid gap-3 p-4 md:grid-cols-2 xl:grid-cols-3">
        {c.candidates.map((x) => {
          const isRec = x.fact_id === rec.fact_id
          const isWin = winner && factsById[x.fact_id]?.status === 'verified'
          const lost = !open && winner && !isWin
          return (
            <div key={x.fact_id} className={cn('flex flex-col rounded-lg border p-3', isWin ? 'border-emerald-300 bg-emerald-50/50' : isRec && open ? 'border-zinc-900 ring-1 ring-zinc-900' : 'border-zinc-200', lost && 'opacity-50')}>
              <div className="flex items-start justify-between gap-2">
                <div className="text-lg font-semibold leading-tight">{x.value}</div>
                {isRec && <Badge tone={open ? 'default' : 'outline'}>Recommended</Badge>}
              </div>
              <div className="mt-2 flex flex-wrap gap-1.5">
                <Badge tone={TIER_TONE[x.authority_tier]}>Tier {x.authority_tier} · {x.tier_label}</Badge>
                <Badge tone="outline">{x.as_at || 'undated'}</Badge>
                {x.doc_error && <Badge tone="red">doc error</Badge>}
                <Badge tone="zinc" className="capitalize">{unitLabel(x.unit_id)} · {x.scope}</Badge>
              </div>
              <button onClick={() => onPreview(factsById[x.fact_id])} className="mt-2 flex-1 cursor-pointer rounded-md bg-zinc-50 p-2 text-left font-serif text-[13px] text-zinc-700 hover:bg-zinc-100">“{x.quote}”</button>
              <div className="mt-2 flex items-center justify-between text-xs text-zinc-500">
                <span>{x.issuer} · {x.doc_id} p{x.page}</span>
                {open && <Button size="sm" variant="outline" disabled={busy} onClick={() => act({ action: 'resolve_contradiction', resolution: 'choose_fact', chosen_fact_id: x.fact_id })}>Choose this value</Button>}
              </div>
            </div>
          )
        })}
      </div>
      {open && (
        <div className="flex flex-wrap items-center justify-between gap-3 border-t border-zinc-100 bg-zinc-50/70 p-4">
          <div className="text-sm"><span className="font-medium">Recommendation: </span>{rec.value ? <span className="font-medium">{rec.value}. </span> : null}<span className="text-zinc-600">{rec.reason}</span></div>
          <div className="flex gap-2">
            <Button variant="outline" disabled={busy} onClick={() => act({ action: 'resolve_contradiction', resolution: 'keep_both_scoped' })}><Layers className="size-4" />Keep both at their scopes</Button>
            {rec.fact_id && <Button variant="success" disabled={busy} onClick={() => act({ action: 'resolve_contradiction', resolution: 'accept_recommendation' })}><Check className="size-4" />Accept recommendation</Button>}
          </div>
        </div>
      )}
    </Card>
  )
}

function ContradictionsTab({ slug, contradictions, facts, docs, ...rest }) {
  const [preview, setPreview] = useState(null)
  const factsById = useMemo(() => Object.fromEntries(facts.map((f) => [f.fact_id, f])), [facts])
  const sorted = [...contradictions].sort((a, b) => (a.status !== b.status ? (a.status === 'open' ? -1 : 1) : (a.label || 'Z').localeCompare(b.label || 'Z')))
  return (
    <div className="space-y-4">
      {sorted.map((c) => <ContradictionCard key={c.contradiction_id} c={c} slug={slug} factsById={factsById} onPreview={setPreview} {...rest} />)}
      {!contradictions.length && <Card className="p-10 text-center text-zinc-500">No contradictions.</Card>}
      <PagePreview slug={slug} fact={preview} docs={docs} onClose={() => setPreview(null)} />
    </div>
  )
}

function PublishTab({ slug, notify, refresh, version }) {
  const [listing, setListing] = useState(null)
  const [voice, setVoice] = useState(null)
  const [busy, setBusy] = useState(false)
  useEffect(() => {
    api(`/developments/${slug}/listing`).then(setListing)
    api(`/developments/${slug}/voice-agent`).then(setVoice)
  }, [slug, version])
  if (!listing || !voice) return <Loader2 className="size-5 animate-spin text-zinc-400" />
  const publish = async () => {
    setBusy(true)
    try {
      const r = await post(`/developments/${slug}/publish`, {})
      notify({ title: 'Published', body: `${r.listing_path} and ${r.voice_path}` })
      refresh()
    } catch (e) { notify({ error: true, title: 'Publish failed', body: e.message }) }
    setBusy(false)
  }
  const nVerified = listing.units.flatMap((u) => u.fields).filter((f) => f.verification_status === 'verified').length
  const nPending = listing.units.flatMap((u) => u.fields).length - nVerified
  return (
    <div className="space-y-4">
      <Card className="flex flex-wrap items-center justify-between gap-3 p-4">
        <div>
          <div className="font-semibold">Ready to publish</div>
          <div className="text-sm text-zinc-500">{nVerified} verified listing fields · {nPending} pending verification (hidden from buyers) · {voice.do_not_state.length} topics the voice agent won't state</div>
        </div>
        <div className="flex gap-2">
          <Button variant="outline" onClick={() => download(`${slug}-05_listing.json`, listing)}><Download className="size-4" />Listing JSON</Button>
          <Button variant="outline" onClick={() => download(`${slug}-04_voice_agent.json`, voice)}><Download className="size-4" />Voice JSON</Button>
          <Button onClick={publish} disabled={busy}>{busy ? <Loader2 className="size-4 animate-spin" /> : <Send className="size-4" />}Publish</Button>
        </div>
      </Card>
      <div className="grid gap-4 lg:grid-cols-5">
        <Card className="lg:col-span-3">
          <div className="flex items-center gap-2 border-b border-zinc-100 p-4"><Building2 className="size-4" /><span className="font-semibold">Listing preview</span><span className="text-xs text-zinc-500">05_listing</span></div>
          <div className="divide-y divide-zinc-100">
            {listing.units.map((u) => (
              <div key={u.unit_id} className="p-4">
                <div className="mb-2 flex items-center gap-2"><span className="font-medium capitalize">{unitLabel(u.unit_id)}</span>{u.primary && <Badge tone="default">Main listing</Badge>}</div>
                <dl className="grid grid-cols-1 gap-x-6 gap-y-1.5 sm:grid-cols-2">
                  {u.fields.map((f) => (
                    <div key={f.label} className="flex items-baseline justify-between gap-3 border-b border-dashed border-zinc-100 py-1">
                      <dt className="text-sm text-zinc-500">{f.label}</dt>
                      {f.verification_status === 'verified'
                        ? <dd className="flex items-center gap-1.5 text-right text-sm font-medium"><CheckCircle2 className="size-3.5 shrink-0 text-emerald-600" />{f.value}</dd>
                        : <dd className="text-right text-sm italic text-zinc-400">pending verification{f.open_contradictions?.length ? ` (${f.open_contradictions.join(', ')})` : ''}</dd>}
                    </div>
                  ))}
                </dl>
              </div>
            ))}
          </div>
        </Card>
        <Card className="lg:col-span-2">
          <div className="flex items-center gap-2 border-b border-zinc-100 p-4"><Mic className="size-4" /><span className="font-semibold">Voice agent payload</span><span className="text-xs text-zinc-500">04_voice_agent</span></div>
          <div className="max-h-[640px] space-y-4 overflow-auto p-4">
            {voice.units.map((u) => (
              <div key={u.unit_id}>
                <div className="mb-1.5 text-xs font-medium uppercase tracking-wide text-zinc-500">{unitLabel(u.unit_id)}</div>
                <ul className="space-y-1.5">
                  {u.verified_facts.map((f) => (
                    <li key={f.fact_id} className="rounded-md border border-zinc-100 p-2 text-sm">
                      <div><span className="text-zinc-500">{prettyField(f.field)}:</span> <span className="font-medium">{f.statement}</span></div>
                      <div className="text-xs text-zinc-400">{f.citation.issuer} · {f.citation.doc_id} p{f.citation.page} · as at {f.citation.as_at}</div>
                    </li>
                  ))}
                </ul>
              </div>
            ))}
            <div>
              <div className="mb-1.5 flex items-center gap-1 text-xs font-medium uppercase tracking-wide text-red-600"><X className="size-3" />Do not state</div>
              <ul className="space-y-1.5">
                {voice.do_not_state.map((d, i) => (
                  <li key={i} className="rounded-md border border-red-100 bg-red-50/50 p-2 text-sm">
                    <span className="font-medium">{prettyField(d.field)}</span> <span className="capitalize text-zinc-500">· {unitLabel(d.unit_id)}</span>
                    <div className="text-xs text-zinc-500">{d.reason}{d.contradictions.length ? ` · ${d.contradictions.join(', ')}` : ''}</div>
                  </li>
                ))}
                {!voice.do_not_state.length && <li className="text-sm text-zinc-500">Nothing blocked.</li>}
              </ul>
            </div>
          </div>
        </Card>
      </div>
    </div>
  )
}

function Development({ slug, tab, reviewer, notify }) {
  const [dev, setDev] = useState(null)
  const [docs, setDocs] = useState([])
  const [facts, setFacts] = useState([])
  const [cons, setCons] = useState([])
  const [version, setVersion] = useState(0)
  const load = useCallback(async () => {
    const [d, dc, f, c] = await Promise.all([api(`/developments/${slug}`), api(`/developments/${slug}/documents`), api(`/developments/${slug}/facts`), api(`/developments/${slug}/contradictions`)])
    setDev(d); setDocs(dc); setFacts(f); setCons(c); setVersion((v) => v + 1)
  }, [slug])
  useEffect(() => { load() }, [load])
  if (!dev) return <Loader2 className="size-5 animate-spin text-zinc-400" />
  const setTab = (t) => { window.location.hash = `/d/${slug}/${t}` }
  const common = { slug, reviewer, notify, refresh: load }
  return (
    <>
      <a href="#" className="mb-4 inline-flex items-center gap-1 text-sm text-zinc-500 hover:text-zinc-900"><ArrowLeft className="size-4" />All developments</a>
      <div className="mb-6 flex flex-wrap items-end justify-between gap-4">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight">{dev.name}</h1>
          <p className="mt-1 text-sm text-zinc-500">{dev.development_id} · main unit <span className="capitalize">{unitLabel(dev.primary_unit_id)}</span></p>
        </div>
        {dev.published && <Badge tone="green"><Check className="size-3" />Published</Badge>}
      </div>
      <div className="mb-6 grid grid-cols-2 gap-4 md:grid-cols-4">
        <Stat label="Documents" value={dev.documents} />
        <Stat label="Facts" value={dev.facts} hint={`${dev.rejected_facts} rejected`} />
        <Stat label="Open contradictions" value={dev.open_contradictions} hint={`of ${dev.contradictions}`} tone={dev.open_contradictions ? 'text-amber-600' : 'text-emerald-600'} />
        <Stat label="Verified" value={`${dev.verified_pct}%`} hint="of accepted facts" />
      </div>
      <div className="mb-4">
        <Tabs value={tab} onChange={setTab} tabs={[
          { value: 'documents', label: 'Documents', icon: <FileText className="size-4" />, count: docs.length },
          { value: 'facts', label: 'Facts', icon: <Layers className="size-4" />, count: facts.length },
          { value: 'contradictions', label: 'Contradictions', icon: <AlertTriangle className="size-4" />, count: dev.open_contradictions },
          { value: 'publish', label: 'Publish', icon: <Send className="size-4" /> },
        ]} />
      </div>
      {tab === 'documents' && <DocumentsTab {...common} docs={docs} onUploaded={load} />}
      {tab === 'facts' && <FactsTab {...common} facts={facts} docs={docs} />}
      {tab === 'contradictions' && <ContradictionsTab {...common} contradictions={cons} facts={facts} docs={docs} />}
      {tab === 'publish' && <PublishTab {...common} version={version} />}
    </>
  )
}

export default function App() {
  const hash = useHash()
  const [devs, setDevs] = useState([])
  const [toast, setToast] = useState(null)
  const [reviewer, setReviewer] = useState(localStorage.getItem('reviewer') || 'agency-reviewer')
  useEffect(() => { localStorage.setItem('reviewer', reviewer) }, [reviewer])
  const m = hash.match(/^\/d\/([a-z0-9-]+)(?:\/(\w+))?/)
  useEffect(() => { if (!m) api('/developments').then(setDevs) }, [hash]) // eslint-disable-line react-hooks/exhaustive-deps
  const notify = useCallback((t) => setToast(t), [])
  return (
    <Shell right={<label className="flex items-center gap-2 text-xs text-zinc-500">Reviewer<input value={reviewer} onChange={(e) => setReviewer(e.target.value)} className="h-8 w-40 rounded-md border border-zinc-200 bg-white px-2 text-sm text-zinc-900 outline-none focus:ring-2 focus:ring-zinc-300" /></label>}>
      {m ? <Development key={m[1]} slug={m[1]} tab={m[2] || 'documents'} reviewer={reviewer} notify={notify} />
        : <DevelopmentsList devs={devs} onCreated={(s) => { window.location.hash = `/d/${s}` }} />}
      <Toast toast={toast} onClose={() => setToast(null)} />
    </Shell>
  )
}
