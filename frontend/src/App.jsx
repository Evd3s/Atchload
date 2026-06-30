import { useState, useCallback } from "react"
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
      display: "inline-flex", alignItems: "center", gap: 4, fontSize: 11, fontWeight: 500, padding: "3px 9px",
      borderRadius: 999, background: c.bg, color: c.text, whiteSpace: "nowrap"
    }}>{texto}</span>
  )
}

function ScoreBadge({ score }) {
  let cor = score >= 70 ? CORES.green : score >= 50 ? CORES.blue : score >= 30 ? CORES.orange : CORES.red;
  return (
    <div style={{
      width: 44, height: 44, borderRadius: 10, flexShrink: 0, background: cor.bg, color: cor.text,
      display: "flex", alignItems: "center", justifyContent: "center", fontWeight: 800, fontSize: 14, 
      border: `1px solid ${cor.text}30`, transition: "all 0.3s"
    }}>{score}</div>
  )
}

function Card({ item }) {
  const [tag, setTag] = useState(item.tag_atchload)
  const [currentScore, setCurrentScore] = useState(item.score)
  const [carregandoVT, setCarregandoVT] = useState(false)
  const [showRiscoModal, setShowRiscoModal] = useState(false)
  
  // Estados para os Detalhes da Análise
  const [showDetalhesModal, setShowDetalhesModal] = useState(false)
  const [hash, setHash] = useState(item.hash)
  const [stats, setStats] = useState({ m: item.malicious || 0, s: item.suspicious || 0 })

  const verificarRaioX = async () => {
    setCarregandoVT(true)
    try {
      const res = await axios.get(`http://127.0.0.1:8000/verificar?url=${encodeURIComponent(item.link)}`)
      setTag(res.data.tag_atchload)
      
      if (res.data.hash) {
         setHash(res.data.hash)
         setStats({ m: res.data.malicious, s: res.data.suspicious })
      }
      
      if (res.data.tag_atchload === "Perigoso") setCurrentScore(0)
      else if (res.data.tag_atchload === "Alerta de Cuidado") setCurrentScore(prev => Math.max(0, prev - 15))
    } catch { 
      setTag("Erro") 
    } finally { 
      setCarregandoVT(false) 
    }
  }

  const getTagColor = (t) => {
    if (t === "Seguro / Confiável") return "green";
    if (t === "Alerta de Cuidado") return "orange";
    if (t === "Perigoso") return "red";
    if (t === "Enviado ao VT") return "blue";
    return "gray";
  }

  const analisado = tag === "Seguro / Confiável" || tag === "Alerta de Cuidado" || tag === "Perigoso";

  return (
    <>
      <div style={{ border: "1px solid #e0e0e0", borderRadius: 12, padding: "16px 20px", marginBottom: 14 }}>
        <div style={{ display: "flex", gap: 12, alignItems: "flex-start" }}>
          <div style={{ flex: 1, minWidth: 0 }}>
            <div style={{ fontSize: 15, fontWeight: 600, marginBottom: 2 }}>{item.titulo}</div>
            <div style={{ fontSize: 12, color: "#888", marginBottom: 8 }}>{item.dominio_limpo}</div>
            
            <div style={{ display: "flex", flexWrap: "wrap", gap: 5, marginBottom: 10 }}>
              <Tag cor={getTagColor(tag)} texto={tag} />
              {item.download_direto && <Tag cor="purple" texto="Arquivo / Download Direto" />}
            </div>

            <div style={{ fontSize: 13, color: "#444", marginBottom: 12 }}>{item.descricao}</div>
            
            <div style={{ display: "flex", gap: 10 }}>
              <a href={item.link} 
                 onClick={(e) => { 
                   e.preventDefault(); 
                   if(tag === "Perigoso" || tag === "Alerta de Cuidado") setShowRiscoModal(true); 
                   else window.open(item.link, "_blank"); 
                 }} 
                 style={{ padding: "8px 16px", borderRadius: 8, fontSize: 13, fontWeight: 500, background: "#1a1a1a", color: "#fff", textDecoration: "none" }}>
                 Abrir site ↗
              </a>
              
              {!analisado && (
                <button 
                  onClick={verificarRaioX} 
                  disabled={carregandoVT} 
                  style={{ padding: "8px 16px", borderRadius: 8, fontSize: 13, background: "#f0f0f0", border: "1px solid #ccc", cursor: carregandoVT ? "wait" : "pointer" }}>
                  {carregandoVT ? "Analisando Destino..." : "Verificar Segurança"}
                </button>
              )}

              {/* NOVO BOTÃO: Só aparece DEPOIS que o VirusTotal analisar */}
              {analisado && hash && (
                <button 
                  onClick={() => setShowDetalhesModal(true)} 
                  style={{ padding: "8px 16px", borderRadius: 8, fontSize: 13, background: "#fff", border: "1px solid #ccc", color: "#333", cursor: "pointer", display: "flex", alignItems: "center", gap: 6 }}>
                  🔍 Ver Detalhes
                </button>
              )}
            </div>
          </div>
          <ScoreBadge score={currentScore} />
        </div>
      </div>

      {/* MODAL 1: AVISO DE RISCO (Bloqueio) */}
      {showRiscoModal && (
        <div style={{ position: "fixed", top: 0, left: 0, width: "100%", height: "100%", backgroundColor: "rgba(0, 0, 0, 0.6)", display: "flex", alignItems: "center", justifyContent: "center", zIndex: 9999 }}>
          <div style={{ background: "#fff", padding: "32px", borderRadius: "16px", maxWidth: "420px", width: "90%" }}>
            <h2 style={{ margin: "0 0 12px 0", color: tag === "Perigoso" ? "#b91c1c" : "#b45309" }}>⚠️ Aviso de Risco</h2>
            <p>Os motores antivírus classificaram o ficheiro ou destino deste link como <b>{tag}</b>.</p>
            <p style={{ fontSize: 13, color: "#666" }}>Deseja prosseguir mesmo com estes alertas de segurança?</p>
            
            <div style={{ display: "flex", flexDirection: "column", gap: 8, marginTop: 24 }}>
              <button onClick={() => setShowRiscoModal(false)} style={{ padding: "12px", borderRadius: "8px", background: "#1a1a1a", color: "#fff", border: "none", cursor: "pointer" }}>Voltar em Segurança</button>
              <button onClick={() => { setShowRiscoModal(false); window.open(item.link, "_blank"); }} style={{ padding: "12px", borderRadius: "8px", background: "transparent", border: "1px solid #e5e7eb", cursor: "pointer" }}>Entendo os riscos, abrir mesmo assim</button>
            </div>
          </div>
        </div>
      )}

      {/* MODAL 2: DETALHES TÉCNICOS (Onde o Hash está escondido) */}
      {showDetalhesModal && (
        <div style={{ position: "fixed", top: 0, left: 0, width: "100%", height: "100%", backgroundColor: "rgba(0, 0, 0, 0.6)", display: "flex", alignItems: "center", justifyContent: "center", zIndex: 9999 }}>
          <div style={{ background: "#fff", padding: "32px", borderRadius: "16px", maxWidth: "500px", width: "90%" }}>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 16 }}>
              <h2 style={{ margin: 0, fontSize: 18, color: "#333" }}>📊 Relatório do VirusTotal</h2>
              <button onClick={() => setShowDetalhesModal(false)} style={{ background: "none", border: "none", fontSize: 18, cursor: "pointer" }}>✖</button>
            </div>
            
            <div style={{ marginBottom: 20 }}>
              <p style={{ margin: "0 0 8px 0", fontSize: 14 }}><strong>Veredito:</strong> <Tag cor={getTagColor(tag)} texto={tag} /></p>
              <p style={{ margin: "0 0 4px 0", fontSize: 14 }}><strong>Ameaças Detetadas:</strong> {stats.m} motores de antivírus</p>
              <p style={{ margin: "0 0 0 0", fontSize: 14 }}><strong>Avisos Suspeitos:</strong> {stats.s} motores de antivírus</p>
            </div>

            {/* O TERMINAL HACKER AQUI DENTRO! */}
            <div style={{ 
              marginBottom: 24, fontSize: 12, background: "#1a1a1a", color: "#00ffcc", 
              padding: "12px", borderRadius: 8, fontFamily: "monospace", wordBreak: "break-all",
              borderLeft: "4px solid #00ffcc"
            }}>
              <strong style={{color: "#888", display: "block", marginBottom: 4}}>Impressão Digital do Ficheiro (SHA-256):</strong> 
              {hash}
            </div>

            <button onClick={() => setShowDetalhesModal(false)} style={{ width: "100%", padding: "12px", borderRadius: "8px", background: "#f0f0f0", color: "#333", border: "1px solid #ccc", cursor: "pointer", fontWeight: "bold" }}>
              Fechar Detalhes
            </button>
          </div>
        </div>
      )}
    </>
  )
}

export default function App() {
  const [query, setQuery] = useState("")
  const [resultados, setResultados] = useState([])
  const [carregando, setCarregando] = useState(false)

  const buscar = useCallback(async () => {
    if (!query.trim() || carregando) return
    setCarregando(true)
    try {
      const res = await axios.get("http://127.0.0.1:8000/buscar", { params: { q: query } })
      setResultados(res.data.resultados)
    } catch { } 
    finally { setCarregando(false) }
  }, [query, carregando])

  return (
    <div style={{ maxWidth: 720, margin: "60px auto", padding: "0 20px", fontFamily: "sans-serif" }}>
      <h1 style={{ textAlign: "center", marginBottom: 8, fontSize: 36 }}>Atchload</h1>
      <p style={{ textAlign: "center", color: "#888", marginBottom: 32, fontSize: 14 }}>O radar de downloads seguros</p>
      
      <div style={{ display: "flex", gap: 8, marginBottom: 32 }}>
        <input 
          type="text" 
          value={query} 
          onChange={e => setQuery(e.target.value)} 
          onKeyUp={e => e.key === 'Enter' && buscar()} 
          placeholder="Pesquise o arquivo que deseja buscar..." 
          style={{ flex: 1, padding: "12px 16px", fontSize: 15, borderRadius: 10, border: "1px solid #ccc", outline: "none" }} 
        />
        <button onClick={buscar} disabled={carregando} style={{ padding: "12px 22px", fontSize: 15, borderRadius: 10, background: "#1a1a1a", color: "#fff", border: "none", cursor: "pointer", opacity: carregando ? 0.7 : 1 }}>{carregando ? "Buscando..." : "Buscar"}</button>
      </div>

      {resultados.map((r, i) => <Card key={i} item={r} />)}
    </div>
  )
}