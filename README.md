# achadinhosdoterra

Automação de pesquisa de achadinhos (Mercado Livre) para o perfil @achadinhosdoterra.

## O que faz

`buscar_ofertas.py` busca as ofertas do dia no Mercado Livre, filtra e ranqueia por
desconto + volume de vendas, e gera `achadinhos.csv` com título, preço, desconto,
link, imagem e uma legenda pronta para postar.

## Rodar manualmente

```
pip install -r requirements.txt
python buscar_ofertas.py
```

Isso atualiza `achadinhos.csv` na raiz do projeto.

## Importante

O link gerado é o link normal do produto. Para gerar comissão, ainda é preciso
transformar cada link em link de afiliado pelo painel do Mercado Livre Afiliados.
