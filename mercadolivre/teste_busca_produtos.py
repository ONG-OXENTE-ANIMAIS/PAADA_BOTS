"""Teste de busca de produtos na API oficial do Mercado Livre, com preço e desconto.

Fluxo verificado em 18/10/2026:
    1. GET /products/search?q=...           -> produtos do catálogo pela palavra-chave
    2. GET /products/{id}/items             -> ofertas do produto, com price,
       original_price, condition, seller_id, shipping e deal_ids

Por que este fluxo (restrições reais da API para apps comuns hoje):
    - buy_box_winner e permalink vêm vazios em /products/{id} (mesma política que
      bloqueou /sites/MLB/search);
    - /items/{item_id} (anúncio) responde 403 access_denied;
    - a busca de catálogo traz muitos produtos sem ofertas ativas (404 "No winners
      found"); por isso o script varre --scan produtos e exibe só os que têm oferta;
    - o link exibido é a página oficial do produto (o próprio ML usa este formato
      nos links de compartilhamento): https://www.mercadolivre.com.br/p/{produto_id}

Critério de oferta exibida:
    - modo normal: oferta mais barata (menor preço);
    - --so-promocoes: oferta em promoção com o maior desconto (original_price > price).

Ambos os endpoints exigem OAuth 2.0 (header Authorization: Bearer <token>).
Tokens: rode antes "python obter_token.py" (veja README_teste.md).

Uso:
    python teste_busca_produtos.py                              # menu interativo (varias buscas)
    python teste_busca_produtos.py "monitor gamer" --limit 5    # busca direta, sem menu
    python teste_busca_produtos.py "capa iphone 16" --limit 5 --so-promocoes --scan 30
"""

import argparse
import os
import sys
from datetime import datetime

import requests

BUSCA_URL = "https://api.mercadolibre.com/products/search"
OFERTAS_URL = "https://api.mercadolibre.com/products/{produto_id}/items"
LINK_PAGINA_PRODUTO = "https://www.mercadolivre.com.br/p/{produto_id}"
SITE_ID = "MLB"  # Mercado Livre Brasil
TIMEOUT_SEGUNDOS = 15

CONDICOES = {"new": "novo", "used": "usado", "refurbished": "recondicionado"}

PASTA_SCRIPT = os.path.dirname(os.path.abspath(__file__))
CAMINHO_ENV = os.path.join(PASTA_SCRIPT, ".env")

BANNER = """
==================================================================
  PAADA BOTS - Teste de busca de itens no Mercado Livre
==================================================================
Este script consulta a API oficial do Mercado Livre e mostra:
  - preço atual da oferta mais barata de cada produto
  - preço de referência e desconto, quando há promoção real
  - condição, vendedor, frete grátis e link do anúncio

Dica: a busca varre vários produtos do catálogo (muitos não têm
ofertas ativas). Ajuste com --limit e --scan se quiser.
"""


def configurar_console():
    """Garante UTF-8 no stdout para acentos no terminal Windows."""
    try:
        if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
            sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass


def carregar_env_local(caminho=None):
    """Carrega variáveis do .env que está ao lado do script, sem sobrescrever o ambiente."""
    caminho = caminho or CAMINHO_ENV
    if not os.path.isfile(caminho):
        return
    with open(caminho, encoding="utf-8-sig") as arquivo:
        for linha in arquivo:
            linha = linha.strip()
            if not linha or linha.startswith("#") or "=" not in linha:
                continue
            chave, valor = linha.split("=", 1)
            os.environ.setdefault(chave.strip(), valor.strip().strip('"').strip("'"))


def requisicao_get(url, token, params=None):
    """Faz um GET autenticado. Devolve a resposta ou None (erros já avisados)."""
    try:
        return requests.get(
            url,
            headers={"Authorization": f"Bearer {token}"},
            params=params,
            timeout=TIMEOUT_SEGUNDOS,
        )
    except requests.exceptions.Timeout:
        print(f"Erro: timeout de {TIMEOUT_SEGUNDOS}s em {url}.")
    except requests.exceptions.ConnectionError:
        print("Erro: falha de conexão com api.mercadolibre.com. Verifique sua internet.")
    except requests.exceptions.RequestException as erro:
        print(f"Erro inesperado na requisição: {erro}")
    return None


def mostrar_erro_http(resposta, contexto=""):
    """Traduz os códigos de erro mais comuns da API em mensagens úteis."""
    dicas = {
        400: "Requisição inválida (confira os parâmetros enviados).",
        401: "Não autorizado: token ausente, inválido ou expirado. Rode 'python obter_token.py --atualizar'.",
        403: "Acesso negado: o token não tem permissão para este recurso.",
        404: "Recurso não encontrado.",
        429: "Limite de requisições atingido (rate limit). Aguarde alguns segundos e tente novamente.",
        500: "Erro interno no servidor da API. Tente novamente mais tarde.",
    }
    prefixo = f"{contexto}: " if contexto else ""
    print(f"{prefixo}erro HTTP {resposta.status_code}: {dicas.get(resposta.status_code, 'erro retornado pela API.')}")
    try:
        corpo = resposta.json()
        if isinstance(corpo, dict):
            detalhe = corpo.get("message") or corpo.get("error")
            if detalhe:
                print(f"Detalhe da API: {detalhe}")
    except ValueError:
        pass


def buscar_produtos(palavra_chave, limite, token):
    """Passo 1: busca produtos de catálogo pela palavra-chave."""
    resposta = requisicao_get(
        BUSCA_URL,
        token,
        params={"site_id": SITE_ID, "status": "active", "q": palavra_chave, "limit": limite},
    )
    if resposta is None:
        return None
    if resposta.status_code != 200:
        mostrar_erro_http(resposta, "busca de produtos")
        return None
    try:
        return resposta.json()
    except ValueError:
        print("Erro: a API respondeu com conteúdo que não é JSON válido.")
        return None


def buscar_ofertas(produto_id, token):
    """Passo 2: ofertas do produto (preço, referência, vendedor, frete)."""
    resposta = requisicao_get(OFERTAS_URL.format(produto_id=produto_id), token)
    if resposta is None:
        return None
    if resposta.status_code == 404:
        return []  # produto sem ofertas ativas ("No winners found")
    if resposta.status_code != 200:
        print(f"  Aviso: ofertas de {produto_id} indisponíveis (HTTP {resposta.status_code}).")
        return None
    try:
        dados = resposta.json()
    except ValueError:
        print(f"  Aviso: resposta inválida nas ofertas de {produto_id}.")
        return None
    return dados.get("results") or []


def oferta_mais_barata(ofertas):
    """Devolve a oferta com menor preço (ou None se não houver ofertas)."""
    com_preco = [oferta for oferta in ofertas if oferta.get("price") is not None]
    if not com_preco:
        return None
    return min(com_preco, key=lambda oferta: oferta["price"])


def oferta_maior_desconto(ofertas):
    """Devolve a oferta em promoção com o maior desconto (ou None)."""
    promocoes = [oferta for oferta in ofertas if oferta_em_promocao(oferta)]
    if not promocoes:
        return None
    return max(promocoes, key=percentual_desconto)


def atributo(attributes, identificador):
    """Extrai o value_name de um atributo do catálogo (ex.: BRAND, MODEL, GTIN)."""
    for item in attributes or []:
        if item.get("id") == identificador:
            return item.get("value_name")
    return None


def formatar_desconto(preco, preco_referencia):
    """Percentual de desconto, só quando o preço atual é menor que o de referência."""
    if not preco or not preco_referencia or preco_referencia <= preco:
        return None
    return round((1 - preco / preco_referencia) * 100)


def oferta_em_promocao(oferta):
    """True quando a oferta tem preço atual menor que o preço de referência."""
    if not oferta:
        return False
    preco = oferta.get("price")
    referencia = oferta.get("original_price")
    return preco is not None and referencia is not None and referencia > preco


def percentual_desconto(oferta):
    """Percentual de desconto da oferta (para ordenar promoções)."""
    preco = oferta["price"]
    referencia = oferta["original_price"]
    return (referencia - preco) / referencia


def mostrar_produto(indice, produto, oferta, ofertas, criterio):
    """Exibe um produto: oferta em destaque + lista de todas as ofertas por preço."""
    attrs = produto.get("attributes") or []
    imagens = produto.get("pictures") or []
    imagem = imagens[0].get("url") if imagens else None

    preco = oferta.get("price") if oferta else None
    preco_referencia = oferta.get("original_price") if oferta else None
    moeda = (oferta.get("currency_id") or "BRL") if preco is not None else ""
    desconto = formatar_desconto(preco, preco_referencia)
    produto_id = produto.get("id")
    link = LINK_PAGINA_PRODUTO.format(produto_id=produto_id) if produto_id else "n/d"

    print("-" * 72)
    print(f"Produto {indice}")
    print(f"  Título        : {produto.get('name', 'n/d')}")
    print(f"  ID do produto : {produto_id or 'n/d'}")
    print(f"  ID anúncio    : {(oferta or {}).get('item_id') or 'n/d'}")
    print(f"  Link produto  : {link}")
    print(f"  Imagem        : {imagem or 'n/d'}")
    print(f"  Marca         : {atributo(attrs, 'BRAND') or 'n/d'}")
    print(f"  Ofertas       : {len(ofertas)}")
    print(f"  Critério      : {criterio}")
    print(f"  Preço atual   : {preco if preco is not None else 'n/d'} {moeda}".rstrip())
    print(f"  Preço ref.    : {preco_referencia if preco_referencia is not None else 'n/d'}")
    print(f"  Desconto      : {f'{desconto}%' if desconto else 'n/d'}")
    if oferta:
        print(f"  Condição      : {CONDICOES.get(oferta.get('condition'), oferta.get('condition') or 'n/d')}")
        print(f"  Vendedor      : {oferta.get('seller_id', 'n/d')}")
        frete = (oferta.get("shipping") or {}).get("free_shipping")
        print(f"  Frete grátis  : {'sim' if frete else 'não'}")
        loja_oficial = oferta.get("official_store_id")
        if loja_oficial:
            print(f"  Loja oficial  : {loja_oficial}")
        deal_ids = oferta.get("deal_ids") or []
        print(f"  Deal IDs      : {', '.join(str(deal) for deal in deal_ids) if deal_ids else 'nenhum'}")

    ordenadas = sorted(
        (item for item in ofertas if item.get("price") is not None),
        key=lambda item: item["price"],
    )
    if ordenadas:
        print("  Lista de ofertas (do mais barato ao mais caro):")
        for num, item in enumerate(ordenadas[:5], start=1):
            moeda_item = item.get("currency_id") or "BRL"
            desconto_item = formatar_desconto(item.get("price"), item.get("original_price"))
            marcador = f" (-{desconto_item}%)" if desconto_item else ""
            frete_item = "frete grátis" if (item.get("shipping") or {}).get("free_shipping") else "frete pago"
            cond_item = CONDICOES.get(item.get("condition"), item.get("condition") or "n/d")
            print(
                f"    {num}) {item.get('price')} {moeda_item}{marcador} | {cond_item} | {frete_item} "
                f"| vendedor {item.get('seller_id')} | {item.get('item_id')}"
            )
        if len(ordenadas) > 5:
            print(f"    ... +{len(ordenadas) - 5} ofertas (use a página do produto para ver todas)")


def executar_busca(palavra_chave, args, token):
    """Executa uma busca completa: varre produtos e exibe os resultados."""
    varredura = args.scan if args.scan is not None else max(args.limit * 3, 15)
    dados = buscar_produtos(palavra_chave, varredura, token)
    if dados is None:
        return 1

    produtos = dados.get("results") or []
    paging = dados.get("paging") or {}

    print(f'\nBusca: "{dados.get("keywords", palavra_chave)}"')
    print(f"Consultado em: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')} (preços mudam com frequência)")
    print(f"Produtos no catálogo: {paging.get('total', 'n/d')} | varridos: {len(produtos)}")
    if not produtos:
        print("Nenhum produto encontrado para essa palavra-chave.")
        return 0

    print(f"Consultas à API: 1 busca + 1 consulta de ofertas por produto (até {1 + len(produtos)} no total)")

    exibidos = 0
    em_promocao = 0
    com_ofertas = 0
    for produto in produtos:
        if exibidos >= args.limit:
            break
        ofertas = buscar_ofertas(produto.get("id"), token)
        if not ofertas:
            continue
        com_ofertas += 1
        if args.so_promocoes:
            oferta = oferta_maior_desconto(ofertas)
            if oferta is None:
                continue
            promocao = True
            criterio = "maior desconto"
        else:
            oferta = oferta_mais_barata(ofertas)
            promocao = oferta_em_promocao(oferta)
            criterio = "menor preço"
        if promocao:
            em_promocao += 1
        exibidos += 1
        mostrar_produto(exibidos, produto, oferta, ofertas, criterio)

    print("-" * 72)
    print(
        f"Resumo: varridos {len(produtos)} produtos, {com_ofertas} com ofertas ativas; "
        f"{exibidos} exibido(s), {em_promocao} com desconto real."
    )
    if args.so_promocoes and exibidos == 0:
        print("Nenhum produto com desconto entre os resultados buscados. Aumente --scan ou tente outra palavra-chave.")
    print("Obs.: preço vem de GET /products/{id}/items; destaque padrão = oferta mais barata.")
    print("Obs.: promoção = original_price > price; use --so-promocoes para destacar maior desconto.")
    return 0


def aviso_sem_terminal():
    """Mensagem quando a execução não permite digitar no terminal (ex.: algumas IDEs)."""
    print("\nNão consegui ler a entrada do teclado nesta execução (sem terminal interativo).")
    print("Soluções:")
    print('  - rode pelo terminal integrado da IDE (VS Code: "Run Python File", o Play do arquivo);')
    print('  - ou passe a busca direto no comando: python teste_busca_produtos.py "fone jbl"')
    return 2


def ler_entrada(prompt):
    """Lê uma linha do terminal. Devolve None se a execução não tem input interativo."""
    try:
        return input(prompt)
    except EOFError:
        return None
    except KeyboardInterrupt:
        raise


def menu_interativo(args, token):
    """Menu simples: buscar item pelo nome, várias vezes, até o usuário sair."""
    print(BANNER)
    while True:
        print("\n[1] Buscar item pelo nome")
        print("[2] Sair")
        try:
            opcao = ler_entrada("Opção: ")
        except KeyboardInterrupt:
            print("\nEncerrado.")
            return 0
        if opcao is None:
            return aviso_sem_terminal()
        opcao = opcao.strip().lower()
        if opcao in {"2", "sair", "exit", "quit"}:
            print("Encerrado. Até a próxima!")
            return 0
        if opcao != "1":
            print("Opção inválida. Digite 1 para buscar ou 2 para sair.")
            continue
        try:
            nome = ler_entrada("Nome do item: ")
        except KeyboardInterrupt:
            print("\nEncerrado.")
            return 0
        if nome is None:
            return aviso_sem_terminal()
        nome = nome.strip()
        if not nome:
            print("Nenhum item informado. Tente novamente.")
            continue
        executar_busca(nome, args, token)
        print()


def main():
    configurar_console()
    parser = argparse.ArgumentParser(
        description="Busca produtos no Mercado Livre e mostra preço atual x preço de referência."
    )
    parser.add_argument(
        "palavra_chave",
        nargs="?",
        default=None,
        help='Palavra-chave de busca (se omitir, abre o menu interativo no terminal)',
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=5,
        help="Quantidade máxima de produtos exibidos (padrão: 5)",
    )
    parser.add_argument(
        "--scan",
        type=int,
        default=None,
        help="Produtos varridos na busca (padrão: 3x o --limit, mínimo 15); "
        "muitos produtos de catálogo não têm ofertas ativas",
    )
    parser.add_argument(
        "--so-promocoes",
        action="store_true",
        help="Mostra apenas produtos com desconto real (preço atual < preço de referência)",
    )
    args = parser.parse_args()

    if args.limit < 1:
        print("Erro: --limit deve ser um número maior ou igual a 1.")
        return 2
    if args.scan is not None and args.scan < args.limit:
        print("Erro: --scan deve ser maior ou igual a --limit.")
        return 2

    carregar_env_local()
    token = os.environ.get("MELI_ACCESS_TOKEN")
    if not token:
        print("Credencial ausente: a API do Mercado Livre exige um access token OAuth 2.0.")
        print("Rode 'python obter_token.py --url' e depois 'python obter_token.py <code>'.")
        print("Detalhes: README_teste.md")
        return 2

    palavra_chave = (args.palavra_chave or "").strip()
    if palavra_chave:
        return executar_busca(palavra_chave, args, token)
    return menu_interativo(args, token)


def executar_com_tratamento():
    """Roda o main e registra qualquer erro inesperado em erro_execucao.log."""
    try:
        return main()
    except SystemExit:
        raise
    except KeyboardInterrupt:
        print("\nEncerrado pelo usuário (Ctrl+C).")
        return 130
    except Exception:
        import traceback

        detalhes = traceback.format_exc()
        print("\nErro inesperado no script:")
        print(detalhes)
        try:
            with open(os.path.join(PASTA_SCRIPT, "erro_execucao.log"), "w", encoding="utf-8") as arquivo:
                arquivo.write(detalhes)
            print("Detalhes gravados em erro_execucao.log (na pasta do script).")
        except OSError:
            pass
        return 1


if __name__ == "__main__":
    sys.exit(executar_com_tratamento())
