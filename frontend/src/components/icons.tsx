/** Hairline icon set drawn on a 16px grid to match the interface stroke weight. */
import type { SVGProps } from 'react'

const base = (props: SVGProps<SVGSVGElement>) => ({
  width: 16,
  height: 16,
  viewBox: '0 0 16 16',
  fill: 'none',
  stroke: 'currentColor',
  strokeWidth: 1.4,
  strokeLinecap: 'round' as const,
  strokeLinejoin: 'round' as const,
  ...props,
})

export const PlusIcon = (p: SVGProps<SVGSVGElement>) => (
  <svg {...base(p)}>
    <path d="M8 3.5v9M3.5 8h9" />
  </svg>
)

export const ArrowUpIcon = (p: SVGProps<SVGSVGElement>) => (
  <svg {...base(p)}>
    <path d="M8 12.5v-9M4 7.5 8 3.5l4 4" />
  </svg>
)

export const ChevronIcon = (p: SVGProps<SVGSVGElement>) => (
  <svg {...base(p)}>
    <path d="m5.5 6.5 2.5 3 2.5-3" />
  </svg>
)

export const DocumentIcon = (p: SVGProps<SVGSVGElement>) => (
  <svg {...base(p)}>
    <path d="M4 2.5h5l3 3v8H4z" />
    <path d="M9 2.5v3h3" />
  </svg>
)

export const ChatIcon = (p: SVGProps<SVGSVGElement>) => (
  <svg {...base(p)}>
    <path d="M2.5 4.5A1.5 1.5 0 0 1 4 3h8a1.5 1.5 0 0 1 1.5 1.5v5A1.5 1.5 0 0 1 12 11H6.5L3.5 13.5V11H4a1.5 1.5 0 0 1-1.5-1.5z" />
  </svg>
)

export const AgentIcon = (p: SVGProps<SVGSVGElement>) => (
  <svg {...base(p)}>
    <path d="M8 2.5v3M4 8.5h8M4 8.5v2.5a1 1 0 0 0 1 1h6a1 1 0 0 0 1-1V8.5" />
    <path d="M5.5 5.5h5a1.5 1.5 0 0 1 1.5 1.5v1.5H4V7a1.5 1.5 0 0 1 1.5-1.5Z" />
  </svg>
)

export const CheckIcon = (p: SVGProps<SVGSVGElement>) => (
  <svg {...base(p)}>
    <path d="m3.5 8.5 3 3 6-7" />
  </svg>
)

export const DotsIcon = (p: SVGProps<SVGSVGElement>) => (
  <svg {...base(p)} strokeWidth={1.8}>
    <path d="M4 8h.01M8 8h.01M12 8h.01" />
  </svg>
)

export const CloseIcon = (p: SVGProps<SVGSVGElement>) => (
  <svg {...base(p)}>
    <path d="m4 4 8 8M12 4l-8 8" />
  </svg>
)

export const LogoutIcon = (p: SVGProps<SVGSVGElement>) => (
  <svg {...base(p)}>
    <path d="M6 13.5H4a1 1 0 0 1-1-1v-9a1 1 0 0 1 1-1h2" />
    <path d="M10 11l3-3-3-3M13 8H6.5" />
  </svg>
)

/** Application mark: three stacked rules of decreasing width — retrieval
 *  narrowing to an answer. Deliberately geometric, no AI iconography. */
export const AppMark = ({ className = '' }: { className?: string }) => (
  <svg width="22" height="22" viewBox="0 0 22 22" className={className} aria-hidden="true">
    <rect x="1" y="1" width="20" height="20" rx="4" fill="currentColor" />
    <path d="M6 7.5h10M6 11h7M6 14.5h4" stroke="#fff" strokeWidth="1.4" strokeLinecap="round" />
  </svg>
)
