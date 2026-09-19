import csv
import re
import urllib.request
from datetime import datetime
from pathlib import Path

from bs4 import BeautifulSoup

URL = "https://www.mercadolivre.com.br/ofertas"
HEADERS = {"User-Agent": "Mozilla/5.0"}
OUTPUT = Path(__file__).parent / "achadinhos.csv"

GANCHOS = [
    "Gente, olha esse preço 😳",
    "Achei isso e vim correndo avisar vocês",
    "Não acreditei quando vi o preço desse aqui",
    "Esse aqui tá quase de graça, olha só",
    "Pausa pro achadinho do dia 👇",
]


def parse_sold(text):
    if not text:
        return 0
    text = text.lower().replace("vendidos", "").replace("+", "").strip()
    text = text.replace(",", ".")
    if "mil" in text:
        return int(float(text.replace("mil", "").strip()) * 1_000)
    if "m" in text:
        return int(float(text.replace("m", "").strip()) * 1_000_000)
    digits = re.sub(r"[^\d]", "", text)
    return int(digits) if digits else 0


def parse_money(aria_label):
    if not aria_label:
        return None
    numbers = re.findall(r"[\d.,]+", aria_label)
    if not numbers:
        return None
    value = numbers[0].replace(".", "").replace(",", ".")
    try:
        return float(value)
    except ValueError:
        return None


def fetch_cards():
    req = urllib.request.Request(URL, headers=HEADERS)
    html = urllib.request.urlopen(req, timeout=20).read().decode("utf-8", errors="ignore")
    soup = BeautifulSoup(html, "lxml")
    return soup.select("div.poly-card")


def extract_product(card):
    title_el = card.select_one("a.poly-component__title")
    if not title_el:
        return None
    title = title_el.get_text(strip=True)
    link = title_el.get("href", "").split("#")[0]

    img_el = card.select_one("img.poly-component__picture")
    image = img_el.get("src") if img_el else ""

    current_el = card.select_one(".poly-price__current .andes-money-amount")
    price_atual = parse_money(current_el.get("aria-label")) if current_el else None

    previous_el = card.select_one(".andes-money-amount--previous")
    price_anterior = parse_money(previous_el.get("aria-label")) if previous_el else None

    discount_el = card.select_one(".poly-price__discount-polylabel")
    desconto_text = discount_el.get_text(strip=True) if discount_el else ""
    desconto = int(re.sub(r"[^\d]", "", desconto_text)) if desconto_text else 0

    sold_el = card.select_one(".poly-component__review-compacted")
    sold_text = sold_el.get_text(" ", strip=True) if sold_el else ""
    vendidos = parse_sold(sold_text.split("|")[-1]) if "|" in sold_text else 0

    rating = ""
    if sold_el:
        rating_span = sold_el.select_one(
            "span.polylabel-label.polylabel-fs-xs.polylabel-fw-regular"
        )
        if rating_span:
            rating = rating_span.get_text(strip=True)

    if price_atual is None:
        return None

    return {
        "titulo": title,
        "preco_atual": price_atual,
        "preco_anterior": price_anterior,
        "desconto_pct": desconto,
        "vendidos": vendidos,
        "avaliacao": rating,
        "link": link,
        "imagem": image,
    }


def score(produto):
    return produto["desconto_pct"] * 2 + min(produto["vendidos"], 200_000) / 2000


def gerar_legenda(produto, idx):
    gancho = GANCHOS[idx % len(GANCHOS)]
    preco = f"R$ {produto['preco_atual']:.2f}".replace(".", ",")
    desconto = produto["desconto_pct"]
    desconto_txt = f" ({desconto}% OFF)" if desconto else ""
    return (
        f"{gancho}\n\n"
        f"{produto['titulo']} por {preco}{desconto_txt}\n\n"
        f"Link de compra nos comentários / bio 🔗\n"
        f"#achadinhos #achadinhosdoterra #promocao"
    )


def main():
    cards = fetch_cards()
    produtos = []
    vistos = set()
    for card in cards:
        produto = extract_product(card)
        if produto and produto["link"] not in vistos:
            vistos.add(produto["link"])
            produtos.append(produto)

    produtos.sort(key=score, reverse=True)

    for idx, produto in enumerate(produtos):
        produto["legenda_sugerida"] = gerar_legenda(produto, idx)

    with OUTPUT.open("w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=[
                "titulo",
                "preco_atual",
                "preco_anterior",
                "desconto_pct",
                "vendidos",
                "avaliacao",
                "link",
                "imagem",
                "legenda_sugerida",
            ],
        )
        writer.writeheader()
        writer.writerows(produtos)

    print(f"{len(produtos)} produtos salvos em {OUTPUT}")
    print(f"Atualizado em {datetime.now().strftime('%d/%m/%Y %H:%M')}")


if __name__ == "__main__":
    main()
