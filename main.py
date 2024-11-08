from pathlib import Path
import openai
from dotenv import load_dotenv, find_dotenv
import streamlit as st
from moviepy.editor import VideoFileClip
from tempfile import gettempdir
import pdfplumber
from re import sub


#Carregar variáveis de ambiente
_ = load_dotenv(find_dotenv())

#Cria pastas temporarias
PASTA_TEMP = Path(gettempdir())
PASTA_TEMP.mkdir(exist_ok=True)
ARQUIVO_AUDIO_TEMP = PASTA_TEMP / 'audio_temp.mp3'
ARQUIVO_VIDEO_TEMP = PASTA_TEMP / 'video_temp.mp4'

#Carregar API
client = openai.OpenAI()

#Funções de transcricao - INÍCIO
def transcricao(file):
    prompt = 'Você é um assistente útil para transcrever áudios. Sua tarefa é corrigir quaisquer discrepâncias ortográficas no texto transcrito.'
    transcricao = client.audio.transcriptions.create(
            model='whisper-1',
            language='pt',
            response_format='text',
            file=file,
            prompt=prompt
        )
    return transcricao

def transcrever_tab_aud():
    arquivo_audio = st.file_uploader('Faça o upload de um arquivo de áudio em formato MP3 para transcrição', type=['mp3'])

    if arquivo_audio is not None:
        transcricao_text = transcricao(arquivo_audio)
        resumo_text = gerar_resumo(transcricao_text, 'transcricao')
        st.write('**Transcrição:**', transcricao_text)
        st.write(resumo_text)

def transcrever_tab_vid():
    arquivo_video = st.file_uploader('Faça o upload de um arquivo de vídeo em formato MP4 para transcrição', type=['mp4'])

    if arquivo_video is not None:
        with open(ARQUIVO_VIDEO_TEMP, 'wb') as video_f:
            video_f.write(arquivo_video.read())

        clip = VideoFileClip(str(ARQUIVO_VIDEO_TEMP))
        clip.audio.write_audiofile(str(ARQUIVO_AUDIO_TEMP))

        with open(ARQUIVO_AUDIO_TEMP, 'rb') as audio_f:
            transcricao_text = transcricao(audio_f)
            resumo_text = gerar_resumo(transcricao_text, 'transcricao')
            st.write('**Transcrição:**', transcricao_text)
            st.write(resumo_text)

#Funções de transcricao - FIM

#Funções para extrair informações limpas do PDF - INÍCIO

def info_tab_peticao_inicial():
    arquivo_pdf = st.file_uploader('Faça o upload de uma Petição Inicial em formato PDF para extração de dados', type=['pdf'])

    if arquivo_pdf is not None:
        info_pdf = extrair_info_pdf(arquivo_pdf)
        info_pdf = limpar_texto(info_pdf)
        resumo_text = gerar_resumo(info_pdf, 'pdf')
        resumo_text = escapar_caracteres_markdown(resumo_text)
        st.markdown(resumo_text)

def extrair_info_pdf(arquivo_pdf):
    texto = ''
    with pdfplumber.open(arquivo_pdf) as pdf:
        for pagina in pdf.pages:
            texto_pagina = pagina.extract_text()
            if texto_pagina:
                # Adiciona uma quebra de linha após o texto de cada página
                texto += texto_pagina + '\n'
    return texto

def limpar_texto(texto):
    texto_limpo = ' '.join(texto.split())
    return texto_limpo

def escapar_caracteres_markdown(texto):
    caracteres_especiais = r'([$@])'
    return sub(caracteres_especiais, r'\\\1', texto)

#Funções para extrair informações limpas do PDF - FIM

#Funções para geração dos resumos - INÍCIO
PROMPT_TRANSCRICAO = '''
Analise o conteúdo do texto delimitado por "####" seguindo as diretrizes abaixo:

1. **Resumo completo**: Elabore um resumo detalhado, destacando os principais temas, tópicos e informações relevantes presentes no texto.
2. **Acordos e decisões**: Identifique e liste em forma de bullet points todas as conclusões, decisões e acordos mencionados.

Utilize o seguinte formato para a resposta:

- **Resumo do texto**: [Inserir o resumo aqui]
- **Acordos e decisões**:
  - [Inserir acordo ou decisão 1]
  - [Inserir acordo ou decisão 2]
  - [Inserir acordo ou decisão n]

Texto para análise: ####{}####
'''

PROMPT_PDF = '''
 Analise o conteúdo da petição inicial delimitada por "####" seguindo as diretrizes abaixo:

 1. **Resumo completo**: Elabore um resumo detalhado, destacando os principais temas, tópicos e informações relevantes presentes na petição inicial.
 2. **Extração de informações**: Realize a extração das seguintes informações dessa petição inicial: Peticionanete, comarca, valor da ação.

 - **Resumo da Petição Inicial**: [Inserir o resumo aqui]
 - **Auxílio para Preenchimento**:
  - [Inserir Peticionanete]
  - [Inserir Comarca]
  - [Inserir Valor da Ação]

Texto para análise: ####{}####
'''

def gerar_resumo(texto, tipo):
    if tipo == 'transcricao':
        PROMPT = PROMPT_TRANSCRICAO
    elif tipo == 'pdf':
        PROMPT = PROMPT_PDF

    resposta = client.chat.completions.create(
        model='gpt-4o',
        messages=[{'role': 'user', 'content': PROMPT.format(texto)}]
    )
    return resposta.choices[0].message.content

#Funções para geração dos resumos - FIM


def main():
    st.header(body='Projeto Integrador :red[IV] - URI Erechim ⚖️', anchor=False, divider='orange')
    st.markdown(body='💻 **Integrantes:** Ademir, Ana M., Denis, Evandro, João, Kauan, Lucas e Lucimar')
    tab_aud, tab_vid, tab_peticao_inicial = st.tabs(['Áudio', 'Vídeo', 'Petição Inicial'])
    with tab_aud:
        transcrever_tab_aud()
    with tab_vid:
        transcrever_tab_vid()
    with tab_peticao_inicial:
        info_tab_peticao_inicial()


if __name__ == '__main__':
    main()
