export function companyPath({ name, id }) {
  return '/' + encodeURIComponent(name) + '-' + id
}
