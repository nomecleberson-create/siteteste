# Playlist MP3 Downloader

Aplicação estática para converter arquivos de áudio selecionados pelo usuário em MP3 e baixar todos em um ZIP.

## Importante
- Não extrai nem baixa áudio diretamente do YouTube.
- Use somente arquivos próprios ou cujo download/conversão você esteja autorizado a fazer.
- A conversão ocorre no navegador; os arquivos não são enviados ao servidor.
- Arquivos muito longos ou grandes podem consumir bastante memória do computador.
- O suporte depende dos codecs disponíveis no navegador.

## Publicar na Vercel
1. Extraia este ZIP.
2. Crie um repositório público no GitHub e envie `index.html` e `vercel.json`.
3. Na Vercel, escolha **Add New > Project** e importe o repositório.
4. Framework Preset: **Other**.
5. Build Command: deixe vazio; Output Directory: `.` (ou deixe o padrão para site estático).
6. Clique em **Deploy**.

Também é possível importar diretamente o projeto pela Vercel usando o repositório GitHub.

## Uso
Abra o site, selecione vários arquivos de áudio ou arraste-os para a área indicada e clique em “Converter e baixar tudo (.ZIP)”. Depois extraia o ZIP e copie os MP3 para o pendrive.
