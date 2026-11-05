// Error state: plain message plus a "Try again" button, announced with role="alert".
// title and description are plain strings: map the failure to words before it gets here,
// so raw codes and stack traces never reach the patient.

import { forwardRef, type HTMLAttributes, type MouseEvent, type ReactNode } from "react"
import { Button } from "./button"
import { cn } from "../../lib/cn"

export type ErrorStateHeadingLevel = "h2" | "h3" | "h4" | "h5" | "h6"

export type ErrorStateProps = Omit<HTMLAttributes<HTMLDivElement>, "title" | "children" | "role"> & {
    title: string
    description: string
    icon?: ReactNode
    headingLevel?: ErrorStateHeadingLevel
    onRetry?: (event: MouseEvent<HTMLButtonElement>) => void
    retryLabel?: string
    retrying?: boolean
}

export const ErrorState = forwardRef<HTMLDivElement, ErrorStateProps>(function ErrorState(
    {
        title,
        description,
        icon,
        headingLevel = "h2",
        onRetry,
        retryLabel = "Try again",
        retrying = false,
        className,
        ...rest
    },
    ref,
) {
    const Heading = headingLevel

    return (
        <div
            ref={ref}
            className={cn(
                "flex w-full min-w-0 flex-col items-center gap-3 px-4 py-10 text-center",
                "font-[family-name:var(--font-sans)] text-[var(--color-text)]",
                "break-words [overflow-wrap:anywhere]",
                className,
            )}
            {...rest}
            role="alert"
        >
            {icon && (
                <span className="inline-flex shrink-0 text-[var(--color-danger)]" aria-hidden="true">
          {icon}
        </span>
            )}
            <Heading className="max-w-full text-lg font-semibold leading-snug text-[var(--color-danger)]">{title}</Heading>
            <p className="max-w-prose text-sm leading-6 text-[var(--color-text-muted)]">{description}</p>
            {onRetry && (
                <Button className="mt-2 max-w-full" loading={retrying} onClick={onRetry}>
                    {retryLabel}
                </Button>
            )}
        </div>
    )
})

ErrorState.displayName = "ErrorState"