import time
import os
import datetime
import winsound
import urllib.request
import urllib.parse 
import sys
import psutil
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys 
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
from selenium.common.exceptions import StaleElementReferenceException, NoSuchElementException

def carregar_variaveis_env():
    base_dir = os.path.dirname(os.path.abspath(__file__))
    candidatos = [
        os.path.join(base_dir, ".env"),
        os.path.join(os.path.dirname(base_dir), ".env"),
        os.path.join(os.getcwd(), ".env"),
    ]

    for caminho in candidatos:
        if not os.path.isfile(caminho):
            continue
        try:
            with open(caminho, "r", encoding="utf-8") as arquivo_env:
                for linha in arquivo_env:
                    linha = linha.strip()
                    if not linha or linha.startswith("#") or "=" not in linha:
                        continue
                    chave, valor = linha.split("=", 1)
                    chave = chave.strip()
                    valor = valor.strip().strip('"').strip("'")
                    if chave and chave not in os.environ:
                        os.environ[chave] = valor
            break
        except Exception:
            pass

carregar_variaveis_env()

# --- CONFIGURAÇÕES ---
REGRAS_DE_ACEITE = [
    ["Betim"],
    ["Juatuba_1"],
    ["Brumadinho Central"],
    ["Niterói"],
    ["Niteroi"],
    ["Santo Afonso"],
    ["Petrovale"],
    ["PTB"],
    ["Cruzeiro"],
    ["Dom Bosco"],
    ["Vianópolis"],
    ["Vianopolis"],
]

PALAVRAS_PROIBIDAS = [
    "fiorino",
    "teresópolis", "teresopolis",
    "citrolândia", "citrolandia",
]

NOME_DO_ANALISTA = "Analista"
NOME_DO_GRUPO = "Drivers Betim" 
NOME_DO_PERFIL = "zap_profile" 
TOPICO_NTFY = os.getenv("TOPICO_NTFY", "")
LINK_ALEXA_MONKEY = os.getenv("LINK_ALEXA_MONKEY", "")

def log(mensagem):
    hora = datetime.datetime.now().strftime("%H:%M:%S") 
    print(f"[{hora}] {mensagem}")

def definir_prioridade_alta():
    """Coloca o script como prioridade ALTA no Windows"""
    try:
        pid = os.getpid()
        py_process = psutil.Process(pid)
        py_process.nice(psutil.HIGH_PRIORITY_CLASS)
        log("🚀 Prioridade de CPU definida para ALTA!")
    except: pass

def notificar_ntfy(titulo, mensagem, tags, prioridade="default"):
    if TOPICO_NTFY:
        try:
            url = f"https://ntfy.sh/{TOPICO_NTFY}"
            data = mensagem.encode('utf-8')
            req = urllib.request.Request(url, data=data, method='POST')
            req.add_header("User-Agent", "Mozilla/5.0")
            req.add_header("Title", titulo)
            req.add_header("Priority", prioridade)
            req.add_header("Tags", tags)
            urllib.request.urlopen(req)
        except: pass
    
def clicar_botao_scroll_baixo(driver):
    """Busca e clica no círculo de rolagem baseado no seu print (aria-label correto)."""
    try:
        # Seletor exato baseado no print: aria-label="Deslizar para o fim da página"
        # Também busca pelo data-icon que aparece dentro do botão
        seletor = 'button[aria-label="Deslizar para o fim da página"], span[data-icon="ic-chevron-down-wide"]'
        
        botoes = driver.find_elements(By.CSS_SELECTOR, seletor)
        
        for btn in botoes:
            if btn.is_displayed():
                # Tenta clicar via JavaScript para ser mais garantido
                driver.execute_script("arguments[0].click();", btn)
                log("⏬ Botão 'Deslizar para o fim' clicado com sucesso!")
                return True
    except Exception as e:
        log(f"DEBUG: Erro ao tentar rolar: {e}")
    return False

def disparar_alarme_total(motivo="ALERTA"):
    log("🚨 ATIVANDO PROTOCOLO DE ACORDAR! 🚨")
    notificar_ntfy("ACORDA AGORA!", f"{motivo} Detectado!", "rotating_light", "high")
    if LINK_ALEXA_MONKEY:
        try:
            log("🐵 Chamando Alexa...")
            req = urllib.request.Request(LINK_ALEXA_MONKEY)
            req.add_header("User-Agent", "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36")
            resp = urllib.request.urlopen(req, timeout=5)
            log(f"✅ Alexa respondeu: {resp.getcode()}")
        except: pass
    try:
        for _ in range(5): winsound.Beep(1500, 300)
    except: pass

def desligar_pc_protocolo(mensagem="ROTA ACEITA"):
    log(f"👋 ROTA ACEITA! INICIANDO PROTOCOLO DE ENCERRAMENTO: {mensagem}")
    notificar_ntfy("Desligando PC", f"{mensagem}. Desligando em 30s...", "zzz")
    try:
        winsound.Beep(1000, 100)
        winsound.Beep(1500, 300)
    except: pass
    log("🔌 Encerrando bot...")
    os.system("shutdown /s /f /t 30")
    sys.exit(0)

def iniciar_driver():
    chrome_options = Options()
    caminho_perfil = os.path.join(os.getcwd(), NOME_DO_PERFIL)
    chrome_options.add_argument(f"user-data-dir={caminho_perfil}")
    chrome_options.add_argument("--disable-blink-features=AutomationControlled")
    # Otimizações de renderização
    chrome_options.add_argument("--disable-extensions")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--start-maximized") 
    chrome_options.add_argument("--log-level=3")
    
    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=chrome_options)
    driver.get("https://web.whatsapp.com")

    driver.implicitly_wait(0)
    return driver

def abrir_conversa_inicial(driver):
    log(f"🔍 Buscando grupo: '{NOME_DO_GRUPO}'...")
    try:
        caixa_busca = WebDriverWait(driver, 60).until(
            EC.element_to_be_clickable((By.CSS_SELECTOR, "div[contenteditable='true'][data-tab='3']"))
        )
        caixa_busca.click()
        caixa_busca.send_keys(NOME_DO_GRUPO)
        time.sleep(2) 
        
        xpath_resultado = f'//span[contains(@title, "{NOME_DO_GRUPO}")]'
        grupo_alvo = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.XPATH, xpath_resultado))
        )
        grupo_alvo.click()
        ActionChains(driver).send_keys(Keys.ENTER).perform()
        
        WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.ID, "main")))
        log("✅ Grupo aberto!")
        
        try:
            xpath_botao_x = '//button[@aria-label="Cancelar pesquisa"]'
            btn_cancelar = WebDriverWait(driver, 5).until(EC.element_to_be_clickable((By.XPATH, xpath_botao_x)))
            btn_cancelar.click()
        except:
            ActionChains(driver).send_keys(Keys.ESCAPE).perform()
            
        log("🚀 Monitoramento iniciado!")
        return True
    except Exception as e:
        log(f"❌ Erro ao abrir grupo: {e}")
        return False

def verificar_lateral_por_analista(driver):
    try:
        xpath_aviso = f'//div[@id="pane-side"]//div[@role="row"][.//span[contains(@title, "{NOME_DO_ANALISTA}")] and .//span[contains(@aria-label, "não lida")]]'
        notificacoes = driver.find_elements(By.XPATH, xpath_aviso)
        return len(notificacoes) > 0
    except: return False

def verificar_regras(texto):
    texto = texto.lower().strip()
    for proibida in PALAVRAS_PROIBIDAS:
        if proibida.lower().strip() in texto: return False, f"🚫 BLOQUEADO: '{proibida}'"
    for grupo in REGRAS_DE_ACEITE:
        if all(palavra.lower().strip() in texto for palavra in grupo): return True, f"✅ APROVADO: {grupo}"
    return False, "⚠️ IGNORADO"

def analisar_e_votar_rapido(driver, msg_element):
    """
    Função otimizada para ler e clicar em menos de 100ms
    """
    try:
        # 1. Busca o Texto (Caminho Otimizado)
        # Tenta pegar direto o texto da mensagem. Se for enquete, o texto fica em lugares específicos.
        texto_completo = msg_element.text.lower()
        
        # Se não tiver 'enquete' no texto cru, nem perde tempo processando
        # Nota: O texto da mensagem de enquete geralmente contém o título.
        
        # 2. Verifica Regras (Processamento Python Puro - Muito Rápido)
        match, motivo = verificar_regras(texto_completo)
        
        if not match:
            return False, motivo, ""

        # 3. Se deu match, procura o checkbox e clica
        # Busca APENAS checkboxes não marcados dentro desta mensagem
        checkboxes = msg_element.find_elements(By.CSS_SELECTOR, 'input[type="checkbox"][aria-checked="false"]')
        
        if checkboxes:
            # Clica no primeiro via JavaScript (Instantâneo)
            driver.execute_script("arguments[0].click();", checkboxes[0])
            # Título para o log (pega a primeira linha do texto)
            titulo = texto_completo.split('\n')[0][:30]
            return True, motivo, titulo
            
        return False, "Sem opção vazia", ""

    except StaleElementReferenceException:
        return False, "Elemento mudou", ""
    except Exception as e:
        return False, str(e), ""

def executar_bot():
    driver = None
    try:
        definir_prioridade_alta()
        os.system("taskkill /f /im chrome.exe >nul 2>&1") 
        driver = iniciar_driver()
        
        print("\n" + "="*50)
        print(f" ☢️ BOT VIGIA ATIVO: Monitorando '{NOME_DO_ANALISTA}'")
        print("="*50 + "\n")
        
        if not abrir_conversa_inicial(driver):
            log("⚠️ FALHA AO ABRIR GRUPO. TENTANDO RODAR MESMO ASSIM...")
            
        notificar_ntfy("Sexta Feira Iniciada", "Aguardando Escala...", "eyes")
        
        msgs_processadas = set()
        MODO_PAUSA = False
        alarme_disparado = False

        xpath_msgs_recentes = '(//div[contains(@class, "message-in")])[last()]'

        while True:
            # 1. Garante rolagem
            clicar_botao_scroll_baixo(driver)

            # 2. Analista chamou?
            if verificar_lateral_por_analista(driver):
                if not MODO_PAUSA:
                    log(f"🚨 O {NOME_DO_ANALISTA} CHAMOU! 🚨")
                    MODO_PAUSA = True
                
                if not alarme_disparado:
                    disparar_alarme_total()
                    alarme_disparado = True 
                
                time.sleep(2)
                continue
            
            if not verificar_lateral_por_analista(driver) and MODO_PAUSA:
                desligar_pc_protocolo()

            if MODO_PAUSA: 
                time.sleep(1)
                continue

            # 3. Processamento de Enquete (Turbo)
            try:
                # Pega a ÚLTIMA mensagem recebida instantaneamente
                msg = driver.find_element(By.XPATH, xpath_msgs_recentes)
                
                if msg.id in msgs_processadas:
                    time.sleep(0.05) 
                    continue

                votou, motivo, titulo = analisar_e_votar_rapido(driver, msg)
                
                if votou:
                    log(f"✅ VOTO REALIZADO: {titulo}")
                    # Dá um tempo para o clique ser registrado pelo servidor do Whats
                    time.sleep(0.5)
                elif "BLOQUEADO" in motivo:
                    log(f"{motivo} - {datetime.datetime.now().strftime('%H:%M:%S')}")
                
                # Marca como processada para não ler de novo no próximo loop
                msgs_processadas.add(msg.id)

            except (NoSuchElementException, StaleElementReferenceException):
                # Erros comuns de "nada novo" ou "tela atualizou", apenas ignora
                pass
            except Exception as e:
                # log(f"Erro loop: {e}") 
                pass

    except KeyboardInterrupt:
        log("Bot parado.")
    except Exception as e:
        log(f"CRASH: {e}")
        time.sleep(5)
    finally:
        if 'driver' in locals():
            try: driver.quit()
            except: pass

def supervisor():
    tentativas = 0
    while True:
        try:
            executar_bot()
        except (KeyboardInterrupt, SystemExit):
            break
        except Exception as e:
            tentativas += 1
            log(f"❌ CRASH DETECTADO (Tentativa {tentativas}): {e}")
            
            os.system("taskkill /f /im chrome.exe >nul 2>&1")
            os.system("taskkill /f /im chromedriver.exe >nul 2>&1")
            
            log("⏳ Reiniciando em 5 segundos...")
            time.sleep(5)

if __name__ == "__main__":
    supervisor()