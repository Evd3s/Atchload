# Atchload 
**Buscador inteligente de downloads seguros**

O Atchload é um buscador focado exclusivamente em encontrar arquivos para download na internet — programas, filmes, músicas, jogos, livros e qualquer outra mídia. Cada resultado é analisado e classificado por segurança, nível de anúncios e disponibilidade de download direto.

---

## Tecnologias utilizadas

| Camada | Tecnologia |
|---|---|
| Frontend | React + Vite |
| Backend | Python + FastAPI |
| Banco de dados | SQLite |
| Busca | SerpApi |
| Segurança | VirusTotal |

---

## Pré-requisitos

Antes de rodar o projeto, instale:

- [Node.js 22+]
- [Python 3.12+]
- [VS Code]

---

## Configuração das APIs

O projeto usa duas chaves de API externas. Você precisa criá-las antes de rodar.

### SerpApi (busca)
1. Acesse [serpapi.com](https://serpapi.com) e crie uma conta gratuita
2. Sua chave aparece no dashboard após o login

### VirusTotal (segurança — futuro)
1. Acesse [virustotal.com](https://www.virustotal.com) e crie uma conta gratuita
2. Acesse [virustotal.com/gui/my-apikey](https://www.virustotal.com/gui/my-apikey) para ver sua chave

---

## Instalação e execução

### 1. Clone o repositório

```bash
git clone https://github.com/Evd3s/atchload.git
cd atchload
```

### 2. Configure o backend

Entre na pasta do backend:

```bash
cd backend
```

Crie o arquivo de variáveis de ambiente:

```bash
# Windows
copy .env.example .env

# Mac / Linux
cp .env.example .env
```

Abra o arquivo `.env` e preencha com suas chaves:

```
SERPAPI_KEY=sua_chave_serpapi_aqui
```

Instale as dependências Python:

```bash
pip install -r requirements.txt
```

Inicie o servidor backend:

```bash
uvicorn main:app --reload
```

O backend estará rodando em: `http://127.0.0.1:8000` ou algo similar.

---

### 3. Configure o frontend

Abra um **novo terminal** e entre na pasta do frontend:

```bash
cd frontend
```

Instale as dependências:

```bash
npm install
```

Inicie o servidor frontend:

```bash
npm run dev
```

O frontend estará rodando em: `http://localhost:5173`

---

## Como rodar no dia a dia

Sempre que for trabalhar no projeto, você precisa de **dois terminais abertos ao mesmo tempo**:

**Terminal 1 — Backend:**
```bash
cd backend
uvicorn main:app --reload
```

**Terminal 2 — Frontend:**
```bash
cd frontend
npm run dev
```

Depois acesse `http://localhost:5173` no navegador.

---

## Autores

- Eudes Pontes
- Lucas Luiz

*Projeto desenvolvido para a disciplina de Projeto — Tecnologia e Sistemas para Internet*
