"""Grava as ofertas encontradas em uma planilha Excel (ofertas.xlsx).

Cada execução acrescenta linhas ao final da planilha; nada é apagado.
A coluna "Link afiliado" fica vazia até o passo de afiliados preencher
produto["link_afiliado"] antes de chamar salvar_ofertas().

Um futuro bot de WhatsApp pode ler este mesmo arquivo (openpyxl ou pandas).
"""

import os
from datetime import datetime

from openpyxl import Workbook, load_workbook
from openpyxl.styles import Font
from openpyxl.utils import get_column_letter

from teste_busca_produtos import CONDICOES

PASTA_SCRIPT = os.path.dirname(os.path.abspath(__file__))
CAMINHO_PLANILHA = os.path.join(PASTA_SCRIPT, "ofertas.xlsx")

# (cabeçalho, largura da coluna)
COLUNAS = [
    ("Data/hora", 17),
    ("Termo", 22),
    ("ID produto", 14),
    ("Nome", 60),
    ("Link produto", 50),
    ("Link afiliado", 50),
    ("Preço", 12),
    ("Preço original", 15),
    ("Desconto (%)", 13),
    ("Moeda", 8),
    ("Vendedor", 14),
    ("Condição", 12),
    ("Frete grátis", 12),
    ("Critério", 14),
]
COLUNAS_PRECO = (7, 8)  # Preço e Preço original


def abrir_planilha(caminho):
    """Abre a planilha existente ou cria uma nova com o cabeçalho."""
    if os.path.isfile(caminho):
        pasta_trabalho = load_workbook(caminho)
        return pasta_trabalho, pasta_trabalho.active

    pasta_trabalho = Workbook()
    aba = pasta_trabalho.active
    aba.title = "Ofertas"
    aba.append([nome for nome, _ in COLUNAS])
    for celula in aba[1]:
        celula.font = Font(bold=True)
    for indice, (_, largura) in enumerate(COLUNAS, start=1):
        aba.column_dimensions[get_column_letter(indice)].width = largura
    aba.freeze_panes = "A2"
    return pasta_trabalho, aba


def montar_linha(produto, termo, data_hora):
    """Converte o dicionário devolvido por executar_busca() em uma linha da planilha."""
    condicao = produto.get("condicao")
    return [
        data_hora,
        termo,
        produto.get("id"),
        produto.get("nome"),
        produto.get("url"),
        produto.get("link_afiliado") or "",
        produto.get("preco"),
        produto.get("preco_original"),
        produto.get("desconto"),
        produto.get("moeda"),
        produto.get("vendedor"),
        CONDICOES.get(condicao, condicao or ""),
        "sim" if produto.get("frete_gratis") else "não",
        produto.get("criterio"),
    ]


def salvar_ofertas(produtos, termo, caminho=CAMINHO_PLANILHA):
    """Acrescenta os produtos na planilha. Devolve True se gravou."""
    if not produtos:
        return False

    pasta_trabalho, aba = abrir_planilha(caminho)
    data_hora = datetime.now().strftime("%d/%m/%Y %H:%M")

    for produto in produtos:
        aba.append(montar_linha(produto, termo, data_hora))
        for coluna in COLUNAS_PRECO:
            aba.cell(row=aba.max_row, column=coluna).number_format = "#,##0.00"

    try:
        pasta_trabalho.save(caminho)
    except PermissionError:
        print(f"Erro: não consegui salvar {caminho}.")
        print("Feche a planilha no Excel e rode o programa de novo.")
        return False

    print(f"\n{len(produtos)} produto(s) gravado(s) em {caminho}")
    return True
