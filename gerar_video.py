import asyncio
import csv
import json
import sys
import urllib.request
from pathlib import Path

import edge_tts
from moviepy import AudioFileClip, ColorClip, CompositeVideoClip, ImageClip, TextClip

sys.stdout.reconfigure(encoding="utf-8")

CSV_PATH = Path(__file__).parent / "achadinhos.csv"
TEMP_DIR = Path(__file__).parent / "temp_video"
OUTPUT_DIR = Path(__file__).parent / "videos"

VOZ = "pt-BR-FranciscaNeural"
W, H = 1080, 1920
MAX_IMAGENS = 6


def escolher_produto(index=0):
    with CSV_PATH.open(encoding="utf-8-sig") as f:
        produtos = list(csv.DictReader(f))
    return produtos[index]


def carregar_galeria(index, imagem_padrao):
    galeria_path = TEMP_DIR / f"galeria_{index}.json"
    if galeria_path.exists():
        urls = json.loads(galeria_path.read_text(encoding="utf-8"))
        if urls:
            return urls[:MAX_IMAGENS]
    return [imagem_padrao]


def baixar_imagem(url, destino):
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=20) as resp:
        destino.write_bytes(resp.read())


async def gerar_audio(texto, destino):
    comunicador = edge_tts.Communicate(texto, VOZ)
    await comunicador.save(str(destino))


def preco_falado(valor):
    reais = int(valor)
    centavos = round((valor - reais) * 100)
    if centavos == 0:
        return f"{reais} reais"
    return f"{reais} reais e {centavos} centavos"


def montar_texto_narracao(produto):
    preco = preco_falado(float(produto["preco_atual"]))
    desconto = produto["desconto_pct"]
    return (
        f"Olha esse preco! {produto['titulo']}, por apenas {preco}, "
        f"com {desconto} por cento de desconto. "
        f"Comenta aqui embaixo que eu te mando o link!"
    )


def gerar_video(produto, index=0):
    TEMP_DIR.mkdir(exist_ok=True)
    OUTPUT_DIR.mkdir(exist_ok=True)

    audio_path = TEMP_DIR / f"audio_{index}.mp3"
    saida_path = OUTPUT_DIR / f"video_{index}.mp4"

    urls_imagens = carregar_galeria(index, produto["imagem"])
    print(f"Baixando {len(urls_imagens)} imagem(ns) do produto...")
    caminhos_imagens = []
    for i, url in enumerate(urls_imagens):
        caminho = TEMP_DIR / f"imagem_{index}_{i}.jpg"
        try:
            baixar_imagem(url, caminho)
            caminhos_imagens.append(caminho)
        except Exception as e:
            print(f"  aviso: falha ao baixar imagem {i}: {e}")
    if not caminhos_imagens:
        raise RuntimeError("Nenhuma imagem baixada com sucesso.")

    print("Gerando narracao...")
    texto = montar_texto_narracao(produto)
    print("Texto:", texto)
    asyncio.run(gerar_audio(texto, audio_path))

    audio = AudioFileClip(str(audio_path))
    duracao = audio.duration + 1.0

    fundo = ColorClip(size=(W, H), color=(15, 17, 21)).with_duration(duracao)

    n = len(caminhos_imagens)
    fatia = duracao / n
    clipes_imagens = []
    for i, caminho in enumerate(caminhos_imagens):
        inicio = i * fatia
        img_probe = ImageClip(str(caminho))
        escala_base = min(W / img_probe.w, H / img_probe.h) * 0.85

        def zoom(t, escala_base=escala_base, fatia=fatia):
            return escala_base * (1 + 0.08 * (t / fatia))

        clip = (
            ImageClip(str(caminho))
            .with_duration(fatia)
            .resized(zoom)
            .with_position("center")
            .with_start(inicio)
        )
        clipes_imagens.append(clip)

    preco_txt = f"R$ {float(produto['preco_atual']):.2f}".replace(".", ",")
    desconto_txt = f"{produto['desconto_pct']}% OFF"

    texto_preco = (
        TextClip(text=preco_txt, font_size=90, color="#ff6b35", stroke_color="black", stroke_width=3)
        .with_duration(duracao)
        .with_position(("center", int(H * 0.72)))
    )

    texto_desconto = (
        TextClip(text=desconto_txt, font_size=55, color="white", stroke_color="black", stroke_width=2)
        .with_duration(duracao)
        .with_position(("center", int(H * 0.80)))
    )

    texto_cta = (
        TextClip(
            text="Comenta aqui embaixo\nque eu te mando o link!",
            font_size=55,
            color="white",
            stroke_color="black",
            stroke_width=2,
            text_align="center",
        )
        .with_duration(duracao)
        .with_position(("center", int(H * 0.87)))
    )

    video = CompositeVideoClip(
        [fundo, *clipes_imagens, texto_preco, texto_desconto, texto_cta], size=(W, H)
    )
    video = video.with_audio(audio)

    print("Renderizando video...")
    video.write_videofile(str(saida_path), fps=24, codec="libx264", audio_codec="aac")

    print(f"Video gerado: {saida_path}")
    return saida_path


if __name__ == "__main__":
    index = 0
    for arg in sys.argv[1:]:
        if arg.isdigit():
            index = int(arg)
    produto = escolher_produto(index)
    gerar_video(produto, index=index)
