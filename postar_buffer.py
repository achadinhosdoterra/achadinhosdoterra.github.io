import json
import urllib.error
import urllib.request

BUFFER_API_URL = "https://api.buffer.com/graphql"


def buffer_graphql(env, query):
    req = urllib.request.Request(
        BUFFER_API_URL,
        data=json.dumps({"query": query}).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {env['BUFFER_API_KEY']}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            resultado = json.loads(resp.read())
    except urllib.error.HTTPError as e:
        print("Erro HTTP da API do Buffer:", e.read().decode())
        raise
    if resultado.get("errors"):
        raise RuntimeError(f"Erro da API do Buffer: {resultado['errors']}")
    return resultado["data"]


def _preco_str(valor):
    valor = float(valor)
    return f"R$ {valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def _escapar(texto):
    return texto.replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n")


def publicar_tiktok(env, produto, link_afiliado, publicar=False):
    video_url = produto.get("video_url")

    print("=== PREVIA DO POST (TIKTOK via Buffer) ===")
    print(f"Produto: {produto['titulo']}")

    if not video_url:
        print("Sem video disponivel (real ou gerado) - TikTok exige video, pulando este produto.")
        print("=======================")
        return None

    texto = (
        f"{produto['titulo']} 👀\n\n"
        f"💰 {_preco_str(produto['preco_atual'])}\n\n"
        f"🔗 Link no nosso Instagram ou Telegram: @achadinhosdoterra\n\n"
        f"#achadinhos #achadinhosdoterra #promocao"
    )
    print(f"Video: {video_url}")
    print("Texto:")
    print(texto)
    print("=======================")

    if not publicar:
        print("\n(modo teste: nada foi publicado. Rode com --publicar para postar de verdade)")
        return None

    assets = f'{{video: {{url: "{_escapar(video_url)}"}}}}'
    query = f"""
    mutation {{
      createPost(input: {{
        channelId: "{env['BUFFER_TIKTOK_CHANNEL_ID']}"
        mode: addToQueue
        schedulingType: automatic
        needsApproval: false
        text: "{_escapar(texto)}"
        assets: [{assets}]
        metadata: {{tiktok: {{title: "{_escapar(produto['titulo'][:150])}"}}}}
      }}) {{
        __typename
        ... on PostActionSuccess {{ post {{ id status }} }}
        ... on InvalidInputError {{ message }}
        ... on UnexpectedError {{ message }}
        ... on RestProxyError {{ message code }}
        ... on LimitReachedError {{ message }}
        ... on UnauthorizedError {{ message }}
        ... on NotFoundError {{ message }}
      }}
    }}
    """
    resultado = buffer_graphql(env, query)
    payload = resultado["createPost"]
    if payload["__typename"] != "PostActionSuccess":
        raise RuntimeError(f"Falha ao criar post no TikTok via Buffer: {payload}")
    print("Publicado (na fila) no TikTok! ID:", payload["post"]["id"], "status:", payload["post"]["status"])
    return payload["post"]["id"]
