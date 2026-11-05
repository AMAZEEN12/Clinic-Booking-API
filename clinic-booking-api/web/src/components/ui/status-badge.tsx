// Status badge: the status is always written out as text. Colour and icon are extras.

import { forwardRef, type HTMLAttributes, type ReactNode } from "react"
import { cn } from "../../lib/cn"

export type StatusBadgeTone = "neutral" | "info" | "success" | "warning" | "danger"

export type StatusBadgeProps = HTMLAttributes<HTMLSpanElement> & {
    tone?: StatusBadgeTone
    icon?: ReactNode
    children: ReactNode
}

const toneClasses: Record<StatusBadgeTone, string> = {
    neutral: "bg-[var(--color-surface)] text-[var(--color-text)] border-[var(--color-border-input)]",
    info: "bg-[var(--color-primary)] text-[var(--color-on-primary)] border-transparent",
    success: "bg-[var(--color-success)] text-[var(--color-on-success)] border-transparent",
    warning: "bg-[var(--color-warning)] text-[var(--color-on-warning)] border-transparent",
    danger: "bg-[var(--color-danger)] text-[var(--color-on-danger)] border-transparent",
}

export const StatusBadge = forwardRef<HTMLSpanElement, StatusBadgeProps>(function StatusBadge(
    { tone = "neutral", icon, className, children, ...rest },
    ref,
) {
    return (
        <span
            ref={ref}
            className={cn(
                "inline-flex max-w-full min-w-0 items-center gap-1 align-middle",
                "rounded-[var(--radius-sm)] border px-2 py-0.5",
                "text-sm font-medium leading-5 font-[family-name:var(--font-sans)]",
                "whitespace-normal break-words [overflow-wrap:anywhere]",
                toneClasses[tone],
                className,
            )}
            {...rest}
        >
      {icon && (
          <span className="inline-flex shrink-0" aria-hidden="true">
          {icon}
        </span>
      )}
            <span className="min-w-0">{children}</span>
    </span>
    )
})

StatusBadge.displayName = "StatusBadge"