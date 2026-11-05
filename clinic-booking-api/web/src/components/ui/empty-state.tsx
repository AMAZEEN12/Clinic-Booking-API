// Empty state: a title (real heading), one line of explanation, optional action button.

import { forwardRef, type HTMLAttributes, type MouseEvent, type ReactNode } from "react"
import { Button } from "./button"
import { cn } from "../../lib/cn"

export type EmptyStateHeadingLevel = "h2" | "h3" | "h4" | "h5" | "h6"

export type EmptyStateAction = {
    label: string
    onClick: (event: MouseEvent<HTMLButtonElement>) => void
}

export type EmptyStateProps = Omit<HTMLAttributes<HTMLDivElement>, "title" | "children"> & {
    title: ReactNode
    description: ReactNode
    icon?: ReactNode
    action?: EmptyStateAction
    headingLevel?: EmptyStateHeadingLevel
}

export const EmptyState = forwardRef<HTMLDivElement, EmptyStateProps>(function EmptyState(
    { title, description, icon, action, headingLevel = "h2", className, ...rest },
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
        >
            {icon && (
                <span className="inline-flex shrink-0 text-[var(--color-text-muted)]" aria-hidden="true">
          {icon}
        </span>
            )}
            <Heading className="max-w-full text-lg font-semibold leading-snug text-[var(--color-text)]">{title}</Heading>
            <p className="max-w-prose text-sm leading-6 text-[var(--color-text-muted)]">{description}</p>
            {action && (
                <Button className="mt-2 max-w-full" onClick={action.onClick}>
                    {action.label}
                </Button>
            )}
        </div>
    )
})

EmptyState.displayName = "EmptyState"