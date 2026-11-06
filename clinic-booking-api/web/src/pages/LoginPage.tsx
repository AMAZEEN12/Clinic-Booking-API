import { useRef, useState, type FormEvent } from "react"
import { Navigate, useLocation, useNavigate } from "react-router-dom"
import { Button } from "@/components/ui/button"
import { FormField } from "@/components/ui/form-field"
import { Input } from "@/components/ui/input"
import { Panel } from "@/components/ui/panel"
import { useAuth } from "@/hooks/useAuth"
import { usePageTitle } from "@/hooks/usePageTitle"
import { login } from "@/services/api"
import { describeError } from "@/utils/messages"
import { homeFor } from "@/utils/routes"

/** Where to go after signing in: the page the person was sent away from, if their role may open it. */
function readFrom(state: unknown): string | undefined {
    if (state && typeof state === "object" && "from" in state && typeof state.from === "string") return state.from
    return undefined
}

export function LoginPage() {
    usePageTitle("Sign in")
    const session = useAuth()
    const navigate = useNavigate()
    const location = useLocation()
    const [email, setEmail] = useState("")
    const [password, setPassword] = useState("")
    const [emailError, setEmailError] = useState<string | undefined>()
    const [passwordError, setPasswordError] = useState<string | undefined>()
    const [failure, setFailure] = useState<string | undefined>()
    const [busy, setBusy] = useState(false)
    const emailRef = useRef<HTMLInputElement>(null)
    const passwordRef = useRef<HTMLInputElement>(null)

    // Already signed in: nothing to do here.
    if (session) return <Navigate to={homeFor(session.role)} replace />

    async function handleSubmit(event: FormEvent) {
        event.preventDefault()
        if (busy) return
        const missingEmail = email.trim() ? undefined : "Enter your email."
        const missingPassword = password ? undefined : "Enter your password."
        setEmailError(missingEmail)
        setPasswordError(missingPassword)
        setFailure(undefined)
        if (missingEmail) return emailRef.current?.focus()
        if (missingPassword) return passwordRef.current?.focus()

        setBusy(true)
        try {
            const signedIn = await login(email.trim(), password)
            // RequireRole sends the person home if the page they came from is not for their role.
            navigate(readFrom(location.state) ?? homeFor(signedIn.role), { replace: true })
        } catch (error) {
            setFailure(describeError(error, "login"))
            setBusy(false)
        }
    }

    return (
        <div className="mx-auto max-w-md space-y-6">
            <div className="space-y-1">
                <h1 className="font-heading text-3xl font-extrabold sm:text-4xl">Sign in</h1>
                <p className="text-[var(--color-text-muted)]">
                    Patients can book and manage appointments. Clinic staff see the daily dashboard.
                </p>
            </div>

            <Panel>
                <form onSubmit={handleSubmit} noValidate className="space-y-4">
                    <FormField label="Email" required error={emailError}>
                        {(field) => (
                            <Input
                                {...field}
                                ref={emailRef}
                                type="email"
                                value={email}
                                autoComplete="username"
                                autoCapitalize="none"
                                onChange={(e) => setEmail(e.target.value)}
                            />
                        )}
                    </FormField>
                    <FormField label="Password" required error={passwordError}>
                        {(field) => (
                            <Input
                                {...field}
                                ref={passwordRef}
                                type="password"
                                value={password}
                                autoComplete="current-password"
                                onChange={(e) => setPassword(e.target.value)}
                            />
                        )}
                    </FormField>

                    <div aria-live="polite">
                        {failure && (
                            <p role="alert" className="text-sm font-medium text-[var(--color-danger)]">
                                <span aria-hidden="true">! </span>
                                {failure}
                            </p>
                        )}
                    </div>

                    <Button type="submit" size="lg" className="w-full" loading={busy}>
                        Sign in
                    </Button>
                </form>
            </Panel>
        </div>
    )
}
