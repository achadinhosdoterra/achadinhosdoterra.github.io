import csv
import json
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")

ENV_PATH = Path(__file__).parent / ".env"
CSV_PATH = Path(__file__).parent / "achadinhos.csv"
GRAPH_URL = "https://graph.instagram.com/v21.0"


def load_env():
    env = {}
    with ENV_PATH.open() as f:
        for line in f:
            line = line.strip()
            if line and "=" in line:
                k, v = line.split("=", 1)
                env[k] = v
    return env


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


def escolher_produto(index=0):
    with CSV_PATH.open(encoding="utf-8-sig") as f:
        produtos = list(csv.DictReader(f))
    return produtos[index]


def comentar_link(env, media_id, link_afiliado):
    mensagem = f"Link de compra: {link_afiliado}"
    resultado = graph_post(
        f"{media_id}/comments",
        message=mensagem,
        access_token=env["IG_ACCESS_TOKEN"],
    )
    print("Comentario postado:", resultado.get("id"))


def publicar_feed(env, produto, publicar=False, link_afiliado=None):
    caption = produto["legenda_sugerida"]
    imagem = produto["imagem"]

    print("=== PREVIA DO POST ===")
    print(f"Produto: {produto['titulo']}")
    print(f"Preco: R$ {produto['preco_atual']} ({produto['desconto_pct']}% OFF)")
    print(f"Imagem: {imagem}")
    print("Legenda:")
    print(caption)
    print("=======================")

    if not publicar:
        print("\n(modo teste: nada foi publicado. Rode com --publicar para postar de verdade)")
        return

    print("Criando container de midia...")
    container = graph_post(
        f"{env['IG_USER_ID']}/media",
        image_url=imagem,
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
        comentar_link(env, media_id, link_afiliado)


if __name__ == "__main__":
    publicar = "--publicar" in sys.argv
    index = 0
    link_afiliado = None
    for arg in sys.argv[1:]:
        if arg.isdigit():
            index = int(arg)
        elif arg.startswith("--link="):
            link_afiliado = arg.split("=", 1)[1]

    env = load_env()
    produto = escolher_produto(index)
    publicar_feed(env, produto, publicar=publicar, link_afiliado=link_afiliado)
