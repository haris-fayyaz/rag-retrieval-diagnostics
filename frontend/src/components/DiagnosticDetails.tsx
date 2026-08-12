import Disclosure from './Disclosure'

function Row({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex items-baseline justify-between gap-4 py-1.5">
      <span className="text-[12.5px] text-muted-foreground">{label}</span>
      <span className="truncate font-mono text-[12px] text-foreground">{value}</span>
    </div>
  )
}

function formatDuration(ms: number) {
  return ms >= 1000 ? `${(ms / 1000).toFixed(2)} s` : `${Math.round(ms)} ms`
}

export default function DiagnosticDetails({
  retrievalMs,
  generationMs,
  requestId,
  extra,
}: {
  retrievalMs?: number
  generationMs?: number
  requestId: string
  extra?: { label: string; value: string }[]
}) {
  return (
    <Disclosure label="Details">
      <div className="flex flex-col divide-y divide-border">
        {retrievalMs !== undefined && <Row label="Retrieval" value={formatDuration(retrievalMs)} />}
        {generationMs !== undefined && (
          <Row label="Generation" value={formatDuration(generationMs)} />
        )}
        {extra?.map((item) => <Row key={item.label} label={item.label} value={item.value} />)}
        <Row label="Request ID" value={requestId} />
      </div>
    </Disclosure>
  )
}
