export async function sendQuery(question) {
  const response = await fetch('/api/query', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ question }),
  });

  if (!response.ok) {
    throw new Error(`API error: ${response.status} ${response.statusText}`);
  }

  return response.json();
}

export async function recordSteps(steps) {
  const response = await fetch('/api/record', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ steps }),
  });

  if (!response.ok) return null;
  const data = await response.json();
  return data.video_url ?? null;
}

export async function ingestFile(file) {
  const formData = new FormData();
  formData.append('file', file);

  const response = await fetch('/api/ingest', {
    method: 'POST',
    body: formData,
  });

  if (!response.ok) {
    throw new Error(`Ingest error: ${response.status} ${response.statusText}`);
  }

  return response.json();
}
