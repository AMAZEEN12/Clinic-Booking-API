import { createRoot } from "react-dom/client"
import "./index.css"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { FormField } from "@/components/ui/form-field"
import { Panel } from "@/components/ui/panel"
import { EmptyState } from "@/components/ui/empty-state"
import { ErrorState } from "@/components/ui/error-state"
import { StatusBadge } from "@/components/shared/status-badge"
import { formatClinicDate, formatClinicTime } from "@/utils/clinicTime"
import { validateDetails } from "@/utils/validation"

const errors = validateDetails("", "nope")

createRoot(document.getElementById("root")!).render(
    <div className="mx-auto max-w-3xl space-y-6 p-6">
        <h1 className="font-heading text-3xl font-extrabold">Building blocks</h1>
        <Panel className="space-y-4">
            <div className="flex flex-wrap gap-2">
                <Button>Primary</Button>
                <Button variant="secondary">Secondary</Button>
                <Button variant="danger">Danger</Button>
                <Button loading>Loading</Button>
            </div>
            <FormField label="Full name" required error={errors.name}>
                {(field) => <Input {...field} />}
            </FormField>
            <FormField label="Email" hint="Demo only." error={errors.email}>
                {(field) => <Input {...field} type="email" />}
            </FormField>
            <div className="flex gap-2">
                <StatusBadge status="confirmed" />
                <StatusBadge status="cancelled" />
            </div>
            <p>
                {formatClinicDate("2026-12-10T09:00:00Z")}, {formatClinicTime("2026-12-10T09:00:00Z")}
            </p>
        </Panel>
        <EmptyState title="No times to book yet" description="Please check back soon." />
        <ErrorState title="Something went wrong" description="Please try again." onRetry={() => undefined} />
    </div>,
)