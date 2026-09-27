import csv
import json
import sys
from collections import Counter
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")

from gerar_imagem_story import _slug, gerar_imagem_story, normalizar_imagens_feed
from gerar_video import gerar_video
from postar_instagram import load_env, publicar_feed, publicar_story
from postar_telegram import avisar_fila_vazia, publicar_telegram
from postar_buffer import publicar_tiktok

FILA_PATH = Path(__file__).parent / "fila.csv"
PUBLICADOS_PATH = Path(__file__).parent / "publicados.csv"
TEMP_PATH = Path(__file__).parent / "temp_video" / "post_atual.json"
IMAGENS_DIR = Path(__file__).parent / "imagens_geradas"
STORIES_DIR = Path(__file__).parent / "stories_geradas"
VIDEOS_DIR = Path(__file__).parent / "videos_gerados"
MARCADOR_FILA_VAZIA = Path(__file__).parent / ".aviso_fila_vazia"

REPO = "achadinhosdoterra/achadinhosdoterra.github.io"
MAX_STORIES_POR_PRODUTO = 2


def carregar_fila():
    if not FILA_PATH.exists():
        return []
    with FILA_PATH.open(encoding="utf-8-sig") as f:
        return list(csv.DictReader(f))


def carregar_publicados():
    if not PUBLICADOS_PATH.exists():
        return []
    with PUBLICADOS_PATH.open(encoding="utf-8-sig") as f:
        return list(csv.DictReader(f))


def escolher_para_feed():
    fila = carregar_fila()
    publicados = carregar_publicados()
    ja_postados_feed = {p["titulo"] for p in publicados if p.get("tipo") == "feed"}
    for produto in fila:
        if produto["titulo"] not in ja_postados_feed:
            return produto
    return None


def escolher_para_story():
    fila = carregar_fila()
    publicados = carregar_publicados()
    fila_por_titulo = {p["titulo"]: p for p in fila}

    contagem_stories = Counter(p["titulo"] for p in publicados if p.get("tipo") == "story")
    postados_feed = [p for p in publicados if p.get("tipo") == "feed"]
    postados_feed.sort(key=lambda p: p.get("data_publicacao", ""), reverse=True)

    titulos_vistos = list(dict.fromkeys(p["titulo"] for p in postados_feed))
    candidatos = [
        t for t in titulos_vistos if t in fila_por_titulo and contagem_stories[t] < MAX_STORIES_POR_PRODUTO
    ]
    if candidatos:
        candidatos.sort(key=lambda t: contagem_stories[t])
        return fila_por_titulo[candidatos[0]]

    ja_postados_feed = set(titulos_vistos)
    for produto in fila:
        if produto["titulo"] not in ja_postados_feed and contagem_stories[produto["titulo"]] == 0:
            return produto

    return None


def preparar(tipo):
    produto = escolher_para_feed() if tipo == "feed" else escolher_para_story()
    if not produto:
        print(f"Fila vazia: nenhum produto disponivel para {tipo}. Abastecer fila.csv.")
        if tipo == "feed":
            if not MARCADOR_FILA_VAZIA.exists():
                avisar_fila_vazia(load_env())
                MARCADOR_FILA_VAZIA.write_text("aviso enviado")
            else:
                print("(aviso ja enviado anteriormente, nao vou repetir)")
        return

    if MARCADOR_FILA_VAZIA.exists():
        MARCADOR_FILA_VAZIA.unlink()

    base = Path(__file__).parent
    TEMP_PATH.parent.mkdir(parents=True, exist_ok=True)

    if tipo == "feed":
        caminhos = normalizar_imagens_feed(produto, IMAGENS_DIR)
        relativos = [c.relative_to(base).as_posix() for c in caminhos]

        video_gerado_rel = None
        if not produto.get("video_url"):
            try:
                imagens_video = produto.get("imagens")
                if isinstance(imagens_video, str):
                    imagens_video = [u for u in imagens_video.split("|") if u]
                video_produto = dict(produto)
                video_produto["imagens"] = imagens_video
                caminho_video = gerar_video(video_produto, VIDEOS_DIR, nome_base=_slug(produto["titulo"]))
                video_gerado_rel = caminho_video.relative_to(base).as_posix()
                print("Video gerado para TikTok (fallback, sem video real do anuncio):", video_gerado_rel)
            except Exception as e:
                print(f"Aviso: falha ao gerar video fallback para TikTok, produto seguira sem video no TikTok: {e}")

        with TEMP_PATH.open("w", encoding="utf-8") as f:
            json.dump(
                {"tipo": tipo, "produto": produto, "imagens_geradas": relativos, "video_gerado": video_gerado_rel},
                f,
                ensure_ascii=False,
            )
        print(f"Imagens preparadas para feed ({len(relativos)}):", relativos)
    else:
        caminho = gerar_imagem_story(produto, STORIES_DIR)
        relativo = caminho.relative_to(base).as_posix()
        with TEMP_PATH.open("w", encoding="utf-8") as f:
            json.dump({"tipo": tipo, "produto": produto, "imagens_geradas": [relativo]}, f, ensure_ascii=False)
        print("Imagem preparada para story:", relativo)


def publicar_preparado(publicar):
    if not TEMP_PATH.exists():
        print("Nenhum post preparado (rode --preparar antes). Nada a fazer.")
        return
    with TEMP_PATH.open(encoding="utf-8") as f:
        dados = json.load(f)

    produto_original = dict(dados["produto"])
    produto = dict(produto_original)
    produto["imagens"] = [
        f"https://raw.githubusercontent.com/{REPO}/main/{rel}" for rel in dados["imagens_geradas"]
    ]

    video_gerado_rel = dados.get("video_gerado")
    if video_gerado_rel:
        produto["video_url"] = f"https://raw.githubusercontent.com/{REPO}/main/{video_gerado_rel}"

    env = load_env()
    if dados["tipo"] == "feed":
        publicar_feed(env, produto, publicar=publicar, link_afiliado=produto["link_afiliado"])
        publicar_telegram(env, produto_original, link_afiliado=produto_original["link_afiliado"], publicar=publicar)
        try:
            publicar_tiktok(env, produto, link_afiliado=produto["link_afiliado"], publicar=publicar)
        except Exception as e:
            print(f"Aviso: falha ao publicar no TikTok (Instagram/Telegram ja foram, seguindo em frente): {e}")
    else:
        publicar_story(env, produto, publicar=publicar, link_afiliado=produto["link_afiliado"])

    TEMP_PATH.unlink()


if __name__ == "__main__":
    publicar = "--publicar" in sys.argv
    preparar_flag = "--preparar" in sys.argv
    tipo = "feed"
    for arg in sys.argv[1:]:
        if arg.startswith("--tipo="):
            tipo = arg.split("=", 1)[1]

    if tipo not in ("feed", "story"):
        raise SystemExit("--tipo= deve ser feed ou story")

    if preparar_flag:
        preparar(tipo)
    else:
        publicar_preparado(publicar)
