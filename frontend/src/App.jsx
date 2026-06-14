import { useState } from "react"
import axios from "axios"

const tagStyle = (cor) => ({
  display: "inline-flex",
  alignItems: "center",
  gap: 4,
  fontSize: 11,
  fontWeight: 500,
  padding: "3px 8px",
  borderRadius: 999,
  background: cor === "green" ? "#e6f4ed" : cor === "blue" ? "#e6f0fa" : cor === "orange" ? "#fff3e0" : "#fae6e6",
  color: cor === "green" ? "#1a7a4a" : cor === "blue" ? "#1a5a8a" : cor === "orange" ? "#b45309" : "#8a1a1a",
})

function Tags({ r }) {
  return (
    <div style={{ display: "flex", flexWrap: "wrap", gap: 6, margin: "8px 0" }}>
      {r.fonte_confiavel && (
        <span style={tagStyle("green")}>✓ Fonte conhecida</span>
      )}
      {r.download_direto && (
        <span style={tagStyle("green")}>↓ Download direto</span>
      )}
      {!r.encurtador && !r.download_direto && (
        <span style={tagStyle("blue")}>→ Link direto</span>
      )}
      {r.encurtador && (
        <span style={tagStyle("orange")}>⚠ Encurtador de link</span>
      )}
    </div>
  )
}

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
    <div style={{ maxWidth: 720, margin: "60px auto", padding: "0 20px", fontFamily: "sans-serif" }}>
      <h1 style={{ textAlign: "center", marginBottom: 8, fontSize: 36 }}>Atchload</h1>
      <p style={{ textAlign: "center", color: "#888", marginBottom: 32, fontSize: 14 }}>
        Buscador inteligente de downloads
      </p>

      <div style={{ display: "flex", gap: 8, marginBottom: 32 }}>
        <input
          type="text"
          value={query}
          onChange={e => setQuery(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder="Pesquise um programa, filme, livro, jogo..."
          style={{ flex: 1, padding: "12px 16px", fontSize: 15, borderRadius: 10, border: "1px solid #ccc", outline: "none" }}
        />
        <button
          onClick={buscar}
          style={{ padding: "12px 22px", fontSize: 15, borderRadius: 10, background: "#1a1a1a", color: "#fff", border: "none", cursor: "pointer" }}
        >
          Buscar
        </button>
      </div>

      {carregando && (
        <p style={{ textAlign: "center", color: "#888" }}>Buscando e analisando fontes...</p>
      )}
      {erro && <p style={{ color: "red" }}>{erro}</p>}

      {resultados.map((r, i) => (
        <div key={i} style={{ border: "1px solid #e0e0e0", borderRadius: 12, padding: "16px 20px", marginBottom: 14, position: "relative" }}>

          {/* Score */}
          <div style={{
            position: "absolute", top: 16, right: 16,
            width: 40, height: 40, borderRadius: 8,
            background: r.score >= 80 ? "#e6f4ed" : r.score >= 60 ? "#e6f0fa" : "#fff3e0",
            color: r.score >= 80 ? "#1a7a4a" : r.score >= 60 ? "#1a5a8a" : "#b45309",
            display: "flex", alignItems: "center", justifyContent: "center",
            fontWeight: 700, fontSize: 13
          }}>
            {r.score}
          </div>

          <div style={{ fontSize: 15, fontWeight: 600, marginBottom: 2, paddingRight: 50 }}>{r.titulo}</div>
          <div style={{ fontSize: 12, color: "#888", marginBottom: 6 }}>{r.dominio}</div>

          <Tags r={r} />

          <div style={{ fontSize: 13, color: "#444", marginBottom: 12 }}>{r.descricao}</div>

          <div style={{ display: "flex", gap: 8 }}>
            {r.download_direto ? (
              <a href={r.link} download style={{
                padding: "8px 16px", borderRadius: 8, fontSize: 13, fontWeight: 500,
                background: "#e6f4ed", color: "#1a7a4a", textDecoration: "none"
              }}>
                ↓ Baixar agora
              </a>
            ) : (
              <a href={r.link} target="_blank" rel="noreferrer" style={{
                padding: "8px 16px", borderRadius: 8, fontSize: 13, fontWeight: 500,
                background: "#1a1a1a", color: "#fff", textDecoration: "none"
              }}>
                Abrir site ↗
              </a>
            )}
          </div>
        </div>
      ))}
    </div>
  )
}

export default App