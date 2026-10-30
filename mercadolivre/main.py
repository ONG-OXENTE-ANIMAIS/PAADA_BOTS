"""Ponto de entrada: busca produtos no Mercado Livre, gera links de afiliados e grava no Excel.

Fluxo:
    1. Carrega o token do .env
    2. Sorteia um termo e busca produtos pela API oficial (teste_busca_produtos.executar_busca)
    3. Seleciona os primeiros produtos válidos (limit)
    4. Extrai os links dos produtos
    5. Gera os links de afiliados (link_afiliados.py)      <- PENDENTE
    6. Grava os produtos na planilha ofertas.xlsx
    7. Exibe os links no terminal
"""

import os
import random
import sys
from types import SimpleNamespace

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
    print("\nLinks dos produtos encontrados:")
    for link in links_produtos:
        print(f"  {link}")

    # 5. Geração dos links de afiliados
    # PENDENTE: a chamada depende da assinatura real de gerar_links_afiliados()
    # em link_afiliados.py. Quando existir, o resultado deve ser guardado em
    # produto["link_afiliado"] para cada produto, ANTES do passo 6.

    # 6. Grava na planilha (a coluna "Link afiliado" fica vazia até o passo 5 existir)
    salvar_ofertas(produtos, palavra_chave)

    # 7. Exibição dos links de afiliados: também depende do passo 5.
    return 0


if __name__ == "__main__":
    sys.exit(main())