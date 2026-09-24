import re
import time
import urllib.request
from io import BytesIO
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

LARGURA, ALTURA = 1080, 1920
COR_FUNDO = (15, 17, 21)
COR_FAIXA = (255, 107, 53)
COR_TEXTO = (255, 255, 255)

FONTES_CANDIDATAS = [
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    "C:/Windows/Fonts/arialbd.ttf",
    "C:/Windows/Fonts/arial.ttf",
]


def _fonte(tamanho):
    for caminho in FONTES_CANDIDATAS:
        if Path(caminho).exists():
            return ImageFont.truetype(caminho, tamanho)
    return ImageFont.load_default()


def _slug(titulo):
    s = re.sub(r"[^a-zA-Z0-9]+", "-", titulo.lower()).strip("-")
    return s[:60]


def _preco_str(valor):
    valor = float(valor)
    return f"R$ {valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def gerar_imagem_story(produto, pasta_saida):
    pasta_saida = Path(pasta_saida)
    pasta_saida.mkdir(parents=True, exist_ok=True)

    with urllib.request.urlopen(produto["imagem"], timeout=30) as resp:
        foto = Image.open(BytesIO(resp.read())).convert("RGB")

    canvas = Image.new("RGB", (LARGURA, ALTURA), COR_FUNDO)

    max_w, max_h = LARGURA - 80, 1300
    escala = min(max_w / foto.width, max_h / foto.height)
    novo_w, novo_h = int(foto.width * escala), int(foto.height * escala)
    foto = foto.resize((novo_w, novo_h))
    canvas.paste(foto, ((LARGURA - novo_w) // 2, 260))

    draw = ImageDraw.Draw(canvas)

    fonte_titulo = _fonte(56)
    titulo = produto["titulo"]
    linhas = []
    palavras = titulo.split()
    linha_atual = ""
    for palavra in palavras:
        teste = (linha_atual + " " + palavra).strip()
        if draw.textlength(teste, font=fonte_titulo) > LARGURA - 100:
            linhas.append(linha_atual)
            linha_atual = palavra
        else:
            linha_atual = teste
    if linha_atual:
        linhas.append(linha_atual)
    linhas = linhas[:3]

    y = 60
    for linha in linhas:
        draw.text((50, y), linha, font=fonte_titulo, fill=COR_TEXTO)
        y += 68

    faixa_topo = 260 + novo_h + 40
    draw.rectangle([(0, faixa_topo), (LARGURA, faixa_topo + 260)], fill=COR_FAIXA)

    fonte_preco = _fonte(72)
    draw.text((50, faixa_topo + 20), _preco_str(produto["preco_atual"]), font=fonte_preco, fill=COR_TEXTO)

    fonte_link = _fonte(58)
    bola_y = faixa_topo + 130 + 28
    draw.ellipse([(50, bola_y - 12), (74, bola_y + 12)], fill=COR_TEXTO)
    draw.text((95, faixa_topo + 130), "LINK NA BIO!", font=fonte_link, fill=COR_TEXTO)

    nome_arquivo = f"{_slug(titulo)}-{int(time.time())}.jpg"
    caminho = pasta_saida / nome_arquivo
    canvas.save(caminho, "JPEG", quality=90)
    return caminho
