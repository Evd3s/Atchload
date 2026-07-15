import { useEffect, useMemo, useState, useRef } from "react"
import axios from "axios"

const API_URL = "http://127.0.0.1:8000"
const CONFIG_KEY = "atchload_config"
const FAVORITOS_KEY = "atchload_favoritos"
const USER_KEY = "atchload_usuario_local"

const DEFAULT_CONFIG = {
  tema: "claro",
  mostrarTags: false,
  mostrarMotivos: false,
  mostrarScore: true,
  filtros: {
    semVideo: false,
    semJogos: false,
    semSoftware: false,
    semDocumentos: false,
    semSociais: false,
    somenteDownload: false,
    positivos: [],
    negativos: [],
  },
}

/* Paleta nova: grafite + ciano do ícone (#00D2FC). */
const TEMAS = {
  claro: {
    bg: "#F6FBFD",
    text: "#10232B",
    muted: "#5E727A",
    mutedSoft: "#8DA1A8",
    card: "#FFFFFF",
    surface: "#ECF6F9",
    border: "#D9E9EE",
    borderStrong: "#B7D6DF",
    input: "#FFFFFF",
    inputBorder: "#D4E7ED",
    inputText: "#10232B",
    shadow: "0 1px 2px rgba(12,36,45,0.04), 0 14px 34px -18px rgba(0,110,140,0.22)",
    shadowHover: "0 2px 5px rgba(12,36,45,0.06), 0 20px 45px -18px rgba(0,110,140,0.30)",
    button: "#10232B",
    buttonText: "#F6FBFD",
    accent: "#00D2FC",
    accentHover: "#00BEE5",
    accentSoft: "#DDF8FF",
    accentText: "#007E98",
    danger: "#D94F45",
  },
  escuro: {
    bg: "#081116",
    text: "#EAF8FB",
    muted: "#9EB3BA",
    mutedSoft: "#6F868E",
    card: "#0E1A20",
    surface: "#12242B",
    border: "#213841",
    borderStrong: "#31525E",
    input: "#0E1A20",
    inputBorder: "#27434D",
    inputText: "#EAF8FB",
    shadow: "0 1px 2px rgba(0,0,0,0.35), 0 18px 42px -22px rgba(0,210,252,0.25)",
    shadowHover: "0 2px 5px rgba(0,0,0,0.40), 0 22px 52px -22px rgba(0,210,252,0.35)",
    button: "#00D2FC",
    buttonText: "#061015",
    accent: "#00D2FC",
    accentHover: "#32DDFF",
    accentSoft: "#0E3440",
    accentText: "#6FE8FF",
    danger: "#FF8178",
  }
}

const CORES = {
  green:  { bg: "#E1F7EA", text: "#21734A", bgDark: "#102D20", textDark: "#7FE3A8" },
  blue:   { bg: "#DDF8FF", text: "#007E98", bgDark: "#0E3440", textDark: "#6FE8FF" },
  orange: { bg: "#FFF1D7", text: "#9A5D00", bgDark: "#362812", textDark: "#FFD18A" },
  red:    { bg: "#FFE6E3", text: "#B83D32", bgDark: "#351A18", textDark: "#FF9B92" },
  gray:   { bg: "#EDF3F5", text: "#61747B", bgDark: "#1A2B31", textDark: "#AABCC2" },
  purple: { bg: "#EEE7FF", text: "#6850A8", bgDark: "#241D3B", textDark: "#B7A7FF" },
}

function carregarJSON(chave, padrao) {
  try {
    const salvo = localStorage.getItem(chave)
    return salvo ? { ...padrao, ...JSON.parse(salvo) } : padrao
  } catch {
    return padrao
  }
}

function limitarTexto(texto, limite = 175) {
  if (!texto) return ""
  if (texto.length <= limite) return texto
  return texto.slice(0, limite).trimEnd() + "..."
}

function normalizarDominioFiltro(valor) {
  return (valor || "")
    .trim()
    .toLowerCase()
    .replace(/^https?:\/\//, "")
    .replace(/^www\./, "")
    .split("/")[0]
    .split("?")[0]
}

function dominioFiltroValido(valor) {
  const limpo = normalizarDominioFiltro(valor)
  return limpo.includes(".") && limpo.length >= 4
}

const Icon = {
  search: (p = {}) => (
    <svg width={p.size || 18} height={p.size || 18} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round">
      <circle cx="11" cy="11" r="7.5" />
      <line x1="21" y1="21" x2="16.2" y2="16.2" />
    </svg>
  ),
  star: (p = {}) => (
    <svg width={p.size || 16} height={p.size || 16} viewBox="0 0 24 24" fill={p.filled ? "currentColor" : "none"} stroke="currentColor" strokeWidth="1.8" strokeLinejoin="round">
      <path d="M12 3.5l2.6 5.4 5.9.8-4.3 4.1 1 5.9-5.2-2.8-5.2 2.8 1-5.9-4.3-4.1 5.9-.8L12 3.5z" />
    </svg>
  ),
  moon: (p = {}) => (
    <svg width={p.size || 16} height={p.size || 16} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
      <path d="M20 14.5A8.5 8.5 0 1 1 9.5 4a6.8 6.8 0 0 0 10.5 10.5z" />
    </svg>
  ),
  sun: (p = {}) => (
    <svg width={p.size || 16} height={p.size || 16} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round">
      <circle cx="12" cy="12" r="4.3" />
      <line x1="12" y1="2.5" x2="12" y2="4.8" /><line x1="12" y1="19.2" x2="12" y2="21.5" />
      <line x1="2.5" y1="12" x2="4.8" y2="12" /><line x1="19.2" y1="12" x2="21.5" y2="12" />
      <line x1="5.1" y1="5.1" x2="6.7" y2="6.7" /><line x1="17.3" y1="17.3" x2="18.9" y2="18.9" />
      <line x1="5.1" y1="18.9" x2="6.7" y2="17.3" /><line x1="17.3" y1="6.7" x2="18.9" y2="5.1" />
    </svg>
  ),
  sliders: (p = {}) => (
    <svg width={p.size || 16} height={p.size || 16} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round">
      <line x1="4" y1="6" x2="20" y2="6" /><circle cx="9" cy="6" r="2.2" fill={p.bgFill || "none"} />
      <line x1="4" y1="12" x2="20" y2="12" /><circle cx="16" cy="12" r="2.2" fill={p.bgFill || "none"} />
      <line x1="4" y1="18" x2="20" y2="18" /><circle cx="11" cy="18" r="2.2" fill={p.bgFill || "none"} />
    </svg>
  ),
  arrowDown: (p = {}) => (
    <svg width={p.size || 14} height={p.size || 14} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round">
      <line x1="12" y1="4" x2="12" y2="16" /><polyline points="6 11 12 17 18 11" /><line x1="5" y1="20.5" x2="19" y2="20.5" />
    </svg>
  ),
  external: (p = {}) => (
    <svg width={p.size || 13} height={p.size || 13} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M14 4h6v6" /><path d="M20 4L10 14" /><path d="M19 13v6a1 1 0 0 1-1 1H6a1 1 0 0 1-1-1V7a1 1 0 0 1 1-1h6" />
    </svg>
  ),
  check: (p = {}) => (
    <svg width={p.size || 12} height={p.size || 12} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="3" strokeLinecap="round" strokeLinejoin="round">
      <polyline points="20 6 9 17 4 12" />
    </svg>
  ),
  link: (p = {}) => (
    <svg width={p.size || 12} height={p.size || 12} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round">
      <path d="M9.5 14.5l5-5" />
      <path d="M11 6l1.5-1.5a3.5 3.5 0 0 1 5 5L16 11" />
      <path d="M13 18l-1.5 1.5a3.5 3.5 0 0 1-5-5L8 13" />
    </svg>
  ),
  play: (p = {}) => (
    <svg width={p.size || 12} height={p.size || 12} viewBox="0 0 24 24" fill="currentColor" stroke="none">
      <path d="M7 4.5v15l13-7.5z" />
    </svg>
  ),
  alert: (p = {}) => (
    <svg width={p.size || 12} height={p.size || 12} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M12 3.5l9.5 16.5h-19z" /><line x1="12" y1="9.5" x2="12" y2="14" /><circle cx="12" cy="17" r="0.6" fill="currentColor" />
    </svg>
  ),
  store: (p = {}) => (
    <svg width={p.size || 12} height={p.size || 12} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M4 10h16l-1.2-5H5.2L4 10z" /><path d="M6 10v9h12v-9" /><path d="M9 19v-5h6v5" />
    </svg>
  ),
  user: (p = {}) => (
    <svg width={p.size || 18} height={p.size || 18} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.9" strokeLinecap="round" strokeLinejoin="round">
      <circle cx="12" cy="8" r="4" />
      <path d="M4.5 20c1.6-4.1 4.3-6 7.5-6s5.9 1.9 7.5 6" />
    </svg>
  ),
  logout: (p = {}) => (
    <svg width={p.size || 16} height={p.size || 16} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.9" strokeLinecap="round" strokeLinejoin="round">
      <path d="M10 17l5-5-5-5" />
      <path d="M15 12H3" />
      <path d="M21 4v16" />
    </svg>
  ),
}

function Tag({ cor, texto, icon, escuro }) {
  const c = CORES[cor] || CORES.gray
  return (
    <span style={{
      display: "inline-flex",
      alignItems: "center",
      gap: 5,
      fontSize: 11.5,
      fontWeight: 700,
      letterSpacing: "0.01em",
      padding: "5px 10px 5px 8px",
      borderRadius: 8,
      background: escuro ? c.bgDark : c.bg,
      color: escuro ? c.textDark : c.text,
      whiteSpace: "nowrap",
      lineHeight: 1
    }}>
      {icon}
      {texto}
    </span>
  )
}

function ScoreBadge({ score, tema }) {
  const cor = score >= 80 ? CORES.green : score >= 60 ? CORES.blue : score >= 40 ? CORES.orange : CORES.red
  const corHex = tema.modoEscuro ? cor.textDark : cor.text
  const angulo = -90 + (Math.min(100, Math.max(0, score)) / 100) * 180

  return (
    <div style={{ width: 54, flexShrink: 0, display: "flex", flexDirection: "column", alignItems: "center", gap: 4 }}>
      <div style={{ position: "relative", width: 46, height: 26 }}>
        <svg width="46" height="26" viewBox="0 0 46 26" style={{ position: "absolute", top: 0, left: 0 }}>
          <path d="M3 23 A20 20 0 0 1 43 23" fill="none" stroke={tema.border} strokeWidth="3" strokeLinecap="round" />
          <path
            d="M3 23 A20 20 0 0 1 43 23"
            fill="none"
            stroke={corHex}
            strokeWidth="3"
            strokeLinecap="round"
            strokeDasharray={`${(score / 100) * 62.8} 62.8`}
          />
        </svg>
        <div style={{
          position: "absolute",
          bottom: 0, left: "50%",
          width: 2, height: 16,
          background: corHex,
          borderRadius: 2,
          transformOrigin: "bottom center",
          transform: `translateX(-50%) rotate(${angulo}deg)`,
          transition: "transform 0.5s cubic-bezier(.34,1.4,.64,1)"
        }} />
      </div>
      <div style={{ fontSize: 15, fontWeight: 800, color: corHex, fontVariantNumeric: "tabular-nums", letterSpacing: "-0.02em" }}>
        {score}
      </div>
    </div>
  )
}

function classificarResultado(r) {
  if (r.oficial) return { cor: "green", texto: "Oficial", icon: <Icon.check /> }
  if (r.loja_jogo) return { cor: "blue", texto: "Loja oficial", icon: <Icon.store /> }
  if (r.download_direto) return { cor: "green", texto: "Arquivo direto", icon: <Icon.arrowDown /> }
  if (r.tem_download_na_pagina || r.tem_link_util) return { cor: "blue", texto: "Link encontrado", icon: <Icon.link /> }
  if (r.youtube) return { cor: "purple", texto: "YouTube", icon: <Icon.play /> }
  if (r.social_compartilhamento) return { cor: "blue", texto: "Post útil", icon: <Icon.link /> }
  if (r.fonte_confiavel) return { cor: "green", texto: "Fonte conhecida", icon: <Icon.check /> }
  return { cor: "gray", texto: "Resultado", icon: null }
}

function TagsAvancadas({ r, escuro }) {
  return (
    <div style={{ display: "flex", flexWrap: "wrap", gap: 6, marginTop: 12 }}>
      {r.oficial && <Tag cor="green" texto="Oficial" icon={<Icon.check />} escuro={escuro} />}
      {r.loja_jogo && <Tag cor="blue" texto="Loja/plataforma" icon={<Icon.store />} escuro={escuro} />}
      {r.fonte_confiavel && !r.oficial && !r.loja_jogo && <Tag cor="green" texto="Fonte conhecida" icon={<Icon.check />} escuro={escuro} />}
      {r.download_direto && <Tag cor="green" texto="Arquivo direto" icon={<Icon.arrowDown />} escuro={escuro} />}
      {!r.download_direto && (r.tem_download_na_pagina || r.tem_link_util) && <Tag cor="blue" texto="Link na página" icon={<Icon.link />} escuro={escuro} />}
      {r.youtube && <Tag cor="purple" texto="YouTube" icon={<Icon.play />} escuro={escuro} />}
      {r.streaming && <Tag cor="purple" texto="Streaming" icon={<Icon.play />} escuro={escuro} />}
      {r.social_compartilhamento && <Tag cor="blue" texto="Post com link" icon={<Icon.link />} escuro={escuro} />}
      {r.catalogo && <Tag cor="gray" texto="Catálogo" escuro={escuro} />}
      {r.encurtador && <Tag cor="orange" texto="Encurtador" icon={<Icon.alert />} escuro={escuro} />}
      {r.propaganda === "limpo" && <Tag cor="green" texto="Sem anúncios" icon={<Icon.check />} escuro={escuro} />}
      {r.propaganda === "moderado" && <Tag cor="orange" texto="Poucos anúncios" escuro={escuro} />}
      {r.propaganda === "agressivo" && <Tag cor="red" texto="Muitos anúncios" icon={<Icon.alert />} escuro={escuro} />}
    </div>
  )
}

function getSecurityColor(tag) {
  if (tag === "Seguro / Confiável") return "green"
  if (tag === "Alerta de Cuidado") return "orange"
  if (tag === "Perigoso") return "red"
  if (tag === "Enviado ao VT") return "blue"
  if (tag === "Limite do VT" || tag === "Erro na API" || tag === "VT indisponível") return "orange"
  return "gray"
}

function isSecurityRisk(tag) {
  return tag === "Perigoso" || tag === "Alerta de Cuidado"
}

function isSecurityAnalyzed(tag) {
  return tag === "Seguro / Confiável" || tag === "Alerta de Cuidado" || tag === "Perigoso"
}

function securityText(tag) {
  if (!tag || tag === "Aguardando Análise") return "Não verificado"
  return tag
}

function ModalBase({ tema, children }) {
  return (
    <div style={{
      position: "fixed",
      inset: 0,
      background: tema.modoEscuro ? "rgba(1,8,12,0.78)" : "rgba(8,17,22,0.52)",
      backdropFilter: "blur(8px)",
      display: "flex",
      alignItems: "center",
      justifyContent: "center",
      zIndex: 9999,
      padding: 18,
      animation: "fadeUp 0.18s ease both"
    }}>
      <div style={{
        width: "min(520px, 100%)",
        background: tema.card,
        color: tema.text,
        border: `1px solid ${tema.border}`,
        borderRadius: 20,
        boxShadow: tema.shadowHover,
        padding: 24
      }}>
        {children}
      </div>
    </div>
  )
}

function Card({ r, tema, config, favorito, alternarFavorito, index }) {
  const [hover, setHover] = useState(false)
  const [tagSeg, setTagSeg] = useState(r.tag_atchload || "Aguardando Análise")
  const [hash, setHash] = useState(r.hash || null)
  const [stats, setStats] = useState({ malicious: r.malicious || 0, suspicious: r.suspicious || 0 })
  const [scoreAtual, setScoreAtual] = useState(r.score || 0)
  const [verificando, setVerificando] = useState(false)
  const [modalRisco, setModalRisco] = useState(false)
  const [modalDetalhes, setModalDetalhes] = useState(false)
  const [linkPendente, setLinkPendente] = useState(null)

  useEffect(() => {
    setTagSeg(r.tag_atchload || "Aguardando Análise")
    setHash(r.hash || null)
    setStats({ malicious: r.malicious || 0, suspicious: r.suspicious || 0 })
    setScoreAtual(r.score || 0)
    setVerificando(false)
    setModalRisco(false)
    setModalDetalhes(false)
    setLinkPendente(null)
  }, [r.link, r.score, r.tag_atchload, r.hash, r.malicious, r.suspicious])

  const escuro = tema.modoEscuro
  const downloadHref = r.download_url ? `${API_URL}/baixar?url=${encodeURIComponent(r.download_url)}` : ""
  const descricao = limitarTexto(r.descricao, 175)
  const analisado = isSecurityAnalyzed(tagSeg)
  const risco = isSecurityRisk(tagSeg)

  const aplicarResultadoSeguranca = (data) => {
    const novaTag = data.tag_atchload || "Erro na API"
    setTagSeg(novaTag)
    setHash(data.hash || null)
    setStats({ malicious: data.malicious || 0, suspicious: data.suspicious || 0 })

    setScoreAtual(prev => {
      if (novaTag === "Perigoso") return Math.min(prev, 12)
      if (novaTag === "Alerta de Cuidado") return Math.max(0, prev - 22)
      if (novaTag === "Seguro / Confiável") return Math.min(100, prev + 3)
      return prev
    })
  }

  const verificarSeguranca = async () => {
    if (verificando) return
    setVerificando(true)
    try {
      const res = await axios.get(`${API_URL}/verificar`, { params: { url: r.link } })
      aplicarResultadoSeguranca(res.data || {})
    } catch {
      setTagSeg("Erro na API")
    } finally {
      setVerificando(false)
    }
  }

  const abrirComProtecao = (e, destino) => {
    if (risco) {
      e.preventDefault()
      setLinkPendente(destino)
      setModalRisco(true)
    }
  }

  const favoritoAtualizado = {
    ...r,
    score: scoreAtual,
    tag_atchload: tagSeg,
    hash,
    malicious: stats.malicious,
    suspicious: stats.suspicious
  }

  return (
    <>
      <article
        onMouseEnter={() => setHover(true)}
        onMouseLeave={() => setHover(false)}
        style={{
          border: `1px solid ${risco ? (tagSeg === "Perigoso" ? (escuro ? CORES.red.textDark : CORES.red.text) : (escuro ? CORES.orange.textDark : CORES.orange.text)) : (hover ? tema.borderStrong : tema.border)}`,
          borderRadius: 18,
          padding: "19px 20px",
          marginBottom: 12,
          background: tema.card,
          boxShadow: hover ? tema.shadowHover : tema.shadow,
          transform: hover ? "translateY(-2px)" : "translateY(0)",
          transition: "transform 0.18s ease, box-shadow 0.18s ease, border-color 0.18s ease",
          animation: `cardIn 0.42s cubic-bezier(.22,1,.36,1) both`,
          animationDelay: `${Math.min(index * 0.035, 0.3)}s`,
        }}
      >
        <div style={{ display: "flex", gap: 16, alignItems: "flex-start" }}>
          <div style={{ flex: 1, minWidth: 0 }}>
            <div style={{ display: "flex", alignItems: "center", gap: 9, marginBottom: 8, flexWrap: "wrap" }}>
              <span style={{ fontSize: 12.5, color: tema.mutedSoft, fontWeight: 700 }}>
                {r.dominio || r.dominio_limpo}
              </span>
            </div>

            <a
              href={r.link}
              target="_blank"
              rel="noreferrer"
              onClick={(e) => abrirComProtecao(e, r.link)}
              style={{
                display: "inline-flex",
                alignItems: "baseline",
                gap: 6,
                fontSize: 16.5,
                lineHeight: 1.3,
                fontWeight: 800,
                marginBottom: 7,
                color: tema.text,
                textDecoration: "none",
              }}
            >
              <span style={{
                backgroundImage: `linear-gradient(${tema.accent}, ${tema.accent})`,
                backgroundSize: hover ? "100% 2px" : "0% 2px",
                backgroundRepeat: "no-repeat",
                backgroundPosition: "0 100%",
                transition: "background-size 0.2s ease",
                paddingBottom: 1
              }}>
                {r.titulo || "Resultado sem título"}
              </span>
              <span style={{ color: tema.mutedSoft, flexShrink: 0 }}><Icon.external /></span>
            </a>

            {r.descricao && (
              <p style={{ fontSize: 13.5, color: tema.muted, margin: 0, lineHeight: 1.6 }}>
                {descricao}
              </p>
            )}

            <div style={{ display: "flex", flexWrap: "wrap", gap: 8, marginTop: 14 }}>
              {r.download_direto && r.download_url && (
                <a
                  href={downloadHref}
                  onClick={(e) => abrirComProtecao(e, downloadHref)}
                  style={{
                    display: "inline-flex",
                    alignItems: "center",
                    gap: 6,
                    padding: "8px 14px",
                    borderRadius: 10,
                    fontSize: 13,
                    fontWeight: 800,
                    background: escuro ? CORES.green.bgDark : CORES.green.bg,
                    color: escuro ? CORES.green.textDark : CORES.green.text,
                    textDecoration: "none",
                    transition: "filter 0.15s"
                  }}
                >
                  <Icon.arrowDown size={13} /> Baixar arquivo
                </a>
              )}

              <button
                onClick={() => alternarFavorito(favoritoAtualizado)}
                title={favorito ? "Remover dos favoritos" : "Adicionar aos favoritos"}
                style={{
                  display: "inline-flex",
                  alignItems: "center",
                  gap: 6,
                  padding: "8px 14px",
                  borderRadius: 10,
                  fontSize: 13,
                  fontWeight: 800,
                  border: `1px solid ${favorito ? "transparent" : tema.border}`,
                  background: favorito ? tema.accentSoft : "transparent",
                  color: favorito ? tema.accentText : tema.muted,
                  cursor: "pointer",
                  transition: "border-color 0.15s, color 0.15s, background 0.15s"
                }}
              >
                <Icon.star size={13} filled={favorito} />
                {favorito ? "Salvo" : "Favoritar"}
              </button>

              {!analisado && (
                <button
                  onClick={verificarSeguranca}
                  disabled={verificando}
                  style={{
                    display: "inline-flex",
                    alignItems: "center",
                    gap: 6,
                    padding: "8px 14px",
                    borderRadius: 10,
                    fontSize: 13,
                    fontWeight: 800,
                    border: `1px solid ${tema.border}`,
                    background: verificando ? tema.surface : "transparent",
                    color: verificando ? tema.mutedSoft : tema.accentText,
                    cursor: verificando ? "wait" : "pointer",
                  }}
                >
                  {verificando ? "Verificando..." : "Verificar segurança"}
                </button>
              )}

              {analisado && (
                <button
                  onClick={() => setModalDetalhes(true)}
                  style={{
                    display: "inline-flex",
                    alignItems: "center",
                    gap: 6,
                    padding: "8px 14px",
                    borderRadius: 10,
                    fontSize: 13,
                    fontWeight: 800,
                    border: `1px solid ${tema.border}`,
                    background: "transparent",
                    color: tema.muted,
                    cursor: "pointer",
                  }}
                >
                  Relatório
                </button>
              )}
            </div>

            {config.mostrarTags && (
              <>
                <TagsAvancadas r={r} escuro={escuro} />
                <div style={{ display: "flex", flexWrap: "wrap", gap: 6, marginTop: 8 }}>
                  <Tag cor={getSecurityColor(tagSeg)} texto={`Segurança: ${securityText(tagSeg)}`} escuro={escuro} />
                </div>
              </>
            )}

            {config.mostrarMotivos && r.motivos && r.motivos.length > 0 && (
              <div style={{
                fontSize: 11,
                color: tema.mutedSoft,
                marginTop: 12,
                lineHeight: 1.7,
                paddingTop: 10,
                borderTop: `1px dashed ${tema.border}`,
                fontFamily: "ui-monospace, 'SF Mono', Consolas, monospace"
              }}>
                {r.motivos.join("  ·  ")}
              </div>
            )}
          </div>

          {config.mostrarScore && (
            <ScoreBadge score={scoreAtual} tema={{ ...tema, modoEscuro: escuro }} />
          )}
        </div>
      </article>

      {modalRisco && (
        <ModalBase tema={tema}>
          <h2 style={{ margin: "0 0 10px", color: tagSeg === "Perigoso" ? (escuro ? CORES.red.textDark : CORES.red.text) : (escuro ? CORES.orange.textDark : CORES.orange.text), fontSize: 21 }}>
            Aviso de segurança
          </h2>
          <p style={{ color: tema.muted, lineHeight: 1.6, margin: "0 0 12px" }}>
            O VirusTotal classificou este destino como <strong style={{ color: tema.text }}>{tagSeg}</strong>. Isso não prova sozinho que o site é malicioso, mas indica que vale ter cuidado antes de abrir ou baixar qualquer arquivo.
          </p>
          <div style={{ display: "flex", flexWrap: "wrap", gap: 10, marginTop: 20 }}>
            <button onClick={() => setModalRisco(false)} style={{ padding: "11px 15px", borderRadius: 11, border: "none", background: tema.button, color: tema.buttonText, fontWeight: 800, cursor: "pointer" }}>
              Voltar em segurança
            </button>
            <button onClick={() => { const alvo = linkPendente || r.link; setModalRisco(false); window.open(alvo, "_blank") }} style={{ padding: "11px 15px", borderRadius: 11, border: `1px solid ${tema.border}`, background: "transparent", color: tema.muted, fontWeight: 800, cursor: "pointer" }}>
              Entendo, abrir mesmo assim
            </button>
          </div>
        </ModalBase>
      )}

      {modalDetalhes && (
        <ModalBase tema={tema}>
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", gap: 12, marginBottom: 14 }}>
            <h2 style={{ margin: 0, fontSize: 20 }}>Relatório de segurança</h2>
            <button onClick={() => setModalDetalhes(false)} style={{ border: "none", background: "transparent", color: tema.muted, cursor: "pointer", fontSize: 20, lineHeight: 1 }}>×</button>
          </div>

          <div style={{ display: "flex", flexWrap: "wrap", gap: 8, marginBottom: 16 }}>
            <Tag cor={getSecurityColor(tagSeg)} texto={securityText(tagSeg)} icon={tagSeg === "Seguro / Confiável" ? <Icon.check /> : isSecurityRisk(tagSeg) ? <Icon.alert /> : null} escuro={escuro} />
            <Tag cor={stats.malicious > 0 ? "red" : "gray"} texto={`${stats.malicious || 0} malicioso`} escuro={escuro} />
            <Tag cor={stats.suspicious > 0 ? "orange" : "gray"} texto={`${stats.suspicious || 0} suspeito`} escuro={escuro} />
          </div>

          <p style={{ color: tema.muted, lineHeight: 1.6, margin: "0 0 14px", fontSize: 13.5 }}>
            A análise vem do VirusTotal. Use como sinal de segurança, não como garantia absoluta.
          </p>

          <div style={{
            border: `1px solid ${tema.border}`,
            borderRadius: 14,
            padding: 12,
            background: escuro ? "#071015" : "#F2FAFC",
            color: tema.accentText,
            fontFamily: "ui-monospace, 'SF Mono', Consolas, monospace",
            fontSize: 11.5,
            lineHeight: 1.6,
            wordBreak: "break-all"
          }}>
            <strong style={{ color: tema.muted, display: "block", marginBottom: 4 }}>SHA-256 / identificador retornado:</strong>
            {hash || "Não disponível"}
          </div>
        </ModalBase>
      )}
    </>
  )
}

function Toggle({ ativo, onClick, label, tema }) {
  return (
    <button
      onClick={onClick}
      style={{
        display: "flex",
        justifyContent: "space-between",
        alignItems: "center",
        gap: 18,
        width: "100%",
        padding: "12px 2px",
        background: "transparent",
        border: "none",
        borderBottom: `1px solid ${tema.border}`,
        cursor: "pointer",
        color: tema.text,
        fontSize: 13.5,
        fontWeight: 600,
        textAlign: "left"
      }}
    >
      <span>{label}</span>
      <span style={{
        width: 38,
        height: 22,
        borderRadius: 999,
        background: ativo ? tema.accent : tema.border,
        position: "relative",
        transition: "background 0.2s",
        flexShrink: 0
      }}>
        <span style={{
          width: 16,
          height: 16,
          borderRadius: "50%",
          background: "#fff",
          position: "absolute",
          top: 3,
          left: ativo ? 19 : 3,
          transition: "left 0.2s cubic-bezier(.4,0,.2,1)",
          boxShadow: "0 1px 3px rgba(0,0,0,0.25)"
        }} />
      </span>
    </button>
  )
}

function IconButton({ onClick, active, children, tema, label, title }) {
  const [hover, setHover] = useState(false)
  return (
    <button
      onClick={onClick}
      onMouseEnter={() => setHover(true)}
      onMouseLeave={() => setHover(false)}
      title={title}
      style={{
        display: "flex",
        alignItems: "center",
        gap: 7,
        padding: label ? "9px 14px" : "9px 10px",
        minHeight: 38,
        borderRadius: 11,
        border: `1px solid ${active ? tema.accent : (hover ? tema.borderStrong : tema.border)}`,
        background: active ? tema.accentSoft : tema.card,
        color: active ? tema.accentText : tema.text,
        cursor: "pointer",
        fontWeight: 700,
        fontSize: 13,
        transition: "border-color 0.15s, background 0.15s",
        boxShadow: tema.shadow
      }}
    >
      {children}
      {label}
    </button>
  )
}


function avatarLabel(usuario) {
  if (!usuario) return ""
  const base = usuario.nome || usuario.email || "U"
  return base.trim().slice(0, 1).toUpperCase()
}

function UserAvatarButton({ usuario, tema, active, onClick }) {
  return (
    <button
      onClick={onClick}
      title={usuario ? "Conta local" : "Entrar"}
      style={{
        width: 40,
        height: 40,
        borderRadius: "50%",
        border: `1px solid ${active ? tema.accent : tema.border}`,
        background: usuario ? tema.accentSoft : tema.card,
        color: usuario ? tema.accentText : tema.muted,
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        cursor: "pointer",
        boxShadow: tema.shadow,
        fontWeight: 900,
        fontSize: 14,
        overflow: "hidden"
      }}
    >
      {usuario ? avatarLabel(usuario) : <Icon.user size={19} />}
    </button>
  )
}

function UserMenu({ tema, usuario, onEntrar, onRegistrar, onSair, config, atualizarConfig }) {
  return (
    <section className="user-panel" style={{
      position: "absolute",
      right: 0,
      top: "calc(100% + 10px)",
      width: 360,
      zIndex: 45,
      background: tema.card,
      border: `1px solid ${tema.border}`,
      borderRadius: 18,
      padding: "14px 18px 8px",
      boxShadow: tema.shadowHover,
      animation: "fadeUp 0.22s ease both"
    }}>
      <div style={{ display: "flex", alignItems: "center", gap: 12, paddingBottom: 12, borderBottom: `1px solid ${tema.border}` }}>
        <div style={{
          width: 42,
          height: 42,
          borderRadius: "50%",
          background: usuario ? tema.accentSoft : tema.surface,
          color: usuario ? tema.accentText : tema.muted,
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          fontWeight: 900
        }}>
          {usuario ? avatarLabel(usuario) : <Icon.user size={20} />}
        </div>
        <div style={{ flex: 1, minWidth: 0 }}>
          <div style={{ fontSize: 14, fontWeight: 900, color: tema.text }}>
            {usuario ? (usuario.nome || "Usuário local") : "Você não está logado"}
          </div>
          <div style={{ fontSize: 12, color: tema.mutedSoft, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
            {usuario ? usuario.email : "Conta local apenas para demonstração"}
          </div>
        </div>
      </div>

      {!usuario ? (
        <div style={{ display: "flex", gap: 8, padding: "12px 0", borderBottom: `1px solid ${tema.border}` }}>
          <button onClick={onEntrar} style={{ flex: 1, padding: "10px 12px", borderRadius: 11, border: "none", background: tema.button, color: tema.buttonText, fontWeight: 900, cursor: "pointer" }}>
            Entrar
          </button>
          <button onClick={onRegistrar} style={{ flex: 1, padding: "10px 12px", borderRadius: 11, border: `1px solid ${tema.border}`, background: "transparent", color: tema.text, fontWeight: 900, cursor: "pointer" }}>
            Registrar
          </button>
        </div>
      ) : (
        <div style={{ display: "flex", gap: 8, padding: "12px 0", borderBottom: `1px solid ${tema.border}` }}>
          <button onClick={onRegistrar} style={{ flex: 1, padding: "10px 12px", borderRadius: 11, border: `1px solid ${tema.border}`, background: "transparent", color: tema.text, fontWeight: 900, cursor: "pointer" }}>
            Trocar conta
          </button>
          <button onClick={onSair} style={{ flex: 1, padding: "10px 12px", borderRadius: 11, border: "none", background: tema.surface, color: tema.muted, fontWeight: 900, cursor: "pointer" }}>
            Sair
          </button>
        </div>
      )}

      <div style={{ paddingTop: 4 }}>
        <div style={{ display: "flex", alignItems: "center", gap: 8, fontSize: 13, fontWeight: 900, color: tema.text, margin: "8px 0 2px" }}>
          <Icon.sliders size={14} /> Configurações
        </div>
        <Toggle tema={tema} label="Mostrar tags técnicas" ativo={config.mostrarTags} onClick={() => atualizarConfig("mostrarTags", !config.mostrarTags)} />
        <Toggle tema={tema} label="Mostrar motivos do score" ativo={config.mostrarMotivos} onClick={() => atualizarConfig("mostrarMotivos", !config.mostrarMotivos)} />
        <Toggle tema={tema} label="Mostrar score" ativo={config.mostrarScore} onClick={() => atualizarConfig("mostrarScore", !config.mostrarScore)} />
        <p style={{ fontSize: 11.5, color: tema.mutedSoft, margin: "10px 0 4px", lineHeight: 1.45 }}>
          Login e preferências são salvos apenas neste navegador.
        </p>
      </div>
    </section>
  )
}

function AuthModal({ tema, modoInicial, onClose, onSalvar }) {
  const [modo, setModo] = useState(modoInicial || "login")
  const [nome, setNome] = useState("")
  const [email, setEmail] = useState("")
  const [senha, setSenha] = useState("")
  const [erro, setErro] = useState("")

  useEffect(() => {
    setModo(modoInicial || "login")
    setErro("")
  }, [modoInicial])

  const confirmar = () => {
    const emailLimpo = email.trim().toLowerCase()
    if (!emailLimpo || !emailLimpo.includes("@")) {
      setErro("Digite um e-mail válido.")
      return
    }
    if (!senha.trim()) {
      setErro("Digite uma senha.")
      return
    }
    if (modo === "registro" && !nome.trim()) {
      setErro("Digite seu nome.")
      return
    }

    const usuario = {
      nome: modo === "registro" ? nome.trim() : (nome.trim() || emailLimpo.split("@")[0]),
      email: emailLimpo,
      criadoEm: new Date().toISOString(),
      localDemo: true
    }
    onSalvar(usuario)
  }

  return (
    <ModalBase tema={tema}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", gap: 12, marginBottom: 16 }}>
        <div>
          <h2 style={{ margin: 0, fontSize: 22 }}>{modo === "registro" ? "Criar conta" : "Entrar"}</h2>
          <p style={{ margin: "5px 0 0", color: tema.muted, fontSize: 13.5 }}>
            Demonstração local, sem banco de dados.
          </p>
        </div>
        <button onClick={onClose} style={{ border: "none", background: "transparent", color: tema.muted, cursor: "pointer", fontSize: 22, lineHeight: 1 }}>×</button>
      </div>

      {modo === "registro" && (
        <label style={{ display: "block", marginBottom: 10 }}>
          <span style={{ display: "block", fontSize: 12.5, fontWeight: 800, color: tema.muted, marginBottom: 5 }}>Nome</span>
          <input value={nome} onChange={e => setNome(e.target.value)} placeholder="Seu nome" style={{ width: "100%", padding: "12px 13px", borderRadius: 12, border: `1px solid ${tema.border}`, background: tema.input, color: tema.inputText, outline: "none", fontWeight: 700 }} />
        </label>
      )}

      <label style={{ display: "block", marginBottom: 10 }}>
        <span style={{ display: "block", fontSize: 12.5, fontWeight: 800, color: tema.muted, marginBottom: 5 }}>E-mail</span>
        <input value={email} onChange={e => setEmail(e.target.value)} placeholder="exemplo@email.com" style={{ width: "100%", padding: "12px 13px", borderRadius: 12, border: `1px solid ${tema.border}`, background: tema.input, color: tema.inputText, outline: "none", fontWeight: 700 }} />
      </label>

      <label style={{ display: "block", marginBottom: 10 }}>
        <span style={{ display: "block", fontSize: 12.5, fontWeight: 800, color: tema.muted, marginBottom: 5 }}>Senha</span>
        <input type="password" value={senha} onChange={e => setSenha(e.target.value)} placeholder="Senha local de exemplo" onKeyDown={e => e.key === "Enter" && confirmar()} style={{ width: "100%", padding: "12px 13px", borderRadius: 12, border: `1px solid ${tema.border}`, background: tema.input, color: tema.inputText, outline: "none", fontWeight: 700 }} />
      </label>

      {erro && <p style={{ color: tema.danger, fontSize: 13, fontWeight: 800, margin: "4px 0 10px" }}>{erro}</p>}

      <button onClick={confirmar} style={{ width: "100%", padding: "12px 14px", borderRadius: 12, border: "none", background: tema.button, color: tema.buttonText, fontWeight: 900, cursor: "pointer", marginTop: 6 }}>
        {modo === "registro" ? "Registrar" : "Entrar"}
      </button>

      <button onClick={() => { setModo(modo === "registro" ? "login" : "registro"); setErro("") }} style={{ width: "100%", padding: "11px 14px", borderRadius: 12, border: "none", background: "transparent", color: tema.accentText, fontWeight: 900, cursor: "pointer", marginTop: 8 }}>
        {modo === "registro" ? "Já tenho conta" : "Criar conta local"}
      </button>
    </ModalBase>
  )
}



function ChipInput({ tema, titulo, descricao, valor, onChange, placeholder, tipo }) {
  const [texto, setTexto] = useState("")
  const [selecionado, setSelecionado] = useState(null)
  const inputChipRef = useRef(null)

  const adicionar = () => {
    const limpo = normalizarDominioFiltro(texto)
    if (!dominioFiltroValido(limpo)) return
    if (!valor.includes(limpo)) onChange([...valor, limpo])
    setTexto("")
    setSelecionado(null)
  }

  const remover = (dom) => {
    onChange(valor.filter(v => v !== dom))
    setSelecionado(null)
  }

  const onKeyDown = (e) => {
    if (e.key === "Enter") {
      e.preventDefault()
      adicionar()
      return
    }

    if ((e.key === "Backspace" || e.key === "Delete") && selecionado) {
      e.preventDefault()
      remover(selecionado)
      return
    }

    if (e.key === "Backspace" && !texto && valor.length > 0) {
      e.preventDefault()
      if (selecionado === valor[valor.length - 1]) remover(selecionado)
      else setSelecionado(valor[valor.length - 1])
    }
  }

  const cor = tipo === "positivo" ? CORES.blue : CORES.red

  return (
    <div style={{ padding: "13px 0", borderBottom: `1px solid ${tema.border}` }}>
      <div style={{ fontSize: 13, fontWeight: 800, color: tema.text, marginBottom: 4 }}>
        {titulo}
      </div>
      <div style={{ fontSize: 11.5, color: tema.mutedSoft, lineHeight: 1.45, marginBottom: 9 }}>
        {descricao}
      </div>

      <div
        onClick={() => setSelecionado(null)}
        style={{
          display: "flex",
          alignItems: "center",
          flexWrap: "wrap",
          gap: 7,
          minHeight: 42,
          padding: "7px 9px",
          border: `1px solid ${tema.border}`,
          borderRadius: 13,
          background: tema.input,
          cursor: "text"
        }}
      >
        {valor.map(dom => {
          const ativo = selecionado === dom
          return (
            <button
              key={dom}
              type="button"
              onClick={(e) => {
                e.stopPropagation()
                setSelecionado(ativo ? null : dom)
                setTimeout(() => inputChipRef.current?.focus(), 0)
              }}
              title="Clique e aperte Backspace/Delete para remover"
              style={{
                border: `1px solid ${ativo ? cor.text : "transparent"}`,
                background: tema.modoEscuro ? cor.bgDark : cor.bg,
                color: tema.modoEscuro ? cor.textDark : cor.text,
                borderRadius: 999,
                padding: "6px 10px",
                fontSize: 12.5,
                fontWeight: 800,
                cursor: "pointer"
              }}
            >
              {dom}
            </button>
          )
        })}

        <input
          ref={inputChipRef}
          value={texto}
          onChange={e => {
            setTexto(e.target.value.toLowerCase())
            setSelecionado(null)
          }}
          onKeyDown={onKeyDown}
          onBlur={() => { if (dominioFiltroValido(texto)) adicionar() }}
          placeholder={valor.length ? "" : placeholder}
          style={{
            flex: 1,
            minWidth: 150,
            border: "none",
            outline: "none",
            background: "transparent",
            color: tema.inputText,
            fontSize: 13.5,
            fontWeight: 700,
            height: 28
          }}
        />
      </div>
    </div>
  )
}

function FiltrosPanel({ tema, filtros, atualizarFiltro }) {
  return (
    <section className="filter-panel-mobile" style={{
      position: "absolute",
      top: "calc(100% + 12px)",
      left: 0,
      width: "min(620px, calc(100vw - 40px))",
      zIndex: 35,
      background: tema.card,
      border: `1px solid ${tema.border}`,
      borderRadius: 18,
      padding: "6px 18px 14px",
      boxShadow: tema.shadowHover,
      animation: "fadeUp 0.22s ease both"
    }}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "baseline", gap: 12, padding: "10px 0 2px" }}>
        <div>
          <h3 style={{ margin: 0, fontSize: 15, color: tema.text }}>Filtros da busca</h3>
          <p style={{ margin: "4px 0 0", color: tema.mutedSoft, fontSize: 12.2, lineHeight: 1.4 }}>
            Ajuste o que deve sumir, ou ensine domínios que quer priorizar.
          </p>
        </div>
      </div>

      <Toggle tema={tema} label="Ocultar vídeos, streaming e YouTube" ativo={filtros.semVideo} onClick={() => atualizarFiltro("semVideo", !filtros.semVideo)} />
      <Toggle tema={tema} label="Ocultar jogos e lojas de jogos" ativo={filtros.semJogos} onClick={() => atualizarFiltro("semJogos", !filtros.semJogos)} />
      <Toggle tema={tema} label="Ocultar programas/software" ativo={filtros.semSoftware} onClick={() => atualizarFiltro("semSoftware", !filtros.semSoftware)} />
      <Toggle tema={tema} label="Ocultar PDFs, artigos e documentos" ativo={filtros.semDocumentos} onClick={() => atualizarFiltro("semDocumentos", !filtros.semDocumentos)} />
      <Toggle tema={tema} label="Ocultar redes sociais e posts" ativo={filtros.semSociais} onClick={() => atualizarFiltro("semSociais", !filtros.semSociais)} />
      <Toggle tema={tema} label="Mostrar só resultados com sinal de download/link" ativo={filtros.somenteDownload} onClick={() => atualizarFiltro("somenteDownload", !filtros.somenteDownload)} />

      <ChipInput
        tema={tema}
        tipo="positivo"
        titulo="Priorizar domínios"
        descricao="Ex.: steam.com, archive.org, youtube.com. O backend faz busca direta nesses sites e dá prioridade se aparecerem."
        valor={filtros.positivos || []}
        onChange={(lista) => atualizarFiltro("positivos", lista)}
        placeholder="digite um domínio e pressione Enter"
      />

      <ChipInput
        tema={tema}
        tipo="negativo"
        titulo="Bloquear domínios"
        descricao="Ex.: youtube.com. Qualquer resultado desse domínio some da lista."
        valor={filtros.negativos || []}
        onChange={(lista) => atualizarFiltro("negativos", lista)}
        placeholder="digite um domínio e pressione Enter"
      />
    </section>
  )
}

function EmptyState({ tema }) {
  return (
    <div style={{ textAlign: "center", padding: "8px 20px 4px", animation: "fadeUp 0.5s ease both" }}>
      <p style={{ fontSize: 13.5, color: tema.mutedSoft, margin: 0 }}>
        Tente nomes diretos: <strong style={{ color: tema.muted }}>"blender"</strong>,{" "}
        <strong style={{ color: tema.muted }}>"minecraft"</strong> ou algo específico como{" "}
        <strong style={{ color: tema.muted }}>"inazuma eleven victory road steam"</strong>.
      </p>
    </div>
  )
}

export default function App() {
  const [query, setQuery] = useState("")
  const [resultados, setResultados] = useState([])
  const [carregando, setCarregando] = useState(false)
  const [erro, setErro] = useState("")
  const [pagina, setPagina] = useState(1)
  const [config, setConfig] = useState(() => carregarJSON(CONFIG_KEY, DEFAULT_CONFIG))
  const [favoritos, setFavoritos] = useState(() => {
    try { return JSON.parse(localStorage.getItem(FAVORITOS_KEY) || "[]") }
    catch { return [] }
  })
  const [mostrarUsuarioMenu, setMostrarUsuarioMenu] = useState(false)
  const [mostrarAuthModal, setMostrarAuthModal] = useState(false)
  const [authModo, setAuthModo] = useState("login")
  const [usuario, setUsuario] = useState(() => carregarJSON(USER_KEY, null))
  const [mostrarFiltros, setMostrarFiltros] = useState(false)
  const [mostrarFavoritos, setMostrarFavoritos] = useState(false)
  const [focado, setFocado] = useState(false)
  const inputRef = useRef(null)

  const temaBase = TEMAS[config.tema] || TEMAS.claro
  const tema = { ...temaBase, modoEscuro: config.tema === "escuro" }
  const filtros = { ...DEFAULT_CONFIG.filtros, ...(config.filtros || {}) }

  useEffect(() => { localStorage.setItem(CONFIG_KEY, JSON.stringify(config)) }, [config])
  useEffect(() => { localStorage.setItem(FAVORITOS_KEY, JSON.stringify(favoritos)) }, [favoritos])
  useEffect(() => {
    if (usuario) localStorage.setItem(USER_KEY, JSON.stringify(usuario))
    else localStorage.removeItem(USER_KEY)
  }, [usuario])
  useEffect(() => { document.body.style.background = tema.bg }, [tema.bg])

  const favoritosMap = useMemo(() => new Set(favoritos.map(f => f.link)), [favoritos])

  const atualizarConfig = (campo, valor) => setConfig(prev => ({ ...prev, [campo]: valor }))

  const atualizarFiltro = (campo, valor) => {
    setConfig(prev => ({
      ...prev,
      filtros: {
        ...DEFAULT_CONFIG.filtros,
        ...(prev.filtros || {}),
        [campo]: valor
      }
    }))
  }

  const abrirAuth = (modo) => {
    setAuthModo(modo)
    setMostrarAuthModal(true)
    setMostrarUsuarioMenu(false)
  }

  const salvarUsuarioLocal = (dados) => {
    setUsuario(dados)
    setMostrarAuthModal(false)
    setMostrarUsuarioMenu(false)
  }

  const sairUsuarioLocal = () => {
    setUsuario(null)
    setMostrarUsuarioMenu(false)
  }

  const voltarInicio = () => {
    setQuery("")
    setResultados([])
    setErro("")
    setPagina(1)
    setMostrarFavoritos(false)
    setMostrarUsuarioMenu(false)
    setMostrarFiltros(false)
    setCarregando(false)
  }

  const alternarFavorito = (r) => {
    setFavoritos(prev => {
      const existe = prev.some(f => f.link === r.link)
      if (existe) return prev.filter(f => f.link !== r.link)
      return [{
        titulo: r.titulo,
        link: r.link,
        dominio: r.dominio || r.dominio_limpo,
        dominio_limpo: r.dominio_limpo,
        descricao: r.descricao,
        score: r.score,
        tipo: r.tipo,
        loja_jogo: r.loja_jogo,
        oficial: r.oficial,
        download_direto: r.download_direto,
        download_url: r.download_url,
        youtube: r.youtube,
        fonte_confiavel: r.fonte_confiavel,
        tem_download_na_pagina: r.tem_download_na_pagina,
        tem_link_util: r.tem_link_util,
        salvo_em: new Date().toISOString()
      }, ...prev]
    })
  }

  const buscar = async () => {
    if (!query.trim()) return
    setCarregando(true)
    setErro("")
    setResultados([])
    setPagina(1)
    setMostrarFavoritos(false)
    try {
      const res = await axios.get(`${API_URL}/buscar`, {
        params: {
          q: query,
          sem_video: filtros.semVideo,
          sem_jogos: filtros.semJogos,
          sem_software: filtros.semSoftware,
          sem_documentos: filtros.semDocumentos,
          sem_sociais: filtros.semSociais,
          somente_download: filtros.somenteDownload,
          positivos: (filtros.positivos || []).join(","),
          negativos: (filtros.negativos || []).join(","),
        }
      })
      setResultados(res.data.resultados || [])
    } catch {
      setErro("Não foi possível buscar. Verifique se o backend está rodando.")
    } finally {
      setCarregando(false)
    }
  }

  const porPagina = 15
  const totalPaginas = Math.max(1, Math.ceil(resultados.length / porPagina))
  const inicio = (pagina - 1) * porPagina
  const resultadosPagina = resultados.slice(inicio, inicio + porPagina)
  const temResultados = resultados.length > 0
  const buscou = temResultados || carregando || erro

  return (
    <main style={{
      minHeight: "100vh",
      background: tema.bg,
      color: tema.text,
      fontFamily: "'Inter', system-ui, -apple-system, sans-serif",
      transition: "background 0.25s ease, color 0.25s ease",
      padding: "28px 24px 70px",
      position: "relative",
      overflowX: "hidden"
    }}>
      <style>{`
        @import url('https://fonts.googleapis.com/css2?family=Tilt+Neon&family=Inter:wght@400;500;600;700;800&display=swap');
        * { box-sizing: border-box; }
        ::selection { background: ${tema.accentSoft}; color: ${tema.accentText}; }
        input::placeholder { color: ${tema.mutedSoft}; }
        a, button { font-family: inherit; }

        @keyframes cardIn { from { opacity: 0; transform: translateY(10px); } to { opacity: 1; transform: translateY(0); } }
        @keyframes fadeUp { from { opacity: 0; transform: translateY(6px); } to { opacity: 1; transform: translateY(0); } }
        @keyframes logoIn { from { opacity: 0; letter-spacing: 6px; } to { opacity: 1; letter-spacing: 1px; } }
        @keyframes pulseDot { 0%, 100% { opacity: 0.35; transform: scale(0.85); } 50% { opacity: 1; transform: scale(1.15); } }
        .pulse-dot { animation: pulseDot 1.3s ease-in-out infinite; }
        .pulse-dot:nth-child(2) { animation-delay: 0.15s; }
        .pulse-dot:nth-child(3) { animation-delay: 0.3s; }

        .user-panel { position: absolute; right: 0; top: calc(100% + 10px); width: 360px; z-index: 45; }
        @media (max-width: 720px) {
          .atch-header { align-items: flex-start !important; }
          .atch-header-actions { position: relative !important; }
          .user-panel { position: fixed !important; top: 78px !important; left: 16px !important; right: 16px !important; width: auto !important; }
          .search-shell { height: auto !important; padding: 12px 14px !important; flex-wrap: wrap; }
          .search-shell input { min-width: 0; height: 42px !important; }
          .search-shell button.buscar { width: 100%; }
          .filter-panel-mobile { width: auto !important; }
        }
      `}</style>

      <header className="atch-header" style={{
        display: "flex",
        justifyContent: "space-between",
        alignItems: "center",
        maxWidth: 900,
        margin: "0 auto",
        gap: 16
      }}>
        <button
          onClick={voltarInicio}
          title="Voltar para a página inicial"
          style={{
            display: "flex",
            alignItems: "center",
            gap: 10,
            border: "none",
            background: "transparent",
            color: tema.text,
            cursor: "pointer",
            padding: 0
          }}
        >
          <img src="/Atchload.png" alt="Atchload" style={{ width: buscou ? 36 : 54, height: buscou ? 36 : 54, objectFit: "contain" }} />
          {buscou && (
            <span style={{
              fontFamily: "'Tilt Neon', sans-serif",
              fontWeight: 400,
              fontSize: 22,
              color: tema.text,
              letterSpacing: "0.5px"
            }}>
              Atchload
            </span>
          )}
        </button>

        <div className="atch-header-actions" style={{ display: "flex", gap: 8, position: "relative", alignItems: "center" }}>
          <IconButton onClick={() => setMostrarFavoritos(v => !v)} active={mostrarFavoritos} tema={tema} label={favoritos.length > 0 ? `Favoritos · ${favoritos.length}` : "Favoritos"} title="Abrir favoritos">
            <Icon.star size={14} filled={mostrarFavoritos} />
          </IconButton>
          <IconButton onClick={() => atualizarConfig("tema", config.tema === "claro" ? "escuro" : "claro")} tema={tema} label="" title="Alternar tema">
            {config.tema === "claro" ? <Icon.moon /> : <Icon.sun />}
          </IconButton>
          <UserAvatarButton
            usuario={usuario}
            tema={tema}
            active={mostrarUsuarioMenu}
            onClick={() => setMostrarUsuarioMenu(v => !v)}
          />

          {mostrarUsuarioMenu && (
            <UserMenu
              tema={tema}
              usuario={usuario}
              config={config}
              atualizarConfig={atualizarConfig}
              onEntrar={() => abrirAuth("login")}
              onRegistrar={() => abrirAuth("registro")}
              onSair={sairUsuarioLocal}
            />
          )}
        </div>
      </header>

      {mostrarAuthModal && (
        <AuthModal
          tema={tema}
          modoInicial={authModo}
          onClose={() => setMostrarAuthModal(false)}
          onSalvar={salvarUsuarioLocal}
        />
      )}

      <section style={{
        position: "relative",
        maxWidth: buscou ? 780 : 700,
        margin: buscou ? "44px auto 30px" : "min(22vh, 190px) auto 0",
        transition: "margin 0.35s cubic-bezier(.22,1,.36,1), max-width 0.35s cubic-bezier(.22,1,.36,1)"
      }}>
        {!buscou && (
          <div style={{ textAlign: "center", marginBottom: 40, animation: "logoIn 0.6s cubic-bezier(.22,1,.36,1) both" }}>
            <button onClick={voltarInicio} style={{ border: "none", background: "transparent", cursor: "pointer", padding: 0 }}>
              <h1 style={{
                margin: "0 0 10px",
                fontSize: 62,
                lineHeight: 1,
                color: tema.text,
                fontFamily: "'Tilt Neon', sans-serif",
                fontWeight: 400,
                letterSpacing: "1px",
              }}>
                Atchload
              </h1>
            </button>
            <p style={{ margin: 0, fontSize: 14.5, color: tema.muted, fontWeight: 600 }}>
              Encontre fontes de download e visualize o nível de confiança antes de abrir.
            </p>
          </div>
        )}

        <div style={{ position: "relative" }}>
          <div className="search-shell" style={{
          display: "flex",
          alignItems: "center",
          gap: 13,
          background: tema.input,
          border: `1.5px solid ${focado ? tema.accent : tema.inputBorder}`,
          borderRadius: 18,
          padding: "0 18px",
          height: 60,
          boxShadow: focado ? `0 0 0 4px ${tema.accentSoft}, ${tema.shadow}` : tema.shadow,
          transition: "border-color 0.18s, box-shadow 0.18s"
        }}>
          <button
            type="button"
            onClick={() => setMostrarFiltros(v => !v)}
            title="Abrir filtros"
            style={{
              border: "none",
              background: mostrarFiltros ? tema.accentSoft : "transparent",
              color: mostrarFiltros ? tema.accentText : (focado ? tema.accent : tema.mutedSoft),
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              width: 34,
              height: 34,
              borderRadius: 999,
              cursor: "pointer",
              flexShrink: 0
            }}
          >
            <Icon.sliders size={18} bgFill={mostrarFiltros ? "currentColor" : "none"} />
          </button>
          <input
            ref={inputRef}
            type="text"
            value={query}
            onChange={e => setQuery(e.target.value)}
            onKeyDown={e => e.key === "Enter" && buscar()}
            onFocus={() => setFocado(true)}
            onBlur={() => setFocado(false)}
            placeholder="Pesquise um programa, filme, livro, jogo..."
            style={{ flex: 1, height: "100%", border: "none", outline: "none", background: "transparent", color: tema.inputText, fontSize: 16, fontWeight: 600 }}
          />
          {query && (
            <button onClick={() => { setQuery(""); inputRef.current?.focus() }} style={{ border: "none", background: "transparent", cursor: "pointer", color: tema.mutedSoft, fontSize: 17, padding: 4, lineHeight: 1, display: "flex" }} aria-label="Limpar">
              ✕
            </button>
          )}
          <button
            className="buscar"
            onClick={buscar}
            disabled={carregando}
            style={{
              padding: "11px 22px",
              borderRadius: 12,
              background: tema.button,
              color: tema.buttonText,
              border: "none",
              cursor: carregando ? "not-allowed" : "pointer",
              fontWeight: 800,
              fontSize: 14,
              opacity: carregando ? 0.65 : 1,
              transition: "opacity 0.15s, transform 0.1s, background 0.15s",
              flexShrink: 0
            }}
          >
            {carregando ? "Buscando" : "Buscar"}
          </button>
        </div>

          {mostrarFiltros && (
            <FiltrosPanel tema={tema} filtros={filtros} atualizarFiltro={atualizarFiltro} />
          )}
        </div>
      </section>

      {erro && (
        <p style={{ color: tema.danger, textAlign: "center", fontSize: 13.5, fontWeight: 600, maxWidth: 780, margin: "0 auto" }}>
          {erro}
        </p>
      )}

      {mostrarFavoritos && (
        <section style={{ maxWidth: 780, margin: "0 auto 28px", animation: "fadeUp 0.3s ease both" }}>
          <h2 style={{ fontSize: 17, fontWeight: 800, marginBottom: 14, color: tema.text }}>Favoritos</h2>
          {favoritos.length === 0 ? (
            <div style={{ border: `1px dashed ${tema.border}`, borderRadius: 16, padding: "30px 20px", textAlign: "center", background: tema.card }}>
              <p style={{ color: tema.mutedSoft, fontSize: 13.5, margin: 0 }}>
                Nada salvo ainda. Toque na estrela de um resultado para guardá-lo aqui.
              </p>
            </div>
          ) : favoritos.map((f, i) => (
            <Card key={f.link} r={f} tema={tema} config={{ ...config, mostrarTags: false, mostrarMotivos: false }} favorito={true} alternarFavorito={alternarFavorito} index={i} />
          ))}
        </section>
      )}

      {carregando && (
        <div style={{ display: "flex", flexDirection: "column", alignItems: "center", gap: 10, padding: "10px 0 4px" }}>
          <div style={{ display: "flex", gap: 6 }}>
            {[0, 1, 2].map(i => <span key={i} className="pulse-dot" style={{ width: 7, height: 7, borderRadius: "50%", background: tema.accent }} />)}
          </div>
          <p style={{ fontSize: 13, color: tema.mutedSoft, margin: 0, fontWeight: 600 }}>
            Analisando fontes e organizando os resultados...
          </p>
        </div>
      )}

      {temResultados && (
        <section style={{ maxWidth: 780, margin: "0 auto" }}>
          <div style={{ display: "flex", alignItems: "center", gap: 8, color: tema.mutedSoft, fontSize: 12.5, marginBottom: 14, fontWeight: 800, textTransform: "uppercase", letterSpacing: "0.04em" }}>
            <span style={{ width: 6, height: 6, borderRadius: "50%", background: tema.accent }} />
            {resultados.length} resultado{resultados.length !== 1 ? "s" : ""}
          </div>

          {resultadosPagina.map((r, i) => (
            <Card key={`${pagina}-${i}-${r.link}`} r={r} tema={tema} config={config} favorito={favoritosMap.has(r.link)} alternarFavorito={alternarFavorito} index={i} />
          ))}

          {resultados.length > porPagina && (
            <div style={{ display: "flex", justifyContent: "center", alignItems: "center", gap: 6, marginTop: 24 }}>
              <button onClick={() => setPagina(p => Math.max(1, p - 1))} disabled={pagina === 1} style={{ width: 34, height: 34, borderRadius: 10, border: `1px solid ${tema.border}`, background: tema.card, color: tema.text, cursor: pagina === 1 ? "not-allowed" : "pointer", opacity: pagina === 1 ? 0.4 : 1, display: "flex", alignItems: "center", justifyContent: "center", fontSize: 15 }}>‹</button>
              {Array.from({ length: totalPaginas }, (_, i) => i + 1).map(n => (
                <button key={n} onClick={() => setPagina(n)} style={{ minWidth: 34, height: 34, padding: "0 6px", borderRadius: 10, border: `1px solid ${n === pagina ? "transparent" : tema.border}`, background: n === pagina ? tema.button : tema.card, color: n === pagina ? tema.buttonText : tema.text, cursor: "pointer", fontWeight: 800, fontSize: 13, transition: "background 0.15s" }}>
                  {n}
                </button>
              ))}
              <button onClick={() => setPagina(p => Math.min(totalPaginas, p + 1))} disabled={pagina === totalPaginas} style={{ width: 34, height: 34, borderRadius: 10, border: `1px solid ${tema.border}`, background: tema.card, color: tema.text, cursor: pagina === totalPaginas ? "not-allowed" : "pointer", opacity: pagina === totalPaginas ? 0.4 : 1, display: "flex", alignItems: "center", justifyContent: "center", fontSize: 15 }}>›</button>
            </div>
          )}
        </section>
      )}
    </main>
  )
}
