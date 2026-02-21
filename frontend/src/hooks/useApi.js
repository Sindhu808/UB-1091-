/**
 * useApi – generic REST fetch hook with loading / error states.
 */
import { useState, useEffect } from 'react'
import axios from 'axios'

export function useApi(endpoint, deps = []) {
    const [data, setData] = useState(null)
    const [loading, setLoad] = useState(true)
    const [error, setError] = useState(null)

    useEffect(() => {
        let cancelled = false
        setLoad(true)
        axios.get(endpoint)
            .then(r => { if (!cancelled) { setData(r.data); setLoad(false) } })
            .catch(e => { if (!cancelled) { setError(e.message); setLoad(false) } })
        return () => { cancelled = true }
        // eslint-disable-next-line react-hooks/exhaustive-deps
    }, deps)

    return { data, loading, error }
}
