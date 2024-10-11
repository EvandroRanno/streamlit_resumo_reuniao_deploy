# Projeto Integrador IV - URI Erechim ⚖️


## Descrição

Este projeto foi desenvolvido para o **Projeto Integrador IV** do curso de Direito da URI Erechim. O objetivo principal é demonstrar como a tecnologia pode ser usada no contexto jurídico para facilitar tarefas do dia a dia, como a transcrição de áudios e vídeos e a extração de informações de petições. A aplicação faz uso da API do OpenAI para transcrição de áudio, resumos automáticos e extração de dados de PDFs, além de permitir a interação com a entrada de áudio em tempo real via microfone.


## Funcionalidades

### 1. **Transcrição de Áudio e Vídeo**
   - Transcrição de arquivos de áudio em formato **MP3** e vídeos em formato **MP4**.
   - Resumo automático dos áudios e vídeos transcritos, destacando pontos importantes e decisões.

### 2. **Transcrição de Áudio em Tempo Real**
   - Realiza a transcrição em tempo real do áudio capturado pelo microfone.
   - O áudio transcrito é exibido imediatamente na interface do Streamlit.

### 3. **Extração de Informações de Petições em PDF**
   - Upload de arquivos **PDF** contendo petições iniciais.
   - O texto da petição é processado e extraído automaticamente.
   - O sistema fornece um resumo da petição, além de identificar algumas informações para auxiliar no preenchimento pelo advogado.


## Requisitos

Para executar este projeto, os seguintes pacotes e bibliotecas são necessários:

- Python 3.10 ou superior
- Bibliotecas Python:
  - `streamlit`
  - `streamlit-webrtc`
  - `moviepy`
  - `pydub`
  - `openai`
  - `PyPDF2`
  - `dotenv`
  - `pathlib`
  - `re`

## Instalação

1. Clone o repositório para sua máquina local:
   ```bash
   git clone https://github.com/EvandroRanno/streamlit_resumo_reuniao_deploy.git

2. Instale as dependências:
   ```bash
   pip install -r requirements.txt

3. Crie um arquivo .env na raiz do projeto e configure sua chave de API do OpenAI:
   ```bash
   OPENAI_API_KEY=digite_sua_API_aqui

4. Execute a aplicação:
   ```bash
   streamlit run main.py

## Integrantes
Ademir, Ana M., Denis, Evandro, João Eduardo, Lucas e Lucimar