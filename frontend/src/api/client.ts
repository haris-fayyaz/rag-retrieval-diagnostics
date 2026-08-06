/**
 * Centralised API client. Every screen goes through this module so that auth,
 * token expiry and HTTP error mapping are handled in exactly one place.
 */

const BASE_URL = (import.meta.env.VITE_API_BASE_URL as string | undefined) ?? ''
const TOKEN_KEY = 'rag_assistant_token'
const USER_KEY = 'rag_assistant_user'

/* ------------------------------------------------------------------ types */

export interface Document {
  id: string
  name: string
  chunk_count: number
}

export interface Citation {
  document_id: string
  document_name: string
  // Position of this chunk within the retrieved list (1-based), not a
  // backend id. Backend has no numeric index, only a chunk_id string.
  chunk_index: number
}

export interface RetrievedChunk {
  document_id: string
  document_name: string
  score: number
  text: string
}

export interface AnswerResponse {
  answer: string
  has_context: boolean
  citations: Citation[]
  chunks: RetrievedChunk[]
  retrieval_ms: number
  generation_ms?: number
  request_id: string
}

/* -------------------------------------------------- raw backend shapes
 * Mirrors app/models.py exactly. Never exposed outside this file, the
 * `answer()` function below maps these into the shapes above. */

interface RawAnswerChunkRef {
  chunk_id: string
  document_id: string
  document_name: string
  score: number
  text_snippet: string
}

interface RawAnswerMetadata {
  retrieval_ms: number
  generation_ms: number | null
  total_ms: number
  retrieved_chunk_count: number
  retrieval_mode: string
  provider: string
}

interface RawAnswerResponse {
  request_id: string
  question: string
  answer: string | null
  citations: string[]
  retrieved_chunks: RawAnswerChunkRef[]
  message: string | null
  metadata: RawAnswerMetadata | null
}

export interface AgentResponse {
  answer: string
  tool: string
  citations: Citation[]
  steps: number
  // Real backend status values, shown as-is in the UI, not remapped
  // into fake categories.
  status: 'success' | 'no_context' | 'refused' | 'tool_error'
  request_id: string
}

interface RawAgentCitation {
  chunk_id: string
  document_id: string
  document_name: string
}

interface RawAgentQueryResponse {
  request_id: string
  answer: string
  selected_tool: string | null
  citations: RawAgentCitation[]
  step_count: number
  status: string
  error: string | null
}

export interface Session {
  token: string
  username: string
}

/* ------------------------------------------------------------------ errors */

export class ApiError extends Error {
  status: number
  constructor(status: number, message: string) {
    super(message)
    this.name = 'ApiError'
    this.status = status
  }
}

/** User-facing copy for every status the backend can return. Never surfaces
 *  server internals or stack traces. */
export function messageForStatus(status: number): string {
  if (status === 401) return 'Your session has expired. Please sign in again.'
  if (status === 403) return 'You do not have permission to perform this action.'
  if (status === 422) return 'Please check the information you entered.'
  if (status === 429) return 'Too many requests. Please wait a moment and try again.'
  if (status >= 500) return 'Something went wrong on the server. Please try again.'
  if (status === 0) return 'Unable to reach the server. Please try again.'
  return 'Something went wrong. Please try again.'
}

/* ------------------------------------------------------------------ session */

let onUnauthorized: (() => void) | null = null

export function setUnauthorizedHandler(handler: (() => void) | null) {
  onUnauthorized = handler
}

export function getSession(): Session | null {
  const token = localStorage.getItem(TOKEN_KEY)
  const username = localStorage.getItem(USER_KEY)
  return token && username ? { token, username } : null
}

function saveSession(session: Session) {
  localStorage.setItem(TOKEN_KEY, session.token)
  localStorage.setItem(USER_KEY, session.username)
}

export function clearSession() {
  localStorage.removeItem(TOKEN_KEY)
  localStorage.removeItem(USER_KEY)
}

/* ------------------------------------------------------------------ request */

async function request<T>(path: string, init: RequestInit = {}): Promise<T> {
  if (!BASE_URL) return mockRequest<T>(path, init)

  const session = getSession()
  let response: Response

  try {
    response = await fetch(`${BASE_URL}${path}`, {
      ...init,
      headers: {
        'Content-Type': 'application/json',
        ...(session ? { Authorization: `Bearer ${session.token}` } : {}),
        ...init.headers,
      },
    })
  } catch {
    throw new ApiError(0, messageForStatus(0))
  }

  if (response.status === 401) {
    clearSession()
    onUnauthorized?.()
    throw new ApiError(401, messageForStatus(401))
  }

  if (!response.ok) throw new ApiError(response.status, messageForStatus(response.status))

  return response.status === 204 ? (undefined as T) : ((await response.json()) as T)
}

/* ------------------------------------------------------------------ endpoints */

export const api = {
  async login(username: string, password: string): Promise<Session> {
    const result = await request<{ access_token: string }>('/auth/token', {
      method: 'POST',
      body: JSON.stringify({ username, password }),
    })
    const session = { token: result.access_token, username }
    saveSession(session)
    return session
  },

  logout() {
    clearSession()
  },

  async listDocuments(): Promise<Document[]> {
    const docs = await request<{ document_id: string; name: string; chunk_count: number }[]>('/documents')
    return docs.map((d) => ({ id: d.document_id, name: d.name, chunk_count: d.chunk_count }))
  },

  async createDocument(name: string, text: string): Promise<Document> {
    const doc = await request<{ document_id: string; name: string; chunk_count: number }>('/documents', {
      method: 'POST',
      body: JSON.stringify({ name, text }),
    })
    return { id: doc.document_id, name: doc.name, chunk_count: doc.chunk_count }
  },

  async answer(params: {
    question: string
    document_ids: string[]
    top_k: number
  }): Promise<AnswerResponse> {
    const raw = await request<RawAnswerResponse>('/answer', {
      method: 'POST',
      body: JSON.stringify(params),
    })

    // retrieved_chunks is already sorted by score (backend guarantees this),
    // so array position doubles as the display rank, 1-based.
    const positionByChunkId = new Map(raw.retrieved_chunks.map((c, i) => [c.chunk_id, i + 1]))

    return {
      answer: raw.answer ?? raw.message ?? '',
      has_context: raw.answer !== null,
      citations: raw.citations.map((chunkId) => {
        const chunk = raw.retrieved_chunks.find((c) => c.chunk_id === chunkId)
        return {
          document_id: chunk?.document_id ?? '',
          document_name: chunk?.document_name ?? '',
          chunk_index: positionByChunkId.get(chunkId) ?? 0,
        }
      }),
      chunks: raw.retrieved_chunks.map((c) => ({
        document_id: c.document_id,
        document_name: c.document_name,
        score: c.score,
        text: c.text_snippet,
      })),
      retrieval_ms: raw.metadata?.retrieval_ms ?? 0,
      generation_ms: raw.metadata?.generation_ms ?? undefined,
      request_id: raw.request_id,
    }
  },

  async agentQuery(question: string): Promise<AgentResponse> {
    // Backend field is "query", not "question" - this endpoint's
    // request shape differs from /answer's.
    const raw = await request<RawAgentQueryResponse>('/agent/query', {
      method: 'POST',
      body: JSON.stringify({ query: question }),
    })

    return {
      answer: raw.answer,
      tool: raw.selected_tool ?? 'none',
      // No separate retrieved-chunks list here (unlike /answer), so
      // each citation's own array position is its display rank.
      citations: raw.citations.map((c, i) => ({
        document_id: c.document_id,
        document_name: c.document_name,
        chunk_index: i + 1,
      })),
      steps: raw.step_count,
      status: raw.status as AgentResponse['status'],
      request_id: raw.request_id,
    }
  },
}

/* ------------------------------------------------------------------ mock
 * Used only while VITE_API_BASE_URL is unset, so the interface is navigable
 * before the backend is wired up. Shapes mirror the real endpoints exactly. */

const mockDocuments: Document[] = [
  { id: 'doc_7f21ab', name: 'Research Notes', chunk_count: 14 },
  { id: 'doc_c40e93', name: 'API Documentation', chunk_count: 32 },
  { id: 'doc_19b8d2', name: 'Project Notes', chunk_count: 9 },
]

const delay = (ms: number) => new Promise((resolve) => setTimeout(resolve, ms))

function requestId() {
  return `req_${Math.random().toString(16).slice(2, 10)}${Math.random().toString(16).slice(2, 6)}`
}

async function mockRequest<T>(path: string, init: RequestInit): Promise<T> {
  const body = init.body ? JSON.parse(init.body as string) : {}
  await delay(path === '/answer' || path === '/agent/query' ? 1400 : 350)

  if (path === '/auth/token') {
    if (!body.username || !body.password) throw new ApiError(422, messageForStatus(422))
    if (body.password === 'wrong') throw new ApiError(401, 'Invalid username or password.')
    return { access_token: 'mock.jwt.token' } as T
  }

  if (path === '/documents' && init.method === 'POST') {
    const created: Document = {
      id: `doc_${Math.random().toString(16).slice(2, 8)}`,
      name: body.name,
      chunk_count: Math.max(1, Math.ceil((body.text?.length ?? 0) / 480)),
    }
    mockDocuments.unshift(created)
    return created as T
  }

  if (path === '/documents') return mockDocuments as T

  if (path === '/answer') {
    const selected = mockDocuments.filter((d) => body.document_ids.includes(d.id))
    const grounded = selected.length > 0 && !/weather|stock price/i.test(body.question)

    if (!grounded) {
      return {
        answer:
          "I couldn't find enough relevant context in the selected sources to answer this question reliably.",
        has_context: false,
        citations: [],
        chunks: [],
        retrieval_ms: 38,
        generation_ms: 210,
        request_id: requestId(),
      } as T
    }

    return {
      answer: `Retrieval runs before generation. The pipeline embeds the question, ranks every chunk in the selected sources by cosine similarity, and passes only the top **${body.top_k}** results to the model as context.\n\nThe generation step is constrained to that context:\n\n- Claims that cannot be traced to a retrieved chunk are omitted rather than inferred.\n- Each sentence is linked back to the chunk it came from, which is what produces the citations below.\n- When similarity falls below the configured floor, the pipeline returns a no-context response instead of guessing.\n\nThe cutoff itself is configured through \`top_k\` on the request.`,
      has_context: true,
      citations: selected.slice(0, 2).map((doc, i) => ({
        document_id: doc.id,
        document_name: doc.name,
        chunk_index: i === 0 ? 3 : 1,
      })),
      chunks: selected.slice(0, 3).map((doc, i) => ({
        document_id: doc.id,
        document_name: doc.name,
        chunk_index: [3, 1, 6][i] ?? i,
        score: [0.82, 0.76, 0.61][i] ?? 0.5,
        text:
          i === 0
            ? 'Retrieval is performed by embedding the incoming question and comparing it against the stored chunk vectors. The highest scoring chunks are selected and concatenated into the prompt context before generation begins.'
            : i === 1
              ? 'The /answer endpoint accepts a question, a list of document identifiers and a top_k value. It returns the generated answer, the citations used, the retrieved chunks and the timing breakdown for retrieval and generation.'
              : 'Chunks that score below the relevance floor are discarded. If no chunk clears the floor the service returns a response indicating that no relevant context was found for the question.',
      })),
      retrieval_ms: 42,
      generation_ms: 1840,
      request_id: requestId(),
    } as T
  }

  if (path === '/agent/query') {
    return {
      answer: `The agent selected the document retrieval tool and searched the indexed sources for material on chunk ranking.\n\nRanking uses cosine similarity over the embedded chunks, with the score threshold applied after ranking rather than before it.`,
      tool: 'document_search',
      citations: [
        { document_id: 'doc_7f21ab', document_name: 'Research Notes', chunk_index: 2 },
        { document_id: 'doc_c40e93', document_name: 'API Documentation', chunk_index: 5 },
      ],
      steps: 3,
      status: 'completed',
      request_id: requestId(),
    } as T
  }

  throw new ApiError(500, messageForStatus(500))
}
