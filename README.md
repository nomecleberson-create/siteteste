# Playlist Downloader Gospel PRO

Interface pública (Vercel) + API de processamento (Render) para playlists do YouTube cujo download e conversão o usuário tem autorização para realizar.

## Arquitetura
- `frontend/index.html`: interface, seleção das faixas, qualidade 128/192/320 kbps e progresso.
- `backend/main.py`: API FastAPI, yt-dlp, FFmpeg e ZIP.
- O backend precisa de FFmpeg instalado no host.

## 1) Publicar backend no Render
1. Suba esta pasta para um repositório GitHub.
2. No Render, crie um **Web Service** e selecione o repositório.
3. Root Directory: `backend`
4. Build Command: `pip install -r requirements.txt`
5. Start Command: `uvicorn main:app --host 0.0.0.0 --port $PORT`
6. Em Environment, configure `FRONTEND_ORIGINS` com o domínio Vercel depois de publicá-lo.
7. Garanta que FFmpeg esteja instalado no ambiente. Em Render, use um Dockerfile se a imagem padrão não tiver FFmpeg.

## 2) Publicar frontend na Vercel
1. Importe o mesmo repositório na Vercel.
2. Root Directory: `frontend`
3. Framework Preset: Other; Build Command vazio; Output Directory `.`.
4. Depois de publicar, abra `frontend/index.html` e troque `https://SEU-BACKEND.onrender.com` pelo endereço real do Render na constante `API`.

## 3) FFmpeg no Render (recomendado: Docker)
Use este Dockerfile no diretório `backend`:
```
FROM python:3.11-slim
RUN apt-get update && apt-get install -y --no-install-recommends ffmpeg && rm -rf /var/lib/apt/lists/*
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY main.py .
CMD ["sh","-c","uvicorn main:app --host 0.0.0.0 --port ${PORT:-10000}"]
```
No Render selecione Docker e Root Directory `backend`.

## Limites e segurança
- Limite configurável de 100 faixas por tarefa; máximo de 2 tarefas simultâneas nesta implementação.
- O armazenamento é temporário e em memória para o estado dos jobs; reinícios do serviço interrompem tarefas.
- Para produção pública, acrescente autenticação, rate limiting persistente, fila de jobs, limites de duração/tamanho e política de retenção.
- Não usar para conteúdo protegido sem autorização. Respeite direitos autorais e os termos da plataforma.
- O YouTube pode alterar mecanismos de acesso; atualize yt-dlp e siga suas regras.
