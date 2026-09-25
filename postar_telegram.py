import json
import urllib.error
import urllib.parse
import urllib.request

TELEGRAM_API = "https://api.telegram.org/bot{token}/{method}"


def telegram_post(env, method, **params):
    url = TELEGRAM_API.format(token=env["TELEGRAM_BOT_TOKEN"], method=method)
    data = urllib.parse.urlencode(params).encode()
    req = urllib.request.Request(url, data=data, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return json.loads(resp.read())
    except urllib.error.HTTPError as e:
        print("Erro da API do Telegram:", e.read().decode())
        raise


def _lista_imagens(produto):
    imagens = produto.get("imagens") or produto.get("imagem")
    if isinstance(imagens, str):
        imagens = imagens.split("|")
    return [i for i in imagens if i]


def _preco_str(valor):
    valor = float(valor)
    return f"R$ {valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def publicar_telegram(env, produto, link_afiliado, publicar=False):
    imagens = _lista_imagens(produto)
    caption = (
        f"{produto['titulo']}\n\n"
        f"💰 {_preco_str(produto['preco_atual'])}\n\n"
        f"🔗 {link_afiliado}"
    )

    print("=== PREVIA DO POST (TELEGRAM) ===")
    print(f"Produto: {produto['titulo']}")
    print(f"Imagens ({len(imagens)}): {imagens}")
    print("Legenda:")
    print(caption)
    print("=======================")

    if not publicar:
        print("\n(modo teste: nada foi publicado. Rode com --publicar para postar de verdade)")
        return

    chat_id = env["TELEGRAM_CHANNEL"]

    if len(imagens) > 1:
        media = [{"type": "photo", "media": url} for url in imagens[:10]]
        media[0]["caption"] = caption
        resultado = telegram_post(env, "sendMediaGroup", chat_id=chat_id, media=json.dumps(media))
    else:
        resultado = telegram_post(env, "sendPhoto", chat_id=chat_id, photo=imagens[0], caption=caption)

    print("Publicado no Telegram!", resultado.get("ok"))
