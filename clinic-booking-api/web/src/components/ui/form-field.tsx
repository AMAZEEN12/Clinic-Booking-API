// FormField: label + hint + error wrapper for any form control.
// children is a function that receives the props to spread onto the control:
//   <FormField label="Name" error={errors.name} required>{(field) => <Input {...field} />}</FormField>
// It wires up: label tied to the control, hint and error linked with aria-describedby,
// aria-invalid on error, aria-required with a visual * hidden from screen readers.

import { useId, type ReactNode } from "react"
import { cn } from "../../lib/cn"

export type FieldControlProps = {
    id: string
    "aria-describedby"?: string
    "aria-invalid"?: true
    "aria-required"?: true
}

export type FormFieldProps = {
    label: string
    hint?: string
    error?: string
    required?: boolean
    id?: string
    className?: string
    children: (field: FieldControlProps) => ReactNode
}

export function FormField({ label, hint, error, required = false, id, className, children }: FormFieldProps) {
    const generatedId = useId()
    const controlId = id ?? generatedId
    const hintId = `${controlId}-hint`
    const errorId = `${controlId}-error`

    const describedBy = [hint ? hintId : null, error ? errorId : null].filter(Boolean).join(" ")

    const field: FieldControlProps = {
        id: controlId,
        ...(describedBy && { "aria-describedby": describedBy }),
        ...(error && { "aria-invalid": true as const }),
        ...(required && { "aria-required": true as const }),
    }

    return (
        <div className={cn("flex flex-col gap-1.5 font-[family-name:var(--font-sans)]", className)}>
            <label htmlFor={controlId} className="text-sm font-medium text-[var(--color-text)]">
                {label}
                {required && (
                    <span aria-hidden="true" className="ml-0.5 text-[var(--color-danger)]">
            *
          </span>
                )}
            </label>

            {hint && (
                <p id={hintId} className="text-sm text-[var(--color-text-muted)]">
                    {hint}
                </p>
            )}

            {children(field)}

            {/* The error is text, never colour alone. */}
            {error && (
                <p id={errorId} className="text-sm font-medium text-[var(--color-danger)]">
                    <span aria-hidden="true">! </span>
                    {error}
                </p>
            )}
        </div>
    )
}