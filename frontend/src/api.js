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

export async function uploadPaper(sessionId, file, title, authors, year) {
  const form = new FormData()
  form.append('session_id', sessionId)
  form.append('file', file)
  form.append('title', title)
  form.append('authors', authors)
  if (year) form.append('year', String(year))

  const res = await fetch(`${BASE_URL}/upload-paper`, { method: 'POST', body: form })
  if (!res.ok) throw new Error(await res.text())
  return res.json()
}

export async function getSummaries(sessionId) {
  const res = await fetch(`${BASE_URL}/summaries/${sessionId}`)
  if (!res.ok) throw new Error(await res.text())
  return res.json()
}

export async function getMatrix(sessionId) {
  const res = await fetch(`${BASE_URL}/matrix/${sessionId}`)
  if (!res.ok) throw new Error(await res.text())
  return res.json()
}

export async function setMatrix(sessionId, matrix) {
  const res = await fetch(`${BASE_URL}/matrix/${sessionId}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ matrix }),
  })
  if (!res.ok) throw new Error(await res.text())
  return res.json()
}

export async function getDirection(sessionId) {
  const res = await fetch(`${BASE_URL}/direction/${sessionId}`)
  if (!res.ok) throw new Error(await res.text())
  return res.json()
}

export async function setDirection(sessionId, direction) {
  const res = await fetch(`${BASE_URL}/direction/${sessionId}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ direction }),
  })
  if (!res.ok) throw new Error(await res.text())
  return res.json()
}

export async function updateRoleState(sessionId, { researchDirection }) {
  const res = await fetch(`${BASE_URL}/role-state`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      session_id: sessionId,
      research_direction: researchDirection || null,
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

export async function getConversations() {
  const res = await fetch(`${BASE_URL}/conversations`)
  if (!res.ok) throw new Error(await res.text())
  return res.json()
}

export async function saveConversations(conversations) {
  const res = await fetch(`${BASE_URL}/conversations`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ conversations }),
  })
  if (!res.ok) throw new Error(await res.text())
  return res.json()
}

export async function deleteConversation(sessionId) {
  const res = await fetch(`${BASE_URL}/conversations/${sessionId}`, {
    method: 'DELETE',
  })
  if (!res.ok) throw new Error(await res.text())
  return res.json()
}

export async function getChatHistory(sessionId) {
  const res = await fetch(`${BASE_URL}/chat-history/${sessionId}`)
  if (!res.ok) throw new Error(await res.text())
  return res.json()
}

export async function saveChatHistory(sessionId, history) {
  const res = await fetch(`${BASE_URL}/chat-history/${sessionId}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ history }),
  })
  if (!res.ok) throw new Error(await res.text())
  return res.json()
}

export async function getGraph(sessionId) {
  const res = await fetch(`${BASE_URL}/graph/${sessionId}`)
  if (!res.ok) throw new Error(await res.text())
  return res.json()
}

