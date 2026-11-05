import { useRef, useState, type FormEvent } from "react"
import { useNavigate } from "react-router-dom"
import { Button } from "@/components/ui/button"
import { FormField } from "@/components/ui/form-field"
import { Input } from "@/components/ui/input"
import { Panel } from "@/components/ui/panel"
import { usePageTitle } from "@/hooks/usePageTitle"
import { routes } from "@/utils/routes"

export function FindPage() {
    usePageTitle("Find a booking")
    const navigate = useNavigate()
    const [id, setId] = useState("")
    const [error, setError] = useState<string | undefined>()
    const inputRef = useRef<HTMLInputElement>(null)

    function handleSubmit(event: FormEvent) {
        event.preventDefault()
        const clean = id.trim()
        if (!clean) {
            setError("Enter your booking ID.")
            inputRef.current?.focus()
            return
        }
        navigate(routes.booking(clean))
    }

    return (
        <div className="mx-auto max-w-xl space-y-6">
            <h1 className="font-heading text-3xl font-extrabold sm:text-4xl">Find a booking</h1>
            <Panel>
                <form onSubmit={handleSubmit} noValidate className="space-y-4">
                    <FormField
                        label="Booking ID"
                        required
                        hint="It starts with bk_ and was shown when you booked."
                        error={error}
                    >
                        {(field) => (
                            <Input
                                {...field}
                                ref={inputRef}
                                value={id}
                                autoComplete="off"
                                autoCapitalize="none"
                                spellCheck={false}
                                onChange={(e) => setId(e.target.value)}
                            />
                        )}
                    </FormField>
                    <Button type="submit" size="lg" className="w-full sm:w-auto">
                        Find booking
                    </Button>
                </form>
            </Panel>
        </div>
    )
}