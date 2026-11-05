// Mirrors the API's rules (app/schemas.py): name 1-200 characters, email shaped like a@b.c, at most 254.
// The server is still the authority; this only saves a round trip and puts the message by the field.
const EMAIL_SHAPE = /^[^@\s]+@[^@\s]+\.[^@\s]+$/

export type DetailsErrors = { name?: string; email?: string }

export function validateDetails(name: string, email: string): DetailsErrors {
    const errors: DetailsErrors = {}

    const cleanName = name.trim()
    if (cleanName.length === 0) errors.name = "Enter your name."
    else if (cleanName.length > 200) errors.name = "Use 200 characters or fewer for your name."

    const cleanEmail = email.trim()
    if (cleanEmail.length === 0) errors.email = "Enter your email."
    else if (cleanEmail.length > 254 || !EMAIL_SHAPE.test(cleanEmail)) {
        errors.email = "Enter an email like name@example.com."
    }

    return errors
}