from pathlib import Path
from datetime import datetime
import time
import queue

import streamlit as st
from streamlit_webrtc import WebRtcMode, webrtc_streamer

import pydub
import openai
from dotenv import load_dotenv, find_dotenv

PASTA_ARQUIVOS = Path(__file__).parent / 'arquivos'
PASTA_ARQUIVOS.mkdir(exist_ok=True)

PROMPT = '''
Faça o seguinte com a transcrição da reunião delimitada por ####:

1. **Resumo da Reunião**: Forneça um resumo detalhado abordando todos os principais assuntos discutidos.
2. **Acordos da Reunião**: Liste todos os acordos e decisões tomadas em formato de bullet points.

Formato desejado:

- Resumo da reunião: [Inserir resumo]
- Acordos da reunião:
  - [Acordo 1]
  - [Acordo 2]
  - [Acordo 3]
  - [Acordo n]

Texto: ####{}####
'''


_ = load_dotenv(find_dotenv())


def salvar_arquivo(caminho_arquivo, conteudo):
    if caminho_arquivo is None or conteudo is None:
        raise ValueError("caminho_arquivo e conteudo não podem ser None")
    
    try:
        with open(caminho_arquivo, 'w') as f:
            f.write(conteudo)
    except Exception as e:
        raise RuntimeError(f"Falha ao salvar {caminho_arquivo}: {e}")
def ler_arquivo(caminho_arquivo):
    if caminho_arquivo is None:
        raise ValueError("caminho_arquivo não pode ser None")

    try:
        with open(caminho_arquivo) as f:
            return f.read()
    except FileNotFoundError:
        return ''

def listar_reunioes():
    lista_reunioes = PASTA_ARQUIVOS.glob('*')
    lista_reunioes = list(lista_reunioes)
    lista_reunioes.sort(reverse=True)
    reunioes_dict = {}
    for pasta_reuniao in lista_reunioes:
        if not pasta_reuniao.is_dir():
            continue
        data_reuniao = pasta_reuniao.stem
        ano, mes, dia, hora, min, seg = data_reuniao.split('_')
        reunioes_dict[data_reuniao] = f'{ano}/{mes}/{dia} {hora}:{min}:{seg}'
        titulo_arquivo = pasta_reuniao / 'titulo.txt'
        if titulo_arquivo.exists():
            titulo = ler_arquivo(titulo_arquivo)
            if titulo:
                reunioes_dict[data_reuniao] += f' - {titulo}'
    return reunioes_dict


# OPENAI UTILS =====================
client = openai.OpenAI()

def transcrever_audio(caminho_audio, language='pt', response_format='text'):
    if not caminho_audio:
        raise ValueError("caminho_audio não pode ser None")

    with open(caminho_audio, 'rb') as arquivo_audio:
        try:
            transcricao = client.audio.transcriptions.create(
                model='whisper-1',
                language=language,
                response_format=response_format,
                file=arquivo_audio,
            )
        except Exception as e:
            raise RuntimeError(f"Falha ao transcrever {caminho_audio}: {e}")

    return transcricao

def chat_openai(
        mensagem,
        modelo='gpt-4o',
    ):
    if not mensagem:
        raise ValueError("mensagem não pode ser None ou vazia")

    messages = [{'role': 'user', 'content': mensagem}]
    try:
        resposta = client.chat.completions.create(
            model=modelo,
            messages=messages,
        )
        choices = resposta.choices
        if choices:
            choice = choices[0]
            if choice.message:
                return choice.message.content
    except Exception as e:
        raise RuntimeError(f"Falha ao obter resposta da OpenAI: {e}")
    return ""

# TAB GRAVAR REUNIÃO =====================

def adicionar_chunck_audio(frames_de_audio, audio_chunck):
    if frames_de_audio is None:
        raise ValueError("frames_de_audio não pode ser None")
    if audio_chunck is None:
        raise ValueError("audio_chunck não pode ser None")

    for frame in frames_de_audio:
        if frame is None:
            raise ValueError("frame não pode ser None")
        sound = pydub.AudioSegment(
            data=frame.to_ndarray().tobytes(),
            sample_width=frame.format.bytes,
            frame_rate=frame.sample_rate,
            channels=len(frame.layout.channels),
        )
        audio_chunck += sound
    return audio_chunck

def tab_gravar_reuniao():
    webrtx_ctx = webrtc_streamer(
        key='recebe_audio',
        mode=WebRtcMode.SENDONLY,
        audio_receiver_size=1024,
        media_stream_constraints={'video': False, 'audio': True},
    )

    if webrtx_ctx is None or not webrtx_ctx.state.playing:
        return

    container = st.empty()
    container.markdown('Comece a falar')
    pasta_reuniao = PASTA_ARQUIVOS / datetime.now().strftime('%Y_%m_%d_%H_%M_%S')
    pasta_reuniao.mkdir(exist_ok=True)

    ultima_trancricao = time.time()
    audio_completo = pydub.AudioSegment.empty()
    audio_chunck = pydub.AudioSegment.empty()
    transcricao = ''

    while True:
        if webrtx_ctx.audio_receiver is None:
            break
        try:
            frames_de_audio = webrtx_ctx.audio_receiver.get_frames(timeout=1)
        except queue.Empty:
            time.sleep(0.1)
            continue
        audio_completo = adicionar_chunck_audio(frames_de_audio, audio_completo)
        audio_chunck = adicionar_chunck_audio(frames_de_audio, audio_chunck)
        if len(audio_chunck) > 0:
            audio_completo.export(pasta_reuniao / 'audio.mp3')
            agora = time.time()
            if agora - ultima_trancricao > 5:
                ultima_trancricao = agora
                audio_chunck.export(pasta_reuniao / 'audio_temp.mp3')
                transcricao_chunck = transcrever_audio(pasta_reuniao / 'audio_temp.mp3')
                transcricao += transcricao_chunck
                salvar_arquivo(pasta_reuniao / 'transcricao.txt', transcricao)
                container.markdown(transcricao)
                audio_chunck = pydub.AudioSegment.empty()


# TAB SELEÇÃO REUNIÃO =====================
def tab_selecao_reuniao():
    reunioes_dict = listar_reunioes()
    if not reunioes_dict:
        st.warning('Nenhuma reunião encontrada')
        return
    reuniao_selecionada = st.selectbox('Selecione uma reunião',
                                      list(reunioes_dict.values()))
    st.divider()
    reuniao_data = next((k for k, v in reunioes_dict.items() if v == reuniao_selecionada), None)
    if not reuniao_data:
        st.warning('Reunião selecionada não encontrada')
        return
    pasta_reuniao = PASTA_ARQUIVOS / reuniao_data
    if not (pasta_reuniao / 'titulo.txt').exists():
        st.warning('Adicione um titulo')
        titulo_reuniao = st.text_input('Título da reunião')
        if titulo_reuniao:
            st.button('Salvar',
                      on_click=salvar_titulo,
                      args=(pasta_reuniao, titulo_reuniao))
    else:
        titulo = ler_arquivo(pasta_reuniao / 'titulo.txt')
        transcricao = ler_arquivo(pasta_reuniao / 'transcricao.txt')
        resumo = ler_arquivo(pasta_reuniao / 'resumo.txt')
        if not resumo:
            gerar_resumo(pasta_reuniao)
            resumo = ler_arquivo(pasta_reuniao / 'resumo.txt')
        st.markdown(f'## {titulo}')
        st.markdown(f'{resumo}')
        st.markdown(f'Transcricao: {transcricao}')
        
def salvar_titulo(pasta_reuniao, titulo):
    if pasta_reuniao is None:
        raise ValueError("pasta_reuniao não pode ser None")
    if titulo is None:
        raise ValueError("titulo não pode ser None")
    salvar_arquivo(pasta_reuniao / 'titulo.txt', titulo)

def gerar_resumo(pasta_reuniao):
    transcricao = ler_arquivo(pasta_reuniao / 'transcricao.txt')
    if transcricao is None:
        raise ValueError("Transcricao not found")
    resumo = chat_openai(mensagem=PROMPT.format(transcricao))
    if resumo is None:
        raise RuntimeError("Falha ao gerar resumo")
    salvar_arquivo(pasta_reuniao / 'resumo.txt', resumo)


# MAIN =====================
def main():
    st.header('🎙️ Transcrição de Reuniões - Projeto Integrador IV', divider=True)
    try:
        tab_gravar, tab_selecao = st.tabs(['Gravar Reunião', 'Ver transcrições salvas'])
        with tab_gravar:
            tab_gravar_reuniao()
        with tab_selecao:
            tab_selecao_reuniao()
    except Exception as e:
        st.error(f'Ocorreu um erro: {e}')


if __name__ == '__main__':
    main()
