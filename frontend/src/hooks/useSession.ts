import { useEffect, useState } from 'react'
import { api, getSession, setUnauthorizedHandler } from '../api/client'

/**
 * Tracks the signed-in username and keeps it in sync with a 401 raised
 * anywhere in the app - a token expiring mid-session drops the user
 * straight back to the login screen instead of leaving stale UI up.
 */
export function useSession() {
  const [username, setUsername] = useState<string | null>(() => getSession()?.username ?? null)

  useEffect(() => {
    setUnauthorizedHandler(() => setUsername(null))
    return () => setUnauthorizedHandler(null)
  }, [])

  function signOut() {
    api.logout()
    setUsername(null)
  }

  return { username, setUsername, signOut }
}