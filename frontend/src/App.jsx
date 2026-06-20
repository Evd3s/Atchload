import { useState, useCallback, useEffect } from "react"
import axios from "axios"

const CORES = {
  green:  { bg: "#e6f4ed", text: "#1a7a4a" },
  blue:   { bg: "#e6f0fa", text: "#1a5a8a" },
  orange: { bg: "#fff3e0", text: "#b45309" },
  red:    { bg: "#fae6e6", text: "#8a1a1a" },
  gray:   { bg: "#f0f0f0", text: "#555555" },
  purple: { bg: "#f3e6fa", text: "#6a1a8a" },
}

function Tag({ cor, texto }) {
  const c = CORES[cor] || CORES.gray
  return (
    <span style={{
      display: "inline-flex", alignItems: "center", gap: 4,
      fontSize: 11, fontWeight: 500, padding: "3px 9px",
      borderRadius: 999, background: c.bg, color: c.text,
      whiteSpace: "nowrap"
    }}>
      {texto}
    </span>
  )
}

function ScoreBadge({ score }) {
  // 70+ vira verde (excelente/download direto)
  // 50+ vira azul (bom/informativo seguro)
  // Abaixo de 50 vira laranja (atenção)
  let cor;
  if (score >= 70) cor = CORES.green;
  else if (score >= 50) cor = CORES.blue;
  else if (score >= 30) cor = CORES.orange;
  else cor = CORES.red;

  return (
    <div style={{
      width: 44, height: 44, borderRadius: 10, flexShrink: 0,
      background: cor.bg, color: cor.text,
      display: "flex", alignItems: "center", justifyContent: "center",
      fontWeight: 800, fontSize: 14, border: `1px solid ${cor.text}30`
    }}>
      {score}
    </div>
  )
}

function Card({ item }) {
  const [tag, setTag] = useState(item.tag_atchload)

  useEffect(() => {
    if (tag === "Aguardando Análise" || tag === "Análise em Processo") {
      const interval = setInterval(async () => {
        try {
          const res = await axios.get(`http://127.0.0.1:8000/verificar?url=${encodeURIComponent(item.link)}`)
          if (res.data.tag_atchload && res.data.tag_atchload !== "Análise em Processo") {
            setTag(res.data.tag_atchload)
            clearInterval(interval)
          }
        } catch (e) { console.error(e) }
      }, 5000)
      return () => clearInterval(interval)
    }
  }, [tag, item.link])

  const getTagColor = (t) => {
    if (t === "Seguro / Confiável") return "green";
    if (t === "Inseguro") return "orange";
    if (t === "Perigoso") return "red";
    return "gray";
  }

  const getAdsColor = (prop) => {
    if (prop === "limpo") return "green";
    if (prop === "moderado") return "orange";
    return "red";
  }

  return (
    <div style={{ border: "1px solid #e0e0e0", borderRadius: 12, padding: "16px 20px", marginBottom: 14 }}>
      <div style={{ display: "flex", gap: 12, alignItems: "flex-start" }}>
        <div style={{ flex: 1, minWidth: 0 }}>
          <div style={{ fontSize: 15, fontWeight: 600, marginBottom: 2 }}>{item.titulo}</div>
          <div style={{ fontSize: 12, color: "#888", marginBottom: 8 }}>{item.dominio_limpo}</div>
          
          <div style={{ display: "flex", flexWrap: "wrap", gap: 5, marginBottom: 10 }}>
            <Tag cor={getTagColor(tag)} texto={tag} />
            {item.download_direto && <Tag cor="purple" texto="Download Direto" />}
            <Tag cor={getAdsColor(item.propaganda)} texto={`Ads: ${item.propaganda}`} />
          </div>

          <div style={{ fontSize: 13, color: "#444", marginBottom: 12 }}>{item.descricao}</div>
          
          <a href={item.link} target="_blank" rel="noreferrer" style={{
            padding: "8px 16px", borderRadius: 8, fontSize: 13, fontWeight: 500,
            background: "#1a1a1a", color: "#fff", textDecoration: "none", display: "inline-block"
          }}>
            Abrir site ↗
          </a>
        </div>
        <ScoreBadge score={item.score} />
      </div>
    </div>
  )
}

export default function App() {
  const [query, setQuery] = useState("")
  const [resultados, setResultados] = useState([])
  const [carregando, setCarregando] = useState(false)
  const [erro, setErro] = useState("")

  const buscar = useCallback(async () => {
    if (!query.trim() || carregando) return
    setCarregando(true)
    setErro("")
    try {
      const res = await axios.get("http://127.0.0.1:8000/buscar", { params: { q: query } })
      setResultados(res.data.resultados)
    } catch {
      setErro("Erro ao buscar. O servidor Python está rodando?")
    } finally {
      setCarregando(false)
    }
  }, [query, carregando])

  return (
    <div style={{ maxWidth: 720, margin: "60px auto", padding: "0 20px", fontFamily: "sans-serif" }}>
      <h1 style={{ textAlign: "center", marginBottom: 8, fontSize: 36 }}>Atchload</h1>
      <p style={{ textAlign: "center", color: "#888", marginBottom: 32, fontSize: 14 }}>
        Buscador inteligente de downloads
      </p>
      
      <div style={{ display: "flex", gap: 8, marginBottom: 32 }}>
        <input
          type="text" value={query} 
          onChange={e => setQuery(e.target.value)}
          onKeyDown={e => e.key === 'Enter' && buscar()}
          placeholder="Pesquise um programa, filme, livro, jogo..."
          style={{ flex: 1, padding: "12px 16px", fontSize: 15, borderRadius: 10, border: "1px solid #ccc", outline: "none" }}
        />
        <button 
          onClick={buscar} 
          disabled={carregando}
          style={{ padding: "12px 22px", fontSize: 15, borderRadius: 10, background: "#1a1a1a", color: "#fff", border: "none", cursor: "pointer", opacity: carregando ? 0.7 : 1 }}
        >
          {carregando ? "Buscando..." : "Buscar"}
        </button>
      </div>

      {erro && <p style={{ color: "red", textAlign: "center" }}>{erro}</p>}
      
      {resultados.map((r, i) => <Card key={i} item={r} />)}
    </div>
  )
}