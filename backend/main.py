from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
import requests
import os
import sqlite3
import base64
from datetime import datetime
from urllib.parse import urlparse
from concurrent.futures import ThreadPoolExecutor, as_completed

load_dotenv()

app = FastAPI()
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

SERPAPI_KEY = os.getenv("SERPAPI_KEY")
VIRUSTOTAL_API_KEY = os.getenv("VIRUSTOTAL_API_KEY")

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
# Mudamos para v3 para o SQLite criar as novas colunas de estatísticas sem dar erro
NOME_BANCO = os.path.join(BASE_DIR, "atchload_v3.db")

def inicializar_banco():
    conexao = sqlite3.connect(NOME_BANCO)
    cursor = conexao.cursor()
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS historico_seguranca (
        alvo TEXT PRIMARY KEY,
        tag_atchload TEXT,
        hash_arquivo TEXT,
        malicious INTEGER,
        suspicious INTEGER,
        data_consulta TEXT
    )
    """)
    conexao.commit()
    conexao.close()

inicializar_banco()

def buscar_cache_local(alvo: str):
    try:
        conexao = sqlite3.connect(NOME_BANCO)
        cursor = conexao.cursor()
        cursor.execute("SELECT tag_atchload, hash_arquivo, malicious, suspicious FROM historico_seguranca WHERE alvo = ?", (alvo,))
        res = cursor.fetchone()
        conexao.close()
        if res:
            return {"tag": res[0], "hash": res[1], "m": res[2], "s": res[3]}
        return None
    except:
        return None

def salvar_no_banco(alvo: str, tag: str, hash_arq: str, m: int, s: int):
    conexao = sqlite3.connect(NOME_BANCO)
    cursor = conexao.cursor()
    data_atual = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    cursor.execute("""
        INSERT OR REPLACE INTO historico_seguranca (alvo, tag_atchload, hash_arquivo, malicious, suspicious, data_consulta) 
        VALUES (?, ?, ?, ?, ?, ?)
    """, (alvo, tag, hash_arq, m, s, data_atual))
    conexao.commit()
    conexao.close()

def calcular_tag_atchload(malicious: int, suspicious: int) -> str:
    if malicious >= 3: return "Perigoso"
    elif malicious >= 1 or suspicious > 2: return "Alerta de Cuidado"
    return "Seguro / Confiável"

def analisar_pagina(url):
    try:
        r = requests.get(url, timeout=3, headers={"User-Agent": "Mozilla/5.0"})
        html = r.text.lower()
        return any(p in html for p in ["mega.nz", "mediafire.com", "drive.google.com", "baixar agora", "download file"])
    except: return False

def processar_item(item):
    link = item.get("link", "")
    dominio = urlparse(link).netloc.replace("www.", "")
    download_direto = analisar_pagina(link)
    
    cache = buscar_cache_local(link)
    tag = cache["tag"] if cache else "Aguardando Análise"
    
    score = 40
    if tag == "Perigoso": score = 0
    elif tag == "Alerta de Cuidado": score -= 15
    if dominio in ["archive.org", "mediafire.com", "mega.nz", "drive.google.com"]: score += 20
    if download_direto: score += 20

    return {
        "titulo": item.get("title", ""),
        "link": link,
        "dominio_limpo": dominio,
        "descricao": item.get("snippet", ""),
        "download_direto": download_direto,
        "tag_atchload": tag,
        "hash": cache["hash"] if cache else None,
        "malicious": cache["m"] if cache else 0,
        "suspicious": cache["s"] if cache else 0,
        "score": max(0, min(score, 100))
    }

@app.get("/buscar")
def buscar(q: str):
    query_hacker = f'{q} ("mediafire.com" OR "mega.nz" OR "drive.google.com" OR "index of")'
    try:
        params = {"q": query_hacker, "api_key": SERPAPI_KEY, "hl": "pt-br", "gl": "br"}
        r = requests.get("https://serpapi.com/search", params=params)
        itens = r.json().get("organic_results", [])
    except:
        itens = []
    
    resultados = []
    with ThreadPoolExecutor(max_workers=5) as executor:
        futuros = {executor.submit(processar_item, item): item for item in itens}
        for futuro in as_completed(futuros): resultados.append(futuro.result())
            
    resultados.sort(key=lambda x: x['score'], reverse=True)
    return {"resultados": resultados}

@app.get("/verificar")
def verificar_url(url: str = Query(...)):
    cache = buscar_cache_local(url)
    if cache and cache["tag"] not in ["Aguardando Análise", "Enviado ao VT"]: 
        return {"tag_atchload": cache["tag"], "hash": cache["hash"], "malicious": cache["m"], "suspicious": cache["s"]}
    
    url_id = base64.urlsafe_b64encode(url.encode()).decode().strip("=")
    headers = {"x-apikey": VIRUSTOTAL_API_KEY}
    
    resp = requests.get(f"https://www.virustotal.com/api/v3/urls/{url_id}", headers=headers)
    
    if resp.status_code == 404:
        requests.post("https://www.virustotal.com/api/v3/urls", headers=headers, data={"url": url})
        salvar_no_banco(url, "Enviado ao VT", "", 0, 0)
        return {"tag_atchload": "Enviado ao VT"}
    
    if resp.status_code == 200:
        dados = resp.json()['data']['attributes']
        stats = dados['last_analysis_stats']
        m, s = stats.get('malicious', 0), stats.get('suspicious', 0)
        tag = calcular_tag_atchload(m, s)
        
        hash_arquivo = dados.get('last_http_response_content_sha256', 'Não disponível')
        
        salvar_no_banco(url, tag, hash_arquivo, m, s)
        return {"tag_atchload": tag, "hash": hash_arquivo, "malicious": m, "suspicious": s}
        
    return {"tag_atchload": "Erro na API"}