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
      fontWeight: 800, fontSize: 14, border: `1px solid ${cor.text}30`,
      transition: "background 0.3s, color 0.3s"
    }}>
      {score}
    </div>
  )
}

function Card({ item }) {
  const [tag, setTag] = useState(item.tag_atchload)
  const [currentScore, setCurrentScore] = useState(item.score)
  const [carregandoVT, setCarregandoVT] = useState(false)
  const [showModal, setShowModal] = useState(false) // Estado do Modal

  const verificarNoVirusTotal = async () => {
    setCarregandoVT(true)
    try {
      const res = await axios.get(`http://127.0.0.1:8000/verificar?url=${encodeURIComponent(item.link)}`)
      const novaTag = res.data.tag_atchload
      setTag(novaTag)

      if (novaTag === "Perigoso") {
        setCurrentScore(0)
      } else if (novaTag === "Alerta de Cuidado") {
        setCurrentScore((prev) => Math.max(0, prev - 15))
      }
    } catch (e) {
      console.error(e)
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

  const getAdsColor = (prop) => {
    if (prop === "limpo") return "green";
    if (prop === "moderado") return "orange";
    return "red";
  }

  // Intercepta o clique para abrir o Modal se houver risco
  const handleAbrirSite = (e) => {
    e.preventDefault();
    if (tag === "Perigoso" || tag === "Alerta de Cuidado") {
      setShowModal(true);
    } else {
      window.open(item.link, "_blank", "noreferrer");
    }
  }

  const precisaVerificar = tag === "Aguardando Análise" || tag === "Enviado ao VT";

  return (
    <>
      <div style={{ border: "1px solid #e0e0e0", borderRadius: 12, padding: "16px 20px", marginBottom: 14 }}>
        <div style={{ display: "flex", gap: 12, alignItems: "flex-start" }}>
          <div style={{ flex: 1, minWidth: 0 }}>
            <div style={{ fontSize: 15, fontWeight: 600, marginBottom: 2 }}>{item.titulo}</div>
            <div style={{ fontSize: 12, color: "#888", marginBottom: 8 }}>{item.dominio_limpo}</div>
            
            <div style={{ display: "flex", flexWrap: "wrap", gap: 5, marginBottom: 10 }}>
              <Tag cor={getTagColor(tag)} texto={tag} />
              {item.download_direto && <Tag cor="purple" texto="Download Direto" />}
              <Tag cor={getAdsColor(item.propaganda)} texto={`Estimativa Ads: ${item.propaganda}`} />
            </div>

            <div style={{ fontSize: 13, color: "#444", marginBottom: 12 }}>{item.descricao}</div>
            
            <div style={{ display: "flex", gap: 10 }}>
              <a href={item.link} onClick={handleAbrirSite} style={{
                padding: "8px 16px", borderRadius: 8, fontSize: 13, fontWeight: 500,
                background: "#1a1a1a", color: "#fff", textDecoration: "none", display: "inline-block", cursor: "pointer"
              }}>
                Abrir site ↗
              </a>
              
              {precisaVerificar && (
                <button 
                  onClick={verificarNoVirusTotal} 
                  disabled={carregandoVT}
                  style={{
                    padding: "8px 16px", borderRadius: 8, fontSize: 13, fontWeight: 500,
                    background: "#f0f0f0", color: "#333", border: "1px solid #ccc", 
                    cursor: carregandoVT ? "wait" : "pointer", opacity: carregandoVT ? 0.7 : 1
                  }}
                >
                  {carregandoVT ? "Analisando..." : (tag === "Enviado ao VT" ? "Verificar Resultado" : "Verificar Segurança")}
                </button>
              )}
            </div>
          </div>
          <ScoreBadge score={currentScore} />
        </div>
      </div>

      {/* MODAL DE SEGURANÇA */}
      {showModal && (
        <div style={{
          position: "fixed", top: 0, left: 0, width: "100%", height: "100%",
          backgroundColor: "rgba(0, 0, 0, 0.6)", backdropFilter: "blur(4px)",
          display: "flex", alignItems: "center", justifyContent: "center", zIndex: 9999
        }}>
          <div style={{
            background: "#fff", padding: "32px", borderRadius: "16px", maxWidth: "420px",
            width: "90%", boxShadow: "0 20px 25px -5px rgba(0, 0, 0, 0.1)"
          }}>
            <div style={{ fontSize: 24, marginBottom: 12 }}>⚠️</div>
            <h2 style={{ margin: "0 0 12px 0", fontSize: 20, color: tag === "Perigoso" ? "#b91c1c" : "#b45309" }}>
              Aviso de Segurança
            </h2>
            <p style={{ margin: "0 0 16px 0", fontSize: 14, color: "#4b5563", lineHeight: "1.5" }}>
              Este destino foi classificado como <b>{tag}</b> pelo sistema. 
              {tag === "Alerta de Cuidado" && " Geralmente, 1 ou 2 alertas podem ser apenas 'falsos positivos' causados por modificações inofensivas no ficheiro, no entanto, recomendamos cautela."}
              {tag === "Perigoso" && " Vários motores de antivírus detetaram ameaças graves neste destino. Não recomendamos o acesso."}
            </p>
            
            <div style={{ display: "flex", flexDirection: "column", gap: 8, marginTop: 24 }}>
              <button 
                onClick={() => setShowModal(false)}
                style={{
                  padding: "12px", borderRadius: "8px", background: "#1a1a1a", 
                  color: "#fff", border: "none", fontWeight: 600, cursor: "pointer"
                }}>
                Voltar em Segurança
              </button>
              <button 
                onClick={() => { setShowModal(false); window.open(item.link, "_blank", "noreferrer"); }}
                style={{
                  padding: "12px", borderRadius: "8px", background: "transparent", 
                  color: "#6b7280", border: "1px solid #e5e7eb", fontWeight: 500, cursor: "pointer"
                }}>
                Entendo os riscos, abrir mesmo assim
              </button>
            </div>
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