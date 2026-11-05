import time
from pathlib import Path

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException

#Configuração do navegador
caminho_perfil = Path(__file__).parent / "chrome_profile"
opcoes = webdriver.ChromeOptions()
opcoes.add_argument("--user-data-dir=" + str(caminho_perfil))
opcoes.add_argument("--start-maximized")
navegador = webdriver.Chrome(options=opcoes)
espera = WebDriverWait(navegador, 180)
opcoes.add_experimental_option(
    "excludeSwitches", ["enable-automation"]
)
opcoes.add_experimental_option("useAutomationExtension", False)
navegador.get("https://web.whatsapp.com/")

#WhatsApp
espera.until(EC.presence_of_element_located((By.ID, "side")))
fechar = navegador.find_elements(
    By.XPATH,
    "//div[@role='dialog']//button[@aria-label='Fechar']"
)
if len(fechar) > 0:
    fechar[0].click()

#grupo
nome_grupo = "TESTE PAADA"

grupo = espera.until(EC.element_to_be_clickable(
    (By.XPATH, "//span[@title='" + nome_grupo + "']")
))

grupo.click()

campo_mensagem = espera.until(EC.element_to_be_clickable(
    (By.XPATH, "//footer//div[@contenteditable='true']")
))

#Mensagem
mensagem = [
    "🚨 PROMOÇÃO RELÂMPAGO 🚨",
    "🐕 Ração Quatree Supreme Dermato Cães Adultos (15kg)",
    "🥩 Sabor: Cordeiro e Salmão",
    "✨ A melhor alimentação para o seu pet ficar livre de coceiras indesejadas.",
    "❌ De: R$ 266,68",
    "📉 Por: R$ 232,10 (12% DE DESCONTO)",
    "👇 Clique abaixo para garantir (Estoque Limitado):",
    "🔗 git status"
]

texto_mensagem = "\n".join(mensagem)

campo_mensagem.click()
campo_mensagem.send_keys(texto_mensagem)
campo_mensagem.send_keys(Keys.ENTER)

time.sleep(3)