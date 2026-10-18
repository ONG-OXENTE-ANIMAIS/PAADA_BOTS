"""Obtém (ou renova) o access token OAuth 2.0 do Mercado Livre.

Fluxo completo:
    1. Preencha no .env: ML_CLIENT_ID, ML_CLIENT_SECRET e ML_REDIRECT_URI
       (valores do DevCenter > sua aplicação).
    2. python obter_token.py --url
       -> abra a URL gerada no navegador, logado na conta do Mercado Livre
       -> autorize a aplicação
       -> o navegador cai na sua redirect URI com ?code=...
    3. python obter_token.py "http://localhost:8080/callback?code=XXXX"
       -> troca o código por access token e salva em .env (sem imprimir o token)
       -> rode logo em seguida: o código de autorização expira em poucos minutos.
    4. Renove o token antes de expirar (~6h):
       python obter_token.py --atualizar

Documentação oficial:
    https://developers.mercadolivre.com.br/pt_br/autenticacao-e-autorizacao
"""

import argparse
import os
import sys
from urllib.parse import parse_qs, urlencode, urlparse

import requests

from teste_busca_produtos import CAMINHO_ENV, carregar_env_local

TOKEN_URL = "https://api.mercadolibre.com/oauth/token"
AUTH_URL = "https://auth.mercadolivre.com.br/authorization"
TIMEOUT_SEGUNDOS = 15

# offline_access é o que garante o recebimento do refresh_token.
SCOPE = "offline_access read write"


def montar_url_autorizacao(client_id, redirect_uri):
    """Monta a URL em que o usuário autoriza a aplicação no navegador."""
    parametros = {
        "response_type": "code",
        "client_id": client_id,
        "redirect_uri": redirect_uri,
        "scope": SCOPE,
    }
    return f"{AUTH_URL}?{urlencode(parametros)}"


def solicitar_token(dados):
    """Envia os dados ao endpoint de token. Devolve o JSON ou None em caso de erro."""
    try:
        resposta = requests.post(
            TOKEN_URL,
            data=dados,
            headers={"Accept": "application/json"},
            timeout=TIMEOUT_SEGUNDOS,
        )
    except requests.exceptions.Timeout:
        print(f"Erro: timeout de {TIMEOUT_SEGUNDOS}s ao acessar o endpoint de token.")
        return None
    except requests.exceptions.ConnectionError:
        print("Erro: falha de conexão com api.mercadolibre.com. Verifique sua internet.")
        return None
    except requests.exceptions.RequestException as erro:
        print(f"Erro inesperado na requisição: {erro}")
        return None

    try:
        corpo = resposta.json()
    except ValueError:
        print(f"Erro: resposta não é JSON válido (HTTP {resposta.status_code}).")
        return None

    if resposta.status_code != 200:
        detalhe = (
            corpo.get("error_description")
            or corpo.get("message")
            or corpo.get("error")
            or "detalhe não informado"
        )
        print(f"Erro HTTP {resposta.status_code} ao obter o token: {detalhe}")
        if corpo.get("error") == "invalid_grant":
            print("Dica: o código de autorização expira em poucos minutos. Gere um novo")
            print("(python obter_token.py --url) e repita o passo imediatamente.")
            print("Confirme também que a redirect_uri enviada é idêntica à configurada no DevCenter.")
        return None
    return corpo


def salvar_tokens(corpo):
    """Salva os tokens no .env, substituindo os antigos. Nunca imprime os valores."""
    access_token = corpo.get("access_token")
    refresh_token = corpo.get("refresh_token")
    if not access_token:
        print("A resposta da API não contém access_token.")
        return False

    valores = {"MELI_ACCESS_TOKEN": access_token}
    if refresh_token:
        valores["MELI_REFRESH_TOKEN"] = refresh_token

    # Reescreve o .env (ao lado do script) trocando apenas as linhas de token, preservando o resto.
    linhas = []
    restantes = dict(valores)
    if os.path.isfile(CAMINHO_ENV):
        with open(CAMINHO_ENV, encoding="utf-8") as arquivo:
            for linha in arquivo:
                chave = linha.split("=", 1)[0].strip() if "=" in linha else ""
                if chave in restantes:
                    linhas.append(f"{chave}={restantes.pop(chave)}\n")
                else:
                    linhas.append(linha if linha.endswith("\n") else linha + "\n")
    for chave, valor in restantes.items():
        linhas.append(f"{chave}={valor}\n")
    with open(CAMINHO_ENV, "w", encoding="utf-8") as arquivo:
        arquivo.writelines(linhas)

    print(
        f"Token salvo no .env (usuário {corpo.get('user_id', 'n/d')}, "
        f"expira em {corpo.get('expires_in', 'n/d')}s, escopo: {corpo.get('scope', 'n/d')})."
    )
    if not refresh_token:
        print("Atenção: a resposta não veio com refresh_token. Autorize novamente pela URL")
        print("gerada por 'python obter_token.py --url', que já pede o escopo offline_access.")
    return True


def main():
    parser = argparse.ArgumentParser(
        description="Obtém ou renova o access token OAuth do Mercado Livre."
    )
    parser.add_argument(
        "codigo",
        nargs="?",
        help="Código de autorização ou a URL de redirecionamento completa (com ?code=...)",
    )
    parser.add_argument(
        "--url", action="store_true", help="Mostra a URL de autorização da aplicação"
    )
    parser.add_argument(
        "--atualizar",
        action="store_true",
        help="Renova o access token usando o refresh token salvo no .env",
    )
    args = parser.parse_args()

    carregar_env_local()

    if args.url:
        client_id = os.environ.get("ML_CLIENT_ID")
        redirect_uri = os.environ.get("ML_REDIRECT_URI")
        if not client_id or not redirect_uri:
            print("Defina ML_CLIENT_ID e ML_REDIRECT_URI no .env (veja .env.example).")
            return 2
        print(montar_url_autorizacao(client_id, redirect_uri))
        print("\nAbra a URL acima no navegador, autorize a aplicação e, na página final,")
        print("copie a URL completa (ela contém o code) para o próximo passo.")
        return 0

    client_id = os.environ.get("ML_CLIENT_ID")
    client_secret = os.environ.get("ML_CLIENT_SECRET")
    if not client_id or not client_secret:
        print("Defina ML_CLIENT_ID e ML_CLIENT_SECRET no .env (veja .env.example).")
        return 2

    if args.atualizar:
        refresh_token = os.environ.get("MELI_REFRESH_TOKEN")
        if not refresh_token:
            print("MELI_REFRESH_TOKEN não encontrado no .env.")
            print("Rode primeiro o fluxo de autorização: python obter_token.py --url")
            return 2
        corpo = solicitar_token(
            {
                "grant_type": "refresh_token",
                "client_id": client_id,
                "client_secret": client_secret,
                "refresh_token": refresh_token,
            }
        )
        if corpo is None or not salvar_tokens(corpo):
            return 1
        return 0

    codigo = args.codigo
    if not codigo:
        try:
            codigo = input("Cole o código de autorização (ou a URL de redirecionamento): ").strip()
        except EOFError:
            codigo = ""
    if not codigo:
        print("Nenhum código informado. Use: python obter_token.py --url para começar.")
        return 2

    # Aceita tanto o código puro quanto a URL completa copiada do navegador.
    if "code=" in codigo:
        query = parse_qs(urlparse(codigo).query)
        codigo = query.get("code", [""])[0] or codigo
    if not codigo:
        print("Não consegui extrair o parâmetro 'code' da URL informada.")
        return 2

    redirect_uri = os.environ.get("ML_REDIRECT_URI")
    if not redirect_uri:
        print("Defina ML_REDIRECT_URI no .env (deve ser idêntica à do DevCenter).")
        return 2

    corpo = solicitar_token(
        {
            "grant_type": "authorization_code",
            "client_id": client_id,
            "client_secret": client_secret,
            "code": codigo,
            "redirect_uri": redirect_uri,
        }
    )
    if corpo is None or not salvar_tokens(corpo):
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
