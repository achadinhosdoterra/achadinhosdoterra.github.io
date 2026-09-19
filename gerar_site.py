import csv
import html
from pathlib import Path

CSV_PATH = Path(__file__).parent / "achadinhos.csv"
OUTPUT_DIR = Path(__file__).parent / "docs"
OUTPUT_PATH = OUTPUT_DIR / "index.html"

CARD_TEMPLATE = """
<a class="card" href="{link}" target="_blank" rel="noopener noreferrer sponsored">
  <div class="card-img"><img src="{imagem}" alt="{titulo}"></div>
  <div class="card-body">
    <p class="titulo">{titulo}</p>
    <div class="precos">
      <span class="preco-atual">R$ {preco_atual}</span>
      {preco_anterior_html}
    </div>
    {desconto_html}
    <span class="btn">Ver oferta</span>
  </div>
</a>
"""

PAGE_TEMPLATE = """<!DOCTYPE html>
<html lang="pt-BR">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Achadinhos do Terra</title>
<style>
  :root {{
    --bg: #0f1115;
    --card-bg: #1a1d24;
    --accent: #ff6b35;
    --text: #f2f2f2;
    --muted: #9aa0ac;
  }}
  * {{ box-sizing: border-box; }}
  body {{
    margin: 0;
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
    background: var(--bg);
    color: var(--text);
  }}
  header {{
    text-align: center;
    padding: 32px 16px 20px;
  }}
  header h1 {{
    margin: 0 0 6px;
    font-size: 1.6rem;
  }}
  header p {{
    margin: 0;
    color: var(--muted);
    font-size: 0.9rem;
  }}
  .grid {{
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(160px, 1fr));
    gap: 14px;
    padding: 16px;
    max-width: 1000px;
    margin: 0 auto;
  }}
  .card {{
    background: var(--card-bg);
    border-radius: 12px;
    overflow: hidden;
    text-decoration: none;
    color: var(--text);
    display: flex;
    flex-direction: column;
    transition: transform 0.15s ease;
  }}
  .card:active {{
    transform: scale(0.97);
  }}
  .card-img {{
    aspect-ratio: 1 / 1;
    background: #fff;
  }}
  .card-img img {{
    width: 100%;
    height: 100%;
    object-fit: contain;
  }}
  .card-body {{
    padding: 10px 12px 12px;
    display: flex;
    flex-direction: column;
    gap: 6px;
    flex: 1;
  }}
  .titulo {{
    font-size: 0.82rem;
    line-height: 1.25;
    margin: 0;
    display: -webkit-box;
    -webkit-line-clamp: 2;
    -webkit-box-orient: vertical;
    overflow: hidden;
    min-height: 2.5em;
  }}
  .precos {{
    display: flex;
    align-items: baseline;
    gap: 6px;
    flex-wrap: wrap;
  }}
  .preco-atual {{
    font-weight: 700;
    font-size: 1.05rem;
    color: var(--accent);
  }}
  .preco-anterior {{
    font-size: 0.78rem;
    color: var(--muted);
    text-decoration: line-through;
  }}
  .desconto {{
    align-self: flex-start;
    background: #1f7a3f;
    color: #fff;
    font-size: 0.72rem;
    font-weight: 600;
    padding: 2px 7px;
    border-radius: 999px;
  }}
  .btn {{
    margin-top: auto;
    text-align: center;
    background: var(--accent);
    color: #fff;
    font-size: 0.82rem;
    font-weight: 600;
    padding: 8px 0;
    border-radius: 8px;
  }}
  footer {{
    text-align: center;
    color: var(--muted);
    font-size: 0.78rem;
    padding: 24px 16px 40px;
  }}
</style>
</head>
<body>
<header>
  <h1>🌎 Achadinhos do Terra</h1>
  <p>Achadinhos que valem a pena, atualizados todo dia</p>
</header>
<div class="grid">
{cards}
</div>
<footer>
  Atualizado automaticamente todos os dias &middot; Alguns links podem gerar comissão para @achadinhosdoterra
</footer>
</body>
</html>
"""


def render_card(produto):
    desconto = produto.get("desconto_pct", "").strip()
    desconto_html = f'<span class="desconto">{desconto}% OFF</span>' if desconto and desconto != "0" else ""

    preco_anterior = produto.get("preco_anterior", "").strip()
    preco_anterior_html = ""
    if preco_anterior:
        try:
            valor = float(preco_anterior)
            preco_anterior_html = f'<span class="preco-anterior">R$ {valor:.2f}</span>'.replace(".", ",")
        except ValueError:
            pass

    preco_atual = produto.get("preco_atual", "0")
    try:
        preco_atual = f"{float(preco_atual):.2f}".replace(".", ",")
    except ValueError:
        pass

    return CARD_TEMPLATE.format(
        link=html.escape(produto.get("link", "#")),
        imagem=html.escape(produto.get("imagem", "")),
        titulo=html.escape(produto.get("titulo", "")),
        preco_atual=preco_atual,
        preco_anterior_html=preco_anterior_html,
        desconto_html=desconto_html,
    )


def main():
    with CSV_PATH.open(encoding="utf-8-sig") as f:
        produtos = list(csv.DictReader(f))

    cards_html = "\n".join(render_card(p) for p in produtos)
    page = PAGE_TEMPLATE.format(cards=cards_html)

    OUTPUT_DIR.mkdir(exist_ok=True)
    OUTPUT_PATH.write_text(page, encoding="utf-8")
    print(f"Site gerado com {len(produtos)} produtos em {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
