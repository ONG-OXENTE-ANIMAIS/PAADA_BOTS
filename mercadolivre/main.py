"""Ponto de entrada: busca produtos no Mercado Livre e (em breve) gera links de afiliados.

Fluxo:
    1. Carrega o token do .env
    2. Busca produtos pela API oficial (teste_busca_produtos.executar_busca)
    3. Seleciona os primeiros produtos válidos (limit)
    4. Extrai os links dos produtos
    5. Passa os links para o link_afiliados.py        <- PENDENTE
    6. Exibe os links no terminal
"""

import os
import sys
from types import SimpleNamespace

from teste_busca_produtos import carregar_env_local, configurar_console, executar_busca

PALAVRA_CHAVE = "monitor gamer"
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

    # 2 e 3. Busca e seleção dos produtos válidos
    args = SimpleNamespace(
        scan=PRODUTOS_VARRIDOS,
        limit=QUANTIDADE_PRODUTOS,
        so_promocoes=False,
        afiliados=False,
    )
    produtos = executar_busca(PALAVRA_CHAVE, args, token)
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
    # em link_afiliados.py (recebe lista de URLs? lista de dicionários? retorna algo?).
    # Será escrita depois de analisarmos esse arquivo.

    # 6. Exibição dos links de afiliados: também depende do retorno do passo 5.
    return 0


if __name__ == "__main__":
    sys.exit(main())