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

def transcrever_tab_vid():
    arquivo_video = st.file_uploader('Faça o upload de um arquivo de vídeo em formato MP4 para transcrição', type=['mp4'])

    if not arquivo_video is None:
        with open(ARQUIVO_VIDEO_TEMP, 'wb') as video_f:
            video_f.write(arquivo_video.read())

        clip = VideoFileClip(str(ARQUIVO_VIDEO_TEMP))
        clip.audio.write_audiofile(str(ARQUIVO_AUDIO_TEMP))

        with open(ARQUIVO_AUDIO_TEMP, 'rb') as audio_f:
            transcricao_text = transcricao(audio_f)
            st.write(transcricao_text)

def transcrever_tab_aud():
    arquivo_audio = st.file_uploader('Faça o upload de um arquivo de áudio em formato MP3 para transcrição', type=['mp3'])

    if arquivo_audio is not None:
        transcricao_text = transcricao(arquivo_audio)
        resumo_text = gerar_resumo(transcricao_text)
        st.write(resumo_text)

#Funções de transcricao - FIM

#Funções para geração dos resumos - INÍCIO
PROMPT = '''
Identifique o conteúdo do texto delimitado por "####" com base nas seguintes diretrizes:

1. **Resumo detalhado**: Forneça um resumo completo, destacando os principais tópicos discutidos.
2. **Acordos e decisões**: Liste todas as conclusões e acordos mencionados no texto, utilizando bullet points.

Formato esperado:

- **Resumo do texto**: [Inserir resumo]
- **Acordos e decisões**:
  - [Acordo 1]
  - [Acordo 2]
  - [Acordo 3]

Texto: ####{}####
'''

def gerar_resumo(texto):
    prompt = PROMPT.format(texto)
    resposta = client.completions.create(
        model='gpt-4',
        prompt=prompt,
        n=1
    )
    return resposta.choices[0].text.strip()

#Funções para geração dos resumos - FIM

def main():
    st.header(body='Projeto Integrador :red[IV] - URI Erechim ⚖️', anchor=False, divider='orange')
    st.markdown(body='💻 **Integrantes:** Ademir, Ana M., Basi, Denis, Evandro, :rainbow[***João***], Kauan, Lucas')
    tab_mic, tab_vid, tab_aud = st.tabs(['Microfone', 'Vídeo', 'Áudio'])
    with tab_mic:
        transcrever_tab_mic()
    with tab_vid:
        transcrever_tab_vid()
    with tab_aud:
        transcrever_tab_aud()


if __name__ == '__main__':
    main()