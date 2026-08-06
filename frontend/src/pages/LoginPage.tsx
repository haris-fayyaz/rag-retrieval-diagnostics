import { useState, type FormEvent } from 'react'
import { ApiError, api } from '../api/client'
import Button from '../components/Button'
import ErrorMessage from '../components/ErrorMessage'
import Input from '../components/Input'
import { AppMark } from '../components/icons'

export default function LoginPage({ onSignedIn }: { onSignedIn: (username: string) => void }) {
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [submitting, setSubmitting] = useState(false)
  const [error, setError] = useState<string | null>(null)

  async function handleSubmit(event: FormEvent) {
    event.preventDefault()
    setSubmitting(true)
    setError(null)
    try {
      const session = await api.login(username.trim(), password)
      onSignedIn(session.username)
    } catch (err) {
      setError(
        err instanceof ApiError && err.status === 401
          ? 'Invalid username or password.'
          : err instanceof ApiError
            ? err.message
            : 'Something went wrong. Please try again.',
      )
      setSubmitting(false)
    }
  }

  return (
    <main className="grid min-h-screen place-items-center bg-muted px-6 py-12">
      <div className="w-full max-w-[380px]">
        <div className="mb-8 flex flex-col items-center text-center">
          <AppMark className="text-primary" />
          <h1 className="mt-4 text-[22px] font-semibold tracking-[-0.02em]">RAG Assistant</h1>
          <p className="mt-1 text-[13.5px] text-muted-foreground">Sign in to continue</p>
        </div>

        <form
          onSubmit={handleSubmit}
          className="flex flex-col gap-4 rounded-lg border border-border bg-background p-6"
        >
          <Input
            id="username"
            label="Username"
            autoComplete="username"
            autoFocus
            required
            value={username}
            onChange={(e) => setUsername(e.target.value)}
          />
          <Input
            id="password"
            label="Password"
            type="password"
            autoComplete="current-password"
            required
            value={password}
            onChange={(e) => setPassword(e.target.value)}
          />

          {error && <ErrorMessage message={error} />}

          <Button type="submit" disabled={submitting} className="mt-1 w-full">
            {submitting ? 'Signing in...' : 'Sign in'}
          </Button>
        </form>

        <p className="mt-6 text-center text-[12px] text-muted-foreground">
          Grounded answers from your own documents.
        </p>
      </div>
    </main>
  )
}
