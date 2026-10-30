from teste_busca_produtos import executar_busca
from types import SimpleNamespace

# Configurações da busca
args = SimpleNamespace(
    scan=15,
    limit=5,
    so_promocoes=False,
    afiliados=False
)

# Executa a busca
produtos = executar_busca(
    "monitor gamer",
    args,
    "SEU_ACCESS_TOKEN"
)

# Percorre os produtos encontrados
for produto in produtos:
    print("Nome:", produto["nome"])
    print("Link:", produto["url"])
    print("Preço:", produto["preco"])
    print("Preço original:", produto["preco_original"])
    print("Desconto:", produto["desconto"])
    print("-" * 40)
