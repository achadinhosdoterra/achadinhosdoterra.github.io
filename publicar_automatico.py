import csv
import json
import sys
from collections import Counter
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")

from gerar_imagem_story import gerar_imagem_story, normalizar_imagens_feed
from postar_instagram import load_env, publicar_feed, publicar_story

FILA_PATH = Path(__file__).parent / "fila.csv"
PUBLICADOS_PATH = Path(__file__).parent / "publicados.csv"
TEMP_PATH = Path(__file__).parent / "temp_video" / "post_atual.json"
IMAGENS_DIR = Path(__file__).parent / "imagens_geradas"
STORIES_DIR = Path(__file__).parent / "stories_geradas"

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

    for p in postados_feed:
        titulo = p["titulo"]
        if titulo in fila_por_titulo and contagem_stories[titulo] < MAX_STORIES_POR_PRODUTO:
            return fila_por_titulo[titulo]

    ja_postados_feed = {p["titulo"] for p in postados_feed}
    for produto in fila:
        if produto["titulo"] not in ja_postados_feed and contagem_stories[produto["titulo"]] == 0:
            return produto

    return None


def preparar(tipo):
    produto = escolher_para_feed() if tipo == "feed" else escolher_para_story()
    if not produto:
        print(f"Fila vazia: nenhum produto disponivel para {tipo}. Abastecer fila.csv.")
        return

    base = Path(__file__).parent
    TEMP_PATH.parent.mkdir(parents=True, exist_ok=True)

    if tipo == "feed":
        caminhos = normalizar_imagens_feed(produto, IMAGENS_DIR)
        relativos = [c.relative_to(base).as_posix() for c in caminhos]
        with TEMP_PATH.open("w", encoding="utf-8") as f:
            json.dump({"tipo": tipo, "produto": produto, "imagens_geradas": relativos}, f, ensure_ascii=False)
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

    produto = dict(dados["produto"])
    produto["imagens"] = [
        f"https://raw.githubusercontent.com/{REPO}/main/{rel}" for rel in dados["imagens_geradas"]
    ]

    env = load_env()
    if dados["tipo"] == "feed":
        publicar_feed(env, produto, publicar=publicar, link_afiliado=produto["link_afiliado"])
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
