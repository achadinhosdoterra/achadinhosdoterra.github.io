import asyncio
import shutil
import sys
import urllib.request
from pathlib import Path

import edge_tts
from moviepy import AudioFileClip, ColorClip, CompositeVideoClip, ImageClip, TextClip

sys.stdout.reconfigure(encoding="utf-8")

VOZ = "pt-BR-FranciscaNeural"
W, H = 1080, 1920
MAX_IMAGENS = 6


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
    desconto = produto.get("desconto_pct", "0")
    trecho_desconto = f", com {desconto} por cento de desconto" if str(desconto) not in ("0", "") else ""
    return (
        f"Olha esse preco! {produto['titulo']}, por apenas {preco}{trecho_desconto}. "
        f"Link no Instagram e no Telegram, corre la!"
    )


def gerar_video(produto, output_dir, nome_base):
    """Gera um video slideshow (zoom + narracao) a partir das imagens do produto.

    produto: dict com titulo, preco_atual, desconto_pct e imagens (lista de URLs).
    Retorna o Path do mp4 gerado.
    """
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    temp_dir = output_dir / f"_tmp_{nome_base}"
    temp_dir.mkdir(parents=True, exist_ok=True)

    audio_path = temp_dir / "audio.mp3"
    saida_path = output_dir / f"{nome_base}.mp4"

    urls_imagens = produto["imagens"][:MAX_IMAGENS]
    print(f"Baixando {len(urls_imagens)} imagem(ns) do produto...")
    caminhos_imagens = []
    for i, url in enumerate(urls_imagens):
        caminho = temp_dir / f"imagem_{i}.jpg"
        try:
            baixar_imagem(url, caminho)
            caminhos_imagens.append(caminho)
        except Exception as e:
            print(f"  aviso: falha ao baixar imagem {i}: {e}")
    if not caminhos_imagens:
        shutil.rmtree(temp_dir, ignore_errors=True)
        raise RuntimeError("Nenhuma imagem baixada com sucesso.")

    print("Gerando narracao...")
    texto = montar_texto_narracao(produto)
    print("Texto:", texto)
    asyncio.run(gerar_audio(texto, audio_path))

    audio = AudioFileClip(str(audio_path))
    duracao = audio.duration + 1.0

    fundo = ColorClip(size=(W, H), color=(15, 17, 21)).with_duration(duracao)

    IMG_TOPO = 60
    IMG_MAX_W, IMG_MAX_H = W - 100, 1150

    n = len(caminhos_imagens)
    fatia = duracao / n
    clipes_imagens = []
    for i, caminho in enumerate(caminhos_imagens):
        inicio = i * fatia
        img_probe = ImageClip(str(caminho))
        escala = min(IMG_MAX_W / img_probe.w, IMG_MAX_H / img_probe.h)

        clip = (
            ImageClip(str(caminho))
            .with_duration(fatia)
            .resized(escala)
            .with_position(("center", IMG_TOPO))
            .with_start(inicio)
        )
        clipes_imagens.append(clip)

    preco_txt = f"R$ {float(produto['preco_atual']):.2f}".replace(".", ",")
    desconto = str(produto.get("desconto_pct", "0"))

    TEXTO_TOPO = IMG_TOPO + IMG_MAX_H + 40

    textos_overlay = [
        TextClip(
            text=preco_txt,
            font_size=90,
            color="#ff6b35",
            stroke_color="black",
            stroke_width=3,
            margin=(20, 20),
        )
        .with_duration(duracao)
        .with_position(("center", TEXTO_TOPO))
    ]

    if desconto not in ("0", ""):
        desconto_txt = f"{desconto}% OFF"
        textos_overlay.append(
            TextClip(
                text=desconto_txt,
                font_size=55,
                color="white",
                stroke_color="black",
                stroke_width=2,
                margin=(20, 20),
            )
            .with_duration(duracao)
            .with_position(("center", TEXTO_TOPO + 140))
        )

    video = CompositeVideoClip([fundo, *clipes_imagens, *textos_overlay], size=(W, H))
    video = video.with_audio(audio)

    print("Renderizando video...")
    video.write_videofile(str(saida_path), fps=24, codec="libx264", audio_codec="aac")

    shutil.rmtree(temp_dir, ignore_errors=True)
    print(f"Video gerado: {saida_path}")
    return saida_path
