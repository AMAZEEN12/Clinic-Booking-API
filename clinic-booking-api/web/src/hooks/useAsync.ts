import { useCallback, useEffect, useRef, useState } from "react"

export type AsyncState<T> =
    | { status: "loading" }
    | { status: "error"; error: unknown }
    | { status: "ready"; data: T }

/**
 * Runs `load` when the component appears and again whenever `key` changes.
 * - reload(): shows the loading state, then loads again (the "Try again" button).
 * - refresh(): loads again without a loading flash (keeps what is on screen).
 * - setData(): replaces the data without a request (for example after a cancel).
 */
export function useAsync<T>(load: () => Promise<T>, key: string) {
    const [state, setState] = useState<AsyncState<T>>({ status: "loading" })
    const [attempt, setAttempt] = useState(0)

    // Always call the newest `load` without making it a dependency of the effect below.
    const loadRef = useRef(load)
    useEffect(() => {
        loadRef.current = load
    })

    useEffect(() => {
        let ignore = false
        loadRef
            .current()
            .then((data) => {
                if (!ignore) setState({ status: "ready", data })
            })
            .catch((error: unknown) => {
                if (!ignore) setState({ status: "error", error })
            })
        return () => {
            ignore = true
        }
    }, [key, attempt])

    const reload = useCallback(() => {
        setState({ status: "loading" })
        setAttempt((n) => n + 1)
    }, [])

    const refresh = useCallback(() => setAttempt((n) => n + 1), [])

    const setData = useCallback((data: T) => setState({ status: "ready", data }), [])

    return { state, reload, refresh, setData }
}