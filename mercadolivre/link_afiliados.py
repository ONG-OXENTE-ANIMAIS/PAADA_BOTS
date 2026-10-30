"""Automação do gerador de links de afiliados do Mercado Livre (Selenium).

Usa um perfil próprio do Chrome (pasta perfil_chrome/, ao lado deste arquivo)
para manter o login entre execuções. O Selenium NÃO usa o seu Chrome do dia a dia,
então o login precisa ser feito uma vez nesse perfil.

O main.py importa gerar_links_afiliados(). Uso direto, para login e testes:
    python link_afiliados.py --login              # 1ª vez: abre o navegador para você logar
    python link_afiliados.py --testar "<link>"    # gera o link de afiliado e mostra no terminal

Como o link é lido: depois de clicar em Gerar, o código clica em Copiar e lê o link
na área de transferência (pyperclip). Isso sobrescreve o que você tinha copiado.
"""

import argparse
import os
import sys

import pyperclip
from selenium import webdriver
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

URL_GERADOR = "https://www.mercadolivre.com.br/afiliados/linkbuilder#hub"
PASTA_SCRIPT = os.path.dirname(os.path.abspath(__file__))
PASTA_PERFIL = os.path.join(PASTA_SCRIPT, "perfil_chrome")
ESPERA_SEGUNDOS = 20

# Seletores tirados do HTML enviado. O botão Gerar tem um id gerado (_R_...) que muda a cada
# carregamento da página, por isso a busca é pela classe, e não pelo id.
CAMPO_URL = (By.ID, "url-0")
BOTAO_GERAR = (By.CSS_SELECTOR, "button.links-form__button")
# Só recebi o <span>Copiar</span>. Estou supondo que ele fica dentro de um <button>,
# como no botão Gerar. Se a busca falhar, é este seletor que precisa ser corrigido.
BOTAO_COPIAR = (By.XPATH, "//button[.//span[normalize-space()='Copiar']]")


def abrir_navegador():
    """Abre o Chrome com o perfil próprio. Feche outras janelas que usem esse perfil."""
    opcoes = webdriver.ChromeOptions()
    opcoes.add_argument(f"--user-data-dir={PASTA_PERFIL}")
    return webdriver.Chrome(options=opcoes)


def preencher_e_gerar(driver, link_produto):
    """Abre o gerador, digita o link no campo e clica em Gerar.

    Recarrega a página a cada chamada para começar sempre de um formulário limpo.
    """
    driver.get(URL_GERADOR)
    campo = WebDriverWait(driver, ESPERA_SEGUNDOS).until(EC.element_to_be_clickable(CAMPO_URL))
    campo.clear()
    campo.send_keys(link_produto)
    # O botão nasce desativado e só habilita depois que o campo tem conteúdo.
    botao = WebDriverWait(driver, ESPERA_SEGUNDOS).until(EC.element_to_be_clickable(BOTAO_GERAR))
    botao.click()


def ler_link_gerado(driver):
    """Clica em Copiar e devolve o link lido da área de transferência."""
    pyperclip.copy("")  # limpa antes, para não confundir com algo copiado antes
    botao = WebDriverWait(driver, ESPERA_SEGUNDOS).until(EC.element_to_be_clickable(BOTAO_COPIAR))
    botao.click()
    WebDriverWait(driver, 5).until(lambda _: pyperclip.paste().strip().startswith("http"))
    return pyperclip.paste().strip()


def gerar_link_afiliado(driver, link_produto):
    """Gera e devolve o link de afiliado de um produto."""
    preencher_e_gerar(driver, link_produto)
    return ler_link_gerado(driver)


def gerar_links_afiliados(links_produtos):
    """Gera o link de afiliado de cada link de produto, reaproveitando um único navegador.

    Recebe uma lista de URLs. Devolve um dicionário {url_do_produto: link_de_afiliado},
    com None nos produtos em que a geração falhou (o erro aparece no terminal).
    """
    resultados = {}
    driver = abrir_navegador()
    try:
        total = len(links_produtos)
        for indice, link in enumerate(links_produtos, start=1):
            print(f"  [{indice}/{total}] gerando link de afiliado...")
            try:
                resultados[link] = gerar_link_afiliado(driver, link)
            except TimeoutException:
                print(f"  Falhou (tempo esgotado): {link}")
                resultados[link] = None
    finally:
        driver.quit()
    return resultados


def modo_login():
    driver = abrir_navegador()
    try:
        driver.get(URL_GERADOR)
        input("Faça login no navegador que abriu. Quando o gerador de links aparecer, "
              "volte aqui e aperte Enter...")
    finally:
        driver.quit()
    print("Login salvo no perfil. Agora use --testar.")


def modo_testar(link):
    driver = abrir_navegador()
    try:
        link_afiliado = gerar_link_afiliado(driver, link)
        print(f"Link de afiliado lido: {link_afiliado}")
        input("Aperte Enter para fechar o navegador...")
    except TimeoutException:
        print("Algo não apareceu a tempo. Possíveis causas:")
        print("  - o perfil não está logado (rode 'python link_afiliados.py --login');")
        print("  - o botão Copiar não foi encontrado (o seletor BOTAO_COPIAR pode estar errado);")
        print("  - o clique em Copiar não colocou o link na área de transferência.")
        input("Olhe a página e aperte Enter para fechar o navegador...")
    finally:
        driver.quit()


def main():
    parser = argparse.ArgumentParser(description="Gerador de links de afiliados (Selenium).")
    parser.add_argument("--login", action="store_true", help="abre o navegador para fazer login")
    parser.add_argument("--testar", metavar="LINK", help="gera o link de afiliado de um produto e mostra no terminal")
    args = parser.parse_args()

    if args.login:
        modo_login()
    elif args.testar:
        modo_testar(args.testar)
    else:
        parser.print_help()
    return 0


if __name__ == "__main__":
    sys.exit(main())