import csv
import json
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import date
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")

ENV_PATH = Path(__file__).parent / ".env"
CSV_PATH = Path(__file__).parent / "achadinhos.csv"
PUBLICADOS_PATH = Path(__file__).parent / "publicados.csv"
GRAPH_URL = "https://graph.instagram.com/v21.0"
PUBLICADOS_CAMPOS = [
    "data_publicacao",
    "tipo",
    "titulo",
    "preco_atual",
    "preco_anterior",
    "desconto_pct",
    "link",
    "imagem",
    "post_id",
]


CHAVES_ENV = ["IG_APP_ID", "IG_USER_ID", "IG_ACCESS_TOKEN", "IG_APP_SECRET"]


def load_env():
    if ENV_PATH.exists():
        env = {}
        with ENV_PATH.open() as f:
            for line in f:
                line = line.strip()
                if line and "=" in line:
                    k, v = line.split("=", 1)
                    env[k] = v
        return env
    return {k: os.environ[k] for k in CHAVES_ENV if k in os.environ}


def graph_post(path, **params):
    url = f"{GRAPH_URL}/{path}"
    data = urllib.parse.urlencode(params).encode()
    req = urllib.request.Request(url, data=data, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return json.loads(resp.read())
    except urllib.error.HTTPError as e:
        print("Erro da API:", e.read().decode())
        raise


def escolher_produto(index=0, caminho=CSV_PATH):
    with caminho.open(encoding="utf-8-sig") as f:
        produtos = list(csv.DictReader(f))
    return produtos[index]


def _lista_imagens(produto):
    imagens = produto.get("imagens") or produto.get("imagem")
    if isinstance(imagens, str):
        imagens = imagens.split("|")
    return [i for i in imagens if i]


def registrar_publicacao(tipo, produto, link_afiliado, post_id):
    novo = not PUBLICADOS_PATH.exists()
    with PUBLICADOS_PATH.open("a", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=PUBLICADOS_CAMPOS)
        if novo:
            writer.writeheader()
        writer.writerow(
            {
                "data_publicacao": date.today().isoformat(),
                "tipo": tipo,
                "titulo": produto["titulo"],
                "preco_atual": produto["preco_atual"],
                "preco_anterior": produto.get("preco_anterior", ""),
                "desconto_pct": produto.get("desconto_pct", ""),
                "link": link_afiliado,
                "imagem": _lista_imagens(produto)[0],
                "post_id": post_id,
            }
        )
    print(f"Registrado em publicados.csv ({tipo}, {post_id})")


def publicar_feed(env, produto, publicar=False, link_afiliado=None):
    caption = produto["legenda_sugerida"]
    imagens = _lista_imagens(produto)

    print("=== PREVIA DO POST (FEED) ===")
    print(f"Produto: {produto['titulo']}")
    print(f"Preco: R$ {produto['preco_atual']} ({produto['desconto_pct']}% OFF)")
    print(f"Imagens ({len(imagens)}):", imagens)
    print("Legenda:")
    print(caption)
    print("=======================")

    if not publicar:
        print("\n(modo teste: nada foi publicado. Rode com --publicar para postar de verdade)")
        return

    if len(imagens) > 1:
        print("Criando itens do carrossel...")
        children = []
        for url in imagens:
            item = graph_post(
                f"{env['IG_USER_ID']}/media",
                image_url=url,
                is_carousel_item="true",
                access_token=env["IG_ACCESS_TOKEN"],
            )
            children.append(item["id"])
            print("Item criado:", item["id"])

        time.sleep(3)

        print("Criando container do carrossel...")
        container = graph_post(
            f"{env['IG_USER_ID']}/media",
            media_type="CAROUSEL",
            children=",".join(children),
            caption=caption,
            access_token=env["IG_ACCESS_TOKEN"],
        )
    else:
        print("Criando container de midia...")
        container = graph_post(
            f"{env['IG_USER_ID']}/media",
            image_url=imagens[0],
            caption=caption,
            access_token=env["IG_ACCESS_TOKEN"],
        )

    creation_id = container["id"]
    print("Container criado:", creation_id)

    time.sleep(3)

    print("Publicando...")
    result = graph_post(
        f"{env['IG_USER_ID']}/media_publish",
        creation_id=creation_id,
        access_token=env["IG_ACCESS_TOKEN"],
    )
    media_id = result.get("id")
    print("Publicado! ID do post:", media_id)

    if link_afiliado:
        registrar_publicacao("feed", produto, link_afiliado, media_id)


def publicar_reels(env, produto, video_url, publicar=False, link_afiliado=None):
    caption = produto["legenda_sugerida"]

    print("=== PREVIA DO POST (REELS) ===")
    print(f"Produto: {produto['titulo']}")
    print(f"Video: {video_url}")
    print("Legenda:")
    print(caption)
    print("=======================")

    if not publicar:
        print("\n(modo teste: nada foi publicado. Rode com --publicar para postar de verdade)")
        return

    print("Criando container do Reels...")
    container = graph_post(
        f"{env['IG_USER_ID']}/media",
        video_url=video_url,
        media_type="REELS",
        caption=caption,
        access_token=env["IG_ACCESS_TOKEN"],
    )
    creation_id = container["id"]
    print("Container:", creation_id)

    for _ in range(20):
        status = json.loads(
            urllib.request.urlopen(
                f"{GRAPH_URL}/{creation_id}?fields=status_code&access_token={env['IG_ACCESS_TOKEN']}",
                timeout=30,
            ).read()
        )
        print("status:", status)
        if status.get("status_code") == "FINISHED":
            break
        if status.get("status_code") == "ERROR":
            raise RuntimeError("Erro no processamento do video: " + str(status))
        time.sleep(5)

    print("Publicando...")
    result = graph_post(
        f"{env['IG_USER_ID']}/media_publish",
        creation_id=creation_id,
        access_token=env["IG_ACCESS_TOKEN"],
    )
    media_id = result.get("id")
    print("Publicado! ID do Reels:", media_id)

    if link_afiliado:
        registrar_publicacao("reels", produto, link_afiliado, media_id)


def publicar_story(env, produto, publicar=False, link_afiliado=None):
    imagem = _lista_imagens(produto)[0]

    print("=== PREVIA DO STORY ===")
    print(f"Produto: {produto['titulo']}")
    print(f"Imagem: {imagem}")
    print("=======================")

    if not publicar:
        print("\n(modo teste: nada foi publicado. Rode com --publicar para postar de verdade)")
        return

    container = graph_post(
        f"{env['IG_USER_ID']}/media",
        image_url=imagem,
        media_type="STORIES",
        access_token=env["IG_ACCESS_TOKEN"],
    )
    creation_id = container["id"]

    time.sleep(3)

    result = graph_post(
        f"{env['IG_USER_ID']}/media_publish",
        creation_id=creation_id,
        access_token=env["IG_ACCESS_TOKEN"],
    )
    media_id = result.get("id")
    print("Publicado! ID do Story:", media_id)

    if link_afiliado:
        registrar_publicacao("story", produto, link_afiliado, media_id)


if __name__ == "__main__":
    publicar = "--publicar" in sys.argv
    index = 0
    link_afiliado = None
    tipo = "feed"
    video_url = None
    for arg in sys.argv[1:]:
        if arg.isdigit():
            index = int(arg)
        elif arg.startswith("--link="):
            link_afiliado = arg.split("=", 1)[1]
        elif arg.startswith("--tipo="):
            tipo = arg.split("=", 1)[1]
        elif arg.startswith("--video="):
            video_url = arg.split("=", 1)[1]

    env = load_env()
    produto = escolher_produto(index)

    if tipo == "feed":
        publicar_feed(env, produto, publicar=publicar, link_afiliado=link_afiliado)
    elif tipo == "reels":
        if not video_url:
            raise SystemExit("Use --video=<url publica do video> para postar Reels")
        publicar_reels(env, produto, video_url, publicar=publicar, link_afiliado=link_afiliado)
    elif tipo == "story":
        publicar_story(env, produto, publicar=publicar, link_afiliado=link_afiliado)
    else:
        raise SystemExit("--tipo= deve ser feed, reels ou story")
