"""Ponto de entrada: busca produtos no Mercado Livre, gera links de afiliados e grava no Excel.

Fluxo:
    1. Carrega o token do .env
    2. Sorteia um termo e busca produtos pela API oficial (teste_busca_produtos.executar_busca)
    3. Seleciona os primeiros produtos válidos (limit)
    4. Extrai os links dos produtos
    5. Gera os links de afiliados no navegador (link_afiliados.gerar_links_afiliados)
    6. Grava os produtos e os links de afiliados na planilha ofertas.xlsx
    7. Exibe os links de afiliados no terminal
"""

import os
import random
import sys
from types import SimpleNamespace

from link_afiliados import gerar_links_afiliados
from planilha_ofertas import salvar_ofertas
from teste_busca_produtos import carregar_env_local, configurar_console, executar_busca

PALAVRAS_CHAVE = [
    "ração para cachorro",
    "ração para gato",
    "cama para cachorro",
    "arranhador para gato",
    "coleira para cachorro",
    "caixa de areia para gato",
    "bebedouro para pets",
    "brinquedo para cachorro",
]
QUANTIDADE_PRODUTOS = 5
PRODUTOS_VARRIDOS = 15  # muitos produtos de catálogo não têm ofertas; aumente se vier menos de 5


def main():
    configurar_console()

    # 1. Token do .env (mesma função que o teste_busca_produtos já usa)
    carregar_env_local()
    token = os.environ.get("MELI_ACCESS_TOKEN")
    if not token:
        print("Credencial ausente: defina MELI_ACCESS_TOKEN no .env.")
        print("Rode 'python obter_token.py --url' e depois 'python obter_token.py <code>'.")
        return 2

    # 2 e 3. Sorteio do termo, busca e seleção dos produtos válidos
    palavra_chave = random.choice(PALAVRAS_CHAVE)
    print(f'Termo sorteado: "{palavra_chave}"')
    args = SimpleNamespace(
        scan=PRODUTOS_VARRIDOS,
        limit=QUANTIDADE_PRODUTOS,
        so_promocoes=False,
        afiliados=False,
    )
    produtos = executar_busca(palavra_chave, args, token)
    if not produtos:
        print("\nNenhum produto válido retornado. Se viu erro 401 acima, o token expirou:")
        print("rode 'python obter_token.py --atualizar'.")
        return 1

    # 4. Links dos produtos
    links_produtos = [produto["url"] for produto in produtos]

    # 5. Links de afiliados (Selenium). Se o navegador falhar por completo, o programa
    # continua e grava os produtos na planilha com a coluna "Link afiliado" vazia.
    print("\nGerando links de afiliados no navegador (não use o teclado nem copie nada agora)...")
    try:
        links_afiliados = gerar_links_afiliados(links_produtos)
    except Exception as erro:
        print(f"Erro ao abrir/usar o navegador: {erro}")
        print("Confira se há outra janela usando a pasta perfil_chrome e se o login foi feito (--login).")
        links_afiliados = {}
    for produto in produtos:
        produto["link_afiliado"] = links_afiliados.get(produto["url"])

    # 6. Grava na planilha, já com o link de afiliado de cada produto
    salvar_ofertas(produtos, palavra_chave)

    # 7. Exibição dos links de afiliados
    print("\nLinks de afiliados gerados:")
    for produto in produtos:
        print(f"  {produto['nome']}")
        print(f"    {produto['link_afiliado'] or 'NÃO GERADO'}")

    gerados = sum(1 for produto in produtos if produto["link_afiliado"])
    print(f"\n{gerados} de {len(produtos)} links de afiliados gerados.")
    return 0


if __name__ == "__main__":
    sys.exit(main())