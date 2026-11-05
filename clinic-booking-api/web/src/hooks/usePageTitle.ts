import { useEffect } from "react"

/** Sets the browser tab title so screen reader users hear where they are after a page change. */
export function usePageTitle(title: string) {
    useEffect(() => {
        document.title = `${title} | Demo clinic`
    }, [title])
}