import { useState } from "react"
import axios from "axios"

const API_URL = "http://127.0.0.1:8000"

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
  const cor = score >= 80 ? CORES.green : score >= 60 ? CORES.blue : score >= 40 ? CORES.orange : CORES.red
  return (
    <div style={{
      width: 42, height: 42, borderRadius: 8, flexShrink: 0,
      background: cor.bg, color: cor.text,
      display: "flex", alignItems: "center", justifyContent: "center",
      fontWeight: 700, fontSize: 13
    }}>
      {score}
    </div>
  )
}

function Tags({ r }) {
  return (
    <div style={{ display: "flex", flexWrap: "wrap", gap: 5, margin: "8px 0" }}>
      {r.oficial && <Tag cor="green" texto="✓ Oficial" />}
      {r.fonte_confiavel && !r.oficial && <Tag cor="green" texto="✓ Fonte conhecida" />}
      {r.download_direto && <Tag cor="green" texto="↓ Arquivo direto" />}
      {!r.download_direto && r.tem_download_na_pagina && <Tag cor="blue" texto="Link encontrado na página" />}
      {r.youtube && <Tag cor="purple" texto="▶ YouTube" />}
      {r.streaming && <Tag cor="purple" texto="▶ Streaming" />}
      {r.social_compartilhamento && <Tag cor="blue" texto="Post com possível link" />}
      {r.catalogo && <Tag cor="gray" texto="Catálogo/review" />}
      {r.encurtador && <Tag cor="orange" texto="⚠ Encurtador" />}
      {r.propaganda === "limpo" && <Tag cor="green" texto="Sem anúncios" />}
      {r.propaganda === "moderado" && <Tag cor="orange" texto="Poucos anúncios" />}
      {r.propaganda === "agressivo" && <Tag cor="red" texto="Muitos anúncios" />}
    </div>
  )
}

function Card({ r }) {
  const downloadHref = r.download_url
    ? `${API_URL}/baixar?url=${encodeURIComponent(r.download_url)}`
    : ""

  return (
    <div style={{
      border: "1px solid #e0e0e0", borderRadius: 12,
      padding: "16px 20px", marginBottom: 14,
      background: "#fff"
    }}>
      <div style={{ display: "flex", gap: 12, alignItems: "flex-start" }}>
        <div style={{ flex: 1, minWidth: 0 }}>
          <a
            href={r.link}
            target="_blank"
            rel="noreferrer"
            style={{
              display: "block",
              fontSize: 15,
              fontWeight: 600,
              marginBottom: 2,
              color: "#1a1a1a",
              textDecoration: "none"
            }}
          >
            {r.titulo || "Resultado sem título"} ↗
          </a>

          <div style={{ fontSize: 12, color: "#888", marginBottom: 4 }}>{r.dominio}</div>
          <Tags r={r} />
          <div style={{ fontSize: 13, color: "#444", marginBottom: r.download_direto ? 12 : 0 }}>{r.descricao}</div>

          {r.download_direto && r.download_url && (
            <div style={{ display: "flex", gap: 8 }}>
              <a
                href={downloadHref}
                style={{
                  padding: "8px 16px", borderRadius: 8, fontSize: 13, fontWeight: 500,
                  background: "#e6f4ed", color: "#1a7a4a", textDecoration: "none"
                }}
              >
                ↓ Baixar arquivo
              </a>
            </div>
          )}
        </div>
        <ScoreBadge score={r.score} />
      </div>

      {r.motivos && r.motivos.length > 0 && (
        <div style={{ fontSize: 10, color: "#aaa", marginTop: 8, lineHeight: 1.6 }}>
          {r.motivos.join(" · ")}
        </div>
      )}
    </div>
  )
}

export default function App() {
  const [query, setQuery] = useState("")
  const [resultados, setResultados] = useState([])
  const [carregando, setCarregando] = useState(false)
  const [erro, setErro] = useState("")
  const [pagina, setPagina] = useState(1)

  const buscar = async () => {
    if (!query.trim()) return
    setCarregando(true)
    setErro("")
    setResultados([])
    setPagina(1)
    try {
      const res = await axios.get(`${API_URL}/buscar`, { params: { q: query } })
      setResultados(res.data.resultados || [])
    } catch {
      setErro("Erro ao buscar. Verifique se o backend está rodando.")
    } finally {
      setCarregando(false)
    }
  }

  const porPagina = 15
  const totalPaginas = Math.max(1, Math.ceil(resultados.length / porPagina))
  const inicio = (pagina - 1) * porPagina
  const resultadosPagina = resultados.slice(inicio, inicio + porPagina)

  return (
    <div style={{ maxWidth: 720, margin: "60px auto", padding: "0 20px", fontFamily: "sans-serif" }}>
      <h1 style={{ textAlign: "center", marginBottom: 8, fontSize: 40, fontFamily: "'Tilt Neon', sans-serif" }}>Atchload</h1>
      <p style={{ textAlign: "center", color: "#888", marginBottom: 32, fontSize: 14 }}>
        Buscador inteligente de downloads
      </p>

      <div style={{ display: "flex", gap: 8, marginBottom: 32 }}>
        <input
          type="text"
          value={query}
          onChange={e => setQuery(e.target.value)}
          onKeyDown={e => e.key === "Enter" && buscar()}
          placeholder="Pesquise um programa, filme, livro, jogo..."
          style={{ flex: 1, padding: "12px 16px", fontSize: 15, borderRadius: 10, border: "1px solid #ccc", outline: "none" }}
        />
        <button onClick={buscar} style={{
          padding: "12px 22px", fontSize: 15, borderRadius: 10,
          background: "#1a1a1a", color: "#fff", border: "none", cursor: "pointer"
        }}>
          Buscar
        </button>
      </div>

      {carregando && (
        <p style={{ textAlign: "center", color: "#888" }}>
          Buscando e analisando fontes... isso pode levar alguns segundos.
        </p>
      )}
      {erro && <p style={{ color: "red" }}>{erro}</p>}
      {resultadosPagina.map((r, i) => <Card key={`${pagina}-${i}`} r={r} />)}

      {resultados.length > porPagina && (
        <div style={{ display: "flex", justifyContent: "center", alignItems: "center", gap: 8, marginTop: 22 }}>
          <button
            onClick={() => setPagina(p => Math.max(1, p - 1))}
            disabled={pagina === 1}
            style={{ padding: "8px 11px", borderRadius: 8, border: "1px solid #ddd", background: pagina === 1 ? "#f5f5f5" : "#fff", cursor: pagina === 1 ? "not-allowed" : "pointer" }}
          >
            ‹
          </button>

          {Array.from({ length: totalPaginas }, (_, i) => i + 1).map(n => (
            <button
              key={n}
              onClick={() => setPagina(n)}
              style={{
                padding: "8px 12px", borderRadius: 8, border: "1px solid #ddd",
                background: n === pagina ? "#1a1a1a" : "#fff",
                color: n === pagina ? "#fff" : "#333",
                cursor: "pointer"
              }}
            >
              {n}
            </button>
          ))}

          <button
            onClick={() => setPagina(p => Math.min(totalPaginas, p + 1))}
            disabled={pagina === totalPaginas}
            style={{ padding: "8px 11px", borderRadius: 8, border: "1px solid #ddd", background: pagina === totalPaginas ? "#f5f5f5" : "#fff", cursor: pagina === totalPaginas ? "not-allowed" : "pointer" }}
          >
            ›
          </button>
        </div>
      )}
    </div>
  )
}
