from fastapi import FastAPI, Query
import sqlite3
import requests
import base64
from datetime import datetime

app = FastAPI(
    title="Atchload API",
    description="Backend definitivo para o buscador inteligente de downloads seguros",
    version="1.0.0"
)

NOME_BANCO = "atchload.db"

# SUBSTITUA PELA SUA CHAVE REAL DO VIRUSTOTAL
VIRUSTOTAL_API_KEY = "c645ede999514ae13cd0c2950a19d57866e3932a2fcbd107928e5f43c3cdce32"

# ---- FUNÇÕES AUXILIARES DE SEGURANÇA E BANCO DE DADOS ----

def inicializar_banco():
    """Garante que a tabela existe sempre que o servidor inicia"""
    conexao = sqlite3.connect(NOME_BANCO)
    cursor = conexao.cursor()
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS historico_seguranca (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        alvo TEXT UNIQUE,
        tipo TEXT,
        harmless INTEGER,
        suspicious INTEGER,
        malicious INTEGER,
        tag_atchload TEXT,
        data_consulta TEXT
    )
    """)
    conexao.commit()
    conexao.close()

def buscar_cache_local(url: str):
    """Procura se a URL já foi analisada antes para poupar a API"""
    conexao = sqlite3.connect(NOME_BANCO)
    cursor = conexao.cursor()
    cursor.execute(
        "SELECT tag_atchload, harmless, suspicious, malicious, data_consulta FROM historico_seguranca WHERE alvo = ?", 
        (url,)
    )
    resultado = cursor.fetchone()
    conexao.close()
    return resultado

def salvar_no_banco(url: str, harmless: int, suspicious: int, malicious: int, tag: str):
    """Guarda o resultado real da API para consultas futuras"""
    conexao = sqlite3.connect(NOME_BANCO)
    cursor = conexao.cursor()
    data_atual = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    cursor.execute("""
    INSERT OR REPLACE INTO historico_seguranca 
    (alvo, tipo, harmless, suspicious, malicious, tag_atchload, data_consulta)
    VALUES (?, 'url', ?, ?, ?, ?, ?)
    """, (url, harmless, suspicious, malicious, tag, data_atual))
    conexao.commit()
    conexao.close()

def gerar_id_url_virustotal(url: str) -> str:
    """Codifica a URL em Base64 sem preenchimento (=), padrão exigido pelo VirusTotal"""
    url_bytes = url.encode("utf-8")
    base64_bytes = base64.b64encode(url_bytes)
    base64_string = base64_bytes.decode("utf-8")
    return base64_string.rstrip("=")

def calcular_tag_atchload(malicious: int, suspicious: int) -> str:
    """O motor de Scoring do Atchload que define o nível de risco"""
    if malicious > 2:
        return "Perigoso"
    elif malicious > 0 or suspicious > 0:
        return "Inseguro"
    else:
        return "Seguro / Confiável"


inicializar_banco()


# ---- ENDPOINT PRINCIPAL  ----

@app.get("/verificar")
def verificar_url(url: str = Query(..., description="A URL do site ou do download a ser analisada")):
    print(f"🔍 Processando requisição para: {url}")
    
  
    cache = buscar_cache_local(url)
    if cache:
        print("⚡ Item encontrado na Cache Local! Retornando imediatamente.")
        return {
            "alvo": url,
            "status": "sucesso",
            "origem": "Base de Dados Local (Cache)",
            "tag_atchload": cache[0],
            "detalhes_motores": {
                "harmless": cache[1],
                "suspicious": cache[2],
                "malicious": cache[3]
            },
            "analisado_em": cache[4]
        }
    
   
    print("🌐 Link inédito. Consultando a API do VirusTotal em tempo real...")
    url_id = gerar_id_url_virustotal(url)
    endpoint_vt = f"https://www.virustotal.com/api/v3/urls/{url_id}"
    
    headers = {
        "accept": "application/json",
        "x-apikey": VIRUSTOTAL_API_KEY
    }
    
    resposta = requests.get(endpoint_vt, headers=headers)
    
   
    if resposta.status_code == 404:
        print("⚠️ URL nunca vista pelo VirusTotal. Solicitando uma nova análise...")
        scan_endpoint = "https://www.virustotal.com/api/v3/urls"
        requests.post(scan_endpoint, headers=headers, data={"url": url})
        
       
        return {
            "alvo": url,
            "status": "processando",
            "origem": "API (Nova Análise Solicitada)",
            "tag_atchload": "Análise em Processo",
            "mensagem": "Este link é totalmente novo na internet. Solicitamos uma varredura. Tente novamente em instantes."
        }
        
    elif resposta.status_code == 200:
        dados = resposta.json()
        stats = dados['data']['attributes']['last_analysis_stats']
        
        harmless = stats.get('harmless', 0)
        suspicious = stats.get('suspicious', 0)
        malicious = stats.get('malicious', 0)
        
        
        tag_final = calcular_tag_atchload(malicious, suspicious)
        
        # PASSO 4: Salvar o resultado na base de dados SQLite
        salvar_no_banco(url, harmless, suspicious, malicious, tag_final)
        
        return {
            "alvo": url,
            "status": "sucesso",
            "origem": "Análise em Tempo Real (API)",
            "tag_atchload": tag_final,
            "detalhes_motores": {
                "harmless": harmless,
                "suspicious": suspicious,
                "malicious": malicious
            },
            "analisado_em": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
    
    else:
        return {
            "alvo": url,
            "status": "erro",
            "codigo_erro": resposta.status_code,
            "mensagem": "Não foi possível obter o relatório de segurança do link externo."
        }