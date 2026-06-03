const BASE_URL = '/api'

export async function sendChat(sessionId, message) {
  const res = await fetch(`${BASE_URL}/chat`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ session_id: sessionId, message }),
  })
  if (!res.ok) throw new Error(await res.text())
  return res.json()
}

export async function uploadPaper(sessionId, file) {
  const form = new FormData()
  form.append('session_id', sessionId)
  form.append('file', file)

  const res = await fetch(`${BASE_URL}/upload-paper`, { method: 'POST', body: form })
  if (!res.ok) throw new Error(await res.text())
  return res.json()
}

export async function extractMetadata(file) {
  const form = new FormData()
  form.append('file', file)
  const res = await fetch(`${BASE_URL}/extract-metadata`, { method: 'POST', body: form })
  if (!res.ok) throw new Error(await res.text())
  return res.json()
}

export async function getSummaries(sessionId) {
  const res = await fetch(`${BASE_URL}/summaries/${sessionId}`)
  if (!res.ok) throw new Error(await res.text())
  return res.json()
}

export async function updateRoleState(sessionId, { large, medium, small }) {
  const res = await fetch(`${BASE_URL}/role-state`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      session_id: sessionId,
      large_direction: large || null,
      medium_direction: medium || null,
      small_direction: small || null,
    }),
  })
  if (!res.ok) throw new Error(await res.text())
  return res.json()
}

export async function getRoleState(sessionId) {
  const res = await fetch(`${BASE_URL}/role-state/${sessionId}`)
  if (!res.ok) throw new Error(await res.text())
  return res.json()
}

export async function getGraph(sessionId) {
  const res = await fetch(`${BASE_URL}/graph/${sessionId}`)
  if (!res.ok) throw new Error(await res.text())
  return res.json()
}
