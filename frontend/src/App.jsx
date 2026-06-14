import { useState } from "react"
import axios from "axios"

function App() {
  const [query, setQuery] = useState("")
  const [resultados, setResultados] = useState([])
  const [carregando, setCarregando] = useState(false)
  const [erro, setErro] = useState("")

  const buscar = async () => {
    if (!query.trim()) return
    setCarregando(true)
    setErro("")
    setResultados([])

    try {
      const resposta = await axios.get("http://127.0.0.1:8000/buscar", {
        params: { q: query }
      })
      setResultados(resposta.data.resultados)
    } catch (e) {
      setErro("Erro ao buscar. Verifique se o backend está rodando.")
    } finally {
      setCarregando(false)
    }
  }

  const handleKeyDown = (e) => {
    if (e.key === "Enter") buscar()
  }

  return (
    <div style={{ maxWidth: 700, margin: "60px auto", padding: "0 20px", fontFamily: "sans-serif" }}>
      <h1 style={{ textAlign: "center", marginBottom: 32 }}>Atchload</h1>

      <div style={{ display: "flex", gap: 8, marginBottom: 32 }}>
        <input
          type="text"
          value={query}
          onChange={e => setQuery(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder="Pesquise um programa, arquivo ou mídia..."
          style={{ flex: 1, padding: "10px 14px", fontSize: 15, borderRadius: 8, border: "1px solid #ccc" }}
        />
        <button
          onClick={buscar}
          style={{ padding: "10px 20px", fontSize: 15, borderRadius: 8, background: "#1a1a1a", color: "#fff", border: "none", cursor: "pointer" }}
        >
          Buscar
        </button>
      </div>

      {carregando && <p style={{ textAlign: "center", color: "#888" }}>Buscando...</p>}
      {erro && <p style={{ color: "red" }}>{erro}</p>}

      {resultados.map((r, i) => (
        <div key={i} style={{ border: "1px solid #e0e0e0", borderRadius: 10, padding: "14px 18px", marginBottom: 12 }}>
          <div style={{ fontSize: 15, fontWeight: 600, marginBottom: 4 }}>{r.titulo}</div>
          <div style={{ fontSize: 12, color: "#888", marginBottom: 6 }}>{r.dominio}</div>
          <div style={{ fontSize: 13, color: "#444", marginBottom: 10 }}>{r.descricao}</div>
          <a href={r.link} target="_blank" rel="noreferrer"
            style={{ fontSize: 13, color: "#1a5a8a", textDecoration: "none" }}>
            Abrir link ↗
          </a>
        </div>
      ))}
    </div>
  )
}

export default App