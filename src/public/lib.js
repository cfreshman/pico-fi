(() => {
  const Q = (L, q=undefined) => (q ? L : document.body).querySelector(q || L)
  const QQ = (L, q=undefined) => Array.from((q ? L : document.body).querySelectorAll(q || L))

  const persist = (method, data={}) =>
    fetch(`/${method}?data=${encodeURIComponent(JSON.stringify(data))}`)
    .then(res => res.json())
    .then(({ data }) => {
      console.debug(method, 'result:', data)
      return data
    })
  const get = data => persist('get', data)
  const set = data => persist('set', data)

  window.lib = {
    Q, QQ,
    persist, get, set,
  }
})()