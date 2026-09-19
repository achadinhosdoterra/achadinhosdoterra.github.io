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
HOJE_PATH = Path(__file__).parent / "docs" / "hoje" / "index.html"
GRAPH_URL = "https://graph.instagram.com/v21.0"

HOJE_TEMPLATE = """<!DOCTYPE html>
<html lang="pt-BR">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<meta http-equiv="refresh" content="0; url={link}">
<title>Achadinhos do Terra</title>
<style>
  body {{
    margin: 0;
    height: 100vh;
    display: flex;
    align-items: center;
    justify-content: center;
    background: #0f1115;
    color: #f2f2f2;
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
    text-align: center;
    padding: 24px;
  }}
  a {{ color: #ff6b35; font-weight: 600; }}
</style>
<script>window.location.replace("{link}");</script>
</head>
<body>
  <p>Redirecionando para o achadinho de hoje...<br><a href="{link}">Clique aqui se não for redirecionado</a></p>
</body>
</html>
"""


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


def gerar_pagina_hoje(link_afiliado):
    HOJE_PATH.parent.mkdir(parents=True, exist_ok=True)
    HOJE_PATH.write_text(HOJE_TEMPLATE.format(link=link_afiliado), encoding="utf-8")
    print(f"Pagina de redirecionamento atualizada em {HOJE_PATH} -> {link_afiliado}")


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
        gerar_pagina_hoje(link_afiliado)
        print("\nNao esqueca de dar commit/push em docs/hoje/index.html")


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
