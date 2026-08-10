export default function UserMessage({ text }: { text: string }) {
  return (
    <div className="animate-slide-up flex justify-end">
      <div className="max-w-[78%] rounded-lg rounded-tr-[3px] border border-border bg-secondary px-4 py-2.5 text-[15px] leading-relaxed text-foreground">
        {text}
      </div>
    </div>
  )
}
