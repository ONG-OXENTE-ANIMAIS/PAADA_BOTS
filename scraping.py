import requests
from bs4 import BeautifulSoup

pagina = requests.get('https://books.toscrape.com')

dados_pagina = BeautifulSoup(pagina.text, 'html.parser')

pagina_livros = dados_pagina.find_all('li', class_="col-xs-6 col-sm-4 col-md-3 col-lg-3")

for livro in pagina_livros:
    titulo = livro.find('h3').find('a')['title']
    preco = livro.find('p', class_='price_color').text
    print(f'Título: {titulo} | Preço: {preco}')