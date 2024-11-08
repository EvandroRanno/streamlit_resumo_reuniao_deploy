from pathlib import Path
import openai
from dotenv import load_dotenv, find_dotenv
import streamlit as st
from moviepy.editor import VideoFileClip
from tempfile import gettempdir
import pdfplumber
from re import sub
import os
import tempfile
import subprocess


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

def converter_m4a_para_mp3(caminho_arquivo_m4a):
    try:
        # Clonando o FFmpeg (somente uma vez, se necessário)
        if not os.path.exists('ffmpeg'):
            subprocess.run(['git', 'clone', 'https://git.ffmpeg.org/ffmpeg.git', 'ffmpeg'])

        # Compilando FFmpeg (caso ainda não tenha sido feito)
        if not os.path.exists('./ffmpeg/fftools/ffmpeg'):
            subprocess.run(['make'], cwd='./ffmpeg', check=True)

        # Definindo caminho do FFmpeg compilado
        ffmpeg_bin = './ffmpeg/fftools/ffmpeg'

        # Definindo o caminho de saída do arquivo MP3
        caminho_mp3 = caminho_arquivo_m4a.replace('.m4a', '.mp3')

        # Executando a conversão
        subprocess.run([ffmpeg_bin, '-i', caminho_arquivo_m4a, caminho_mp3], check=True)
        return caminho_mp3
    except Exception as e:
        st.error(f"Erro na conversão: {e}")
        return None

def transcrever_tab_aud():
    arquivo_audio = st.file_uploader('Faça o upload de um arquivo de áudio em formato MP3 ou M4A para transcrição', type=['mp3', 'm4a'])

    if arquivo_audio is not None:
        # Salvar o arquivo temporariamente
        with tempfile.NamedTemporaryFile(delete=False, suffix=f".{arquivo_audio.type.split('/')[-1]}") as temp_audio_file:
            temp_audio_file.write(arquivo_audio.read())
            temp_audio_path = temp_audio_file.name

        # Verificar se o arquivo é .m4a e realizar a conversão
        if temp_audio_path.endswith('.m4a'):
            st.write("Convertendo arquivo de M4A para MP3...")
            temp_mp3_path = converter_m4a_para_mp3(temp_audio_path)
            if temp_mp3_path is None:
                st.error("Falha na conversão de M4A para MP3.")
                return
            arquivo_convertido = temp_mp3_path
        else:
            arquivo_convertido = temp_audio_path

        # Realizar a transcrição diretamente com o arquivo convertido
        try:
            with open(arquivo_convertido, 'rb') as audio_file:
                transcricao_text = transcricao(audio_file)  # Chama a função de transcrição
                if transcricao_text:
                    resumo_text = gerar_resumo(transcricao_text, 'transcricao')  # Chama a função de resumo
                    st.write('**Transcrição:**', transcricao_text)
                    st.write(resumo_text)
        except Exception as e:
            st.error(f"Erro ao processar a transcrição: {e}")
        
        # Limpar os arquivos temporários
        os.remove(temp_audio_path)
        if arquivo_convertido != temp_audio_path:
            os.remove(arquivo_convertido)

def transcrever_tab_vid():
    arquivo_video = st.file_uploader('Faça o upload de um arquivo de vídeo em formato MP4 ou MOV para transcrição', type=['mp4', 'mov'])

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
