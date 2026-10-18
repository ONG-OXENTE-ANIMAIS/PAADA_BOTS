# Teste de busca de produtos - API do Mercado Livre

Experimento isolado (pasta `mercadolivre/`): busca produtos por palavra-chave
na API oficial e mostra **preço atual x preço de referência (desconto)**,
condição, vendedor, frete e link. O `.env` desta pasta guarda as credenciais
e é carregado automaticamente (mesmo rodando os scripts de outra pasta).

## Situação da API (verificada em 18/10/2026)

- A API exige OAuth 2.0 (`Authorization: Bearer <token>`); sem token, tudo responde 403.
- O antigo `/sites/MLB/search?q=` está restrito (403) e fora da documentação atual.
- Busca por palavra-chave: `GET /products/search` (Buscador de produtos do catálogo).
- Preço/desconto/vendedor: `GET /products/{id}/items` -> lista de ofertas com `price`
  (preço atual), `original_price` (preço de referência/desconto), `condition`,
  `seller_id`, `shipping.free_shipping`, `deal_ids` e `official_store_id`.
- Restrições descobertas nos testes: `buy_box_winner` e `permalink` vêm vazios em
  `GET /products/{id}` (mesma política que bloqueou o buscador antigo) e
  `GET /items/{item_id}` responde 403; o link exibido é a página oficial do produto
  (formato usado no botão de compartilhar do ML): `https://www.mercadolivre.com.br/p/{produto_id}`.
- Limitação: boa parte dos produtos de catálogo não tem ofertas ativas (404
  "No winners found"); o script varre `--scan` produtos e exibe só os que têm oferta.
  Promoção = `original_price > price` (sinal observado em ofertas reais).

## Arquivos

| Arquivo | Função |
|---|---|
| `obter_token.py` | Gera a URL de autorização, troca o code por token e renova (refresh) |
| `teste_busca_produtos.py` | Busca + ofertas com preço e desconto (menu interativo) |
| `.env` | Suas credenciais (não committado; copie de `.env.example`) |
| `Documentacao_Teste_Mercado_Livre.docx` | Documentação técnica completa do teste |

## Passo a passo

```powershell
# 1. Dependências (na raiz do projeto)
python -m pip install -r requirements.txt

# 2. Preencher credenciais nesta pasta (copie os valores do DevCenter; não cole em conversas)
cd mercadolivre
notepad .env

# 3. Obter o access token
python obter_token.py --url
#    -> abra a URL no navegador (conta do Mercado Livre logada), autorize
#    -> copie a URL final (ela contém ?code=...) e rode em seguida:
python obter_token.py "cole-aqui-a-url-com-o-code"
#    (o code expira em poucos minutos; se falhar, repita o passo)

# 4. Rodar o teste (sem argumento, abre o menu interativo no terminal)
python teste_busca_produtos.py
#    -> [1] Buscar item pelo nome  (digite, ex.: fone jbl, e Enter)
#    -> [2] Sair
#    Dica de IDE: use a opção que abre o terminal integrado
#    (VS Code: "Run Python File"). Se a execução não tiver terminal,
#    o script avisa e sugere rodar com a busca como argumento.
#    (--scan varre produtos no catálogo; muitos não têm ofertas ativas)

# ...ou passa a busca direto como argumento (sem menu):
python teste_busca_produtos.py "fone jbl" --limit 5
python teste_busca_produtos.py "capa iphone 16" --limit 5 --so-promocoes --scan 30  # só descontos reais

# 5. Renovar o token antes de expirar (~6h)
python obter_token.py --atualizar
```

Também funciona rodando da raiz do projeto com o caminho:
`python mercadolivre/teste_busca_produtos.py "fone jbl"`.

## Segurança

- Nunca cole tokens, chaves ou códigos em conversas, código-fonte ou commits.
- `.env` está no `.gitignore`; os scripts nunca imprimem valores de token.
