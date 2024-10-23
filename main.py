from pathlib import Path
import queue
from time import sleep, time
import openai
from dotenv import load_dotenv, find_dotenv
import streamlit as st
from streamlit_webrtc import WebRtcMode, webrtc_streamer
from moviepy.editor import VideoFileClip
import pydub
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
ARQUIVO_MICROFONE_TEMP = PASTA_TEMP / 'microfone_temp.mp3'

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

@st.cache_data
def get_ice_servers():
    return [{'urls': ['stun:stun.l.google.com:19302']}]

def transcrever_tab_mic():
    st.markdown('Transcrição do áudio do microfone em tempo real')
    webrtc = webrtc_streamer(
        key='recebe_audio',
        mode=WebRtcMode.SENDONLY,
        audio_receiver_size=1024,
        rtc_configuration={'iceServers': get_ice_servers()},
        media_stream_constraints={'video': False, 'audio': True},
        translations={'start': 'Iniciar', 'stop': 'Parar'}
    )

    if not webrtc.state.playing:
        return
    
    container = st.empty()
    container.markdown('**Transcrição iniciada**')
    chunck_audio = pydub.AudioSegment.empty()
    tempo_ultima_transcricao = time()
    while True:
        if webrtc.audio_receiver:
            try:
                audio_frames = webrtc.audio_receiver.get_frames(timeout=1)
            except queue.Empty:
                sleep(0.1)
                continue

            for audio_frame in audio_frames:
                sound = pydub.AudioSegment(
                    data=audio_frame.to_ndarray().tobytes(),
                    sample_width=audio_frame.format.bytes,
                    frame_rate=audio_frame.rate,
                    channels=len(audio_frame.layout.channels)
                )
                chunck_audio += sound
            
            agora = time()
            
            if len(chunck_audio) > 0 and agora - tempo_ultima_transcricao > 5:
                tempo_ultima_transcricao = agora
                chunck_audio.export(ARQUIVO_MICROFONE_TEMP, format='mp3')
                chunck_audio = pydub.AudioSegment.empty() #Reinicia para nova gravação

                with open(ARQUIVO_MICROFONE_TEMP, 'rb') as audio_f:
                    transcricao_text = transcricao(audio_f)
                    container.write(transcricao_text)
        else:
            break

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
    st.markdown(body='💻 **Integrantes:** Ademir, Ana M., Denis, Evandro, :rainbow[***João***], Kauan, Lucas e Lucimar')
    tab_mic, tab_aud, tab_vid, tab_peticao_inicial = st.tabs(['Microfone', 'Áudio', 'Vídeo', 'Petição Inicial'])
    with tab_mic:
        transcrever_tab_mic()
    with tab_aud:
        transcrever_tab_aud()
    with tab_vid:
        transcrever_tab_vid()
    with tab_peticao_inicial:
        info_tab_peticao_inicial()


if __name__ == '__main__':
    main()