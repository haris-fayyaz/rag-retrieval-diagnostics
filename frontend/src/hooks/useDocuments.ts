import { useCallback, useEffect, useState } from 'react'
import { api, type Document } from '../api/client'

/**
 * Loads and refreshes the document list. Refetches automatically
 * whenever `active` flips true (right after sign-in) - callers pass
 * the session state in so this hook never fetches while signed out.
 */
export function useDocuments(active: boolean) {
  const [documents, setDocuments] = useState<Document[]>([])
  const [loading, setLoading] = useState(false)

  const refresh = useCallback(async () => {
    setLoading(true)
    try {
      setDocuments(await api.listDocuments())
    } catch {
      setDocuments([])
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    if (active) void refresh()
  }, [active, refresh])

  return { documents, loading, refresh }
}