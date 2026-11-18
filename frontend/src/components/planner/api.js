export async function plannerApi(path, method = 'GET', body) {
  const response = await fetch('/api/planner/' + path, {
    method,
    ...(body && { headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) }),
  })
  if (!response.ok) {
    const error = new Error(response.status === 422 ? '입력한 날짜와 시간을 확인해 주세요.' : '요청을 처리할 수 없습니다. 잠시 후 다시 시도해 주세요.')
    error.status = response.status
    throw error
  }
  return response.status === 204 ? null : response.json()
}
