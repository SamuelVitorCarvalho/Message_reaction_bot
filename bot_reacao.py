import sys
import time
import os
import datetime
import winsound
import urllib.request
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager

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

# --- CONFIGURAÇÃO DE REGRAS (Lógica "OU") ---
# Cada linha dentro desta lista é um GRUPO de condições.
# Se a mensagem contiver TODAS as palavras de ALGUM grupo, ele reage.
REGRAS_DE_ACEITE = [
    ["Sede"],
    ["Niteroi"],
    ["Niterói"],
    ["Santo Afonso"],
    ["Nazareno"],
    ["PTB"],
    ["Senhora das Graças"],
    ["São Caetano"],
    ["Sao Caetano"],
]

PALAVRAS_PROIBIDAS = [
    "fiorino", "passeio grande", "utilitario", "utilitário"
]

NOME_DO_ANALISTA = "Analista"
NOME_DO_GRUPO = "PM MOTORISTAS"
NOME_DO_PERFIL = "zap_profile"
TOPICO_NTFY = os.getenv("TOPICO_NTFY", "")
LINK_ALEXA_MONKEY = os.getenv("LINK_ALEXA_MONKEY", "")

def log(mensagem):
    hora = datetime.datetime.now().strftime("%H:%M:%S")
    print(f"[{hora}] {mensagem}")

def notificar_ntfy(titulo, mensagem, tags, prioridade="default"):
    if TOPICO_NTFY:
        try:
            url = f"https://ntfy.sh/{TOPICO_NTFY}"
            data = mensagem.encode('utf-8')
            
            req = urllib.request.Request(url, data=data, method='POST')
            req.add_header("User-Agent", "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36")
            
            req.add_header("Title", titulo)
            req.add_header("Priority", prioridade)
            req.add_header("Tags", tags)
            
            urllib.request.urlopen(req)
        except Exception as e:
            log(f"⚠️ Erro ao notificar NTFY: {e}")

def disparar_alarme_total(motivo="ALERTA"):
    log(f"🚨 ATIVANDO ALARME! Motivo: {motivo} 🚨")
    
    # 1. Tenta Alexa (Voice Monkey) com Máscara
    if LINK_ALEXA_MONKEY:
        try:
            log("🐵 Enviando sinal para Alexa...")
            
            req = urllib.request.Request(LINK_ALEXA_MONKEY)
            req.add_header("User-Agent", "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36")
            
            resp = urllib.request.urlopen(req, timeout=5)
            log(f"✅ Alexa respondeu: {resp.getcode()}")
        except Exception as e:
            log(f"⚠️ FALHA NA ALEXA (Erro {e}). Verifique o Token ou URL.")

    # 2. Notifica celular (NTFY)
    notificar_ntfy("ANALISTA CHAMANDO!", "Rota detectada!", "rotating_light", "high")

    # 3. Barulho no PC
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

def iniciar_driver():
    chrome_options = Options()
    caminho_perfil = os.path.join(os.getcwd(), NOME_DO_PERFIL)
    chrome_options.add_argument(f"user-data-dir={caminho_perfil}")
    chrome_options.add_argument("--disable-blink-features=AutomationControlled")
    chrome_options.add_argument("--disable-extensions")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--start-maximized")
    
    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=chrome_options)
    driver.get("https://web.whatsapp.com")
    return driver

def abrir_conversa_inicial(driver):
    log(f"🔍 Buscando grupo: '{NOME_DO_GRUPO}'...")
    try:
        # Checa se está na tela de QR Code (espera até 15 segs)
        try:
            WebDriverWait(driver, 15).until(EC.presence_of_element_located((By.CANVAS, "")))
            log("⚠️ TELA DE QR CODE DETECTADA! Escaneie com o seu celular agora...")
            # Dá mais tempo para o humano escanear e aguarda a interface carregar
            WebDriverWait(driver, 60).until(EC.presence_of_element_located((By.ID, "pane-side")))
            log("✅ Login detectado com sucesso!")
        except:
            pass # Se não achou o canvas do QR Code, significa que já está logado

        # =======================================================
        # 🎯 NOVO SELETOR DE BUSCA (ATUALIZAÇÃO WHATSAPP WEB)
        # Baseado exatamente no <input> do seu print
        # =======================================================
        xpath_busca = (
            "//input[@placeholder='Pesquisar ou começar uma nova conversa'] | " # Pelo texto fantasma
            "//div[@id='side']//input[@type='text'] | " # Pela estrutura da barra lateral
            "//input[@data-tab='3'] | " # Pelo atributo do print
            "//div[@id='side']//div[@contenteditable='true']" # Fallback caso o WhatsApp reverta a att
        )
        
        caixa_busca = WebDriverWait(driver, 60).until(
            EC.element_to_be_clickable((By.XPATH, xpath_busca))
        )
        
        caixa_busca.click()
        # Envia o nome do grupo para a caixa de texto
        caixa_busca.send_keys(NOME_DO_GRUPO)
        time.sleep(2) 
        
        # Clica no resultado do grupo
        xpath_resultado = f'//span[contains(@title, "{NOME_DO_GRUPO}")]'
        grupo_alvo = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.XPATH, xpath_resultado))
        )
        grupo_alvo.click()
        ActionChains(driver).send_keys(Keys.ENTER).perform()
        
        WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.ID, "main")))
        log("✅ Grupo aberto!")
        
        # Limpa a caixa de pesquisa (Clica no X)
        try:
            xpath_botao_x = (
                '//button[@aria-label="End icon button"] | '
                '//button[@aria-label="Cancelar pesquisa"] | '
                '//span[@data-icon="x-alt"]/ancestor::button'
            )
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
        # 1. A MIRA BLINDADA: Busca APENAS dentro do painel lateral (pane-side)
        # E já puxa direto a LINHA inteira (role="row") que tenha a bolinha de "não lida" dentro dela.
        # Assim é impossível ele tentar ler um botão solto na tela.
        xpath_linhas_com_msg = '//div[@id="pane-side"]//div[@role="row"][.//span[contains(translate(@aria-label, "NÃO LIDA", "não lida"), "não lida") or contains(translate(@aria-label, "UNREAD", "unread"), "unread")]]'
        
        linhas_nao_lidas = driver.find_elements(By.XPATH, xpath_linhas_com_msg)
        
        for linha in linhas_nao_lidas:
            try:
                # 2. O SELETOR DE DNA: Pega o nome do contato dentro dessa linha exata.
                xpath_titulo = './/span[@title and @dir="auto"]'
                elementos_titulo = linha.find_elements(By.XPATH, xpath_titulo)
                
                if elementos_titulo:
                    nome_da_conversa = elementos_titulo[0].get_attribute('title')
                    
                    # 3. Checa se o nome do Analista está no TÍTULO
                    if NOME_DO_ANALISTA.lower() in nome_da_conversa.lower():
                        return True
            except Exception as e:
                # Se falhar ao ler o nome, ignora em silêncio e vai pro próximo chat
                continue
                
        return False
    except Exception as e:
        log(f"⚠️ [DEBUG] Erro geral no radar da barra lateral: {e}")
        return False

def verificar_regras(texto):
    texto = texto.lower().strip()
    for proibida in PALAVRAS_PROIBIDAS:
        if proibida.lower().strip() in texto: return False, f"🚫 BLOQUEADO: '{proibida}'"
    for grupo in REGRAS_DE_ACEITE:
        if all(palavra.lower().strip() in texto for palavra in grupo): return True, f"✅ APROVADO: {grupo}"
    return False, "⚠️ IGNORADO"

def reagir_mensagem_rapido(driver, mensagem_element):
    try:
        # 1. Scroll rápido (apenas se necessário)
        driver.execute_script("arguments[0].scrollIntoView({block: 'center', inline: 'nearest'});", mensagem_element)
        
        # 2. Hover Instantâneo
        time.sleep(0.05)
        actions = ActionChains(driver)
        actions.move_to_element(mensagem_element).perform()
        
        # Tenta clicar no botão de carinha (reação)
        btn_reagir = WebDriverWait(mensagem_element, 2).until(
            EC.presence_of_element_located((By.XPATH, './/span[@data-icon="react"] | .//div[@aria-label="Reagir"]'))
        )
        
        driver.execute_script("arguments[0].click();", btn_reagir)

        time.sleep(0.4)  # Pequena pausa para o painel de emojis abrir
        
        xpath_joinha = """
            //div[@aria-label="Polegar para cima"] | 
            //div[@aria-label="👍"] |
            //span[@aria-label="👍"] | 
            //img[@alt="👍"] |
            //div[@role="button" and .//img[contains(@src, "emoji")]] 
        """

        try:
            # Espera aparecer algum dos elementos acima
            btn_emoji = WebDriverWait(driver, 3).until(
                EC.element_to_be_clickable((By.XPATH, xpath_joinha))
            )
            btn_emoji.click()
            return True
        except Exception as e:
            # Se falhar no exato, tenta pegar o PRIMEIRO botão do painel de reação (geralmente é o Joinha)
            log("   ---> Joinha específico não achado. Tentando clicar no 1º emoji da lista...")
            painel = driver.find_element(By.CSS_SELECTOR, "div[role='dialog'] > div") # Tenta achar o container
            botoes = painel.find_elements(By.TAG_NAME, "div")
            if botoes:
                botoes[0].click() # Clica no primeiro
                return True
            else:
                raise e

    except Exception as e:
        log(f"--> [ERRO REAÇÃO]: {e}")
        try:
            ActionChains(driver).move_by_offset(-100, 0).click().perform()
        except:
            pass
        return False

def obter_id_e_texto(msg_element):
    try:
        # Tenta pegar ID do ancestral
        parent = msg_element.find_element(By.XPATH, "./ancestor::div[@data-id]")
        msg_id = parent.get_attribute("data-id")
        
        try:
            # Tenta pegar o container que segura todo o texto copíavel (inclui quebras de linha)
            container_texto = msg_element.find_element(By.CSS_SELECTOR, ".copyable-text")
            texto = container_texto.text.lower()
        except:
            # Se falhar, pega tudo que está dentro do elemento da mensagem
            texto = msg_element.text.lower()
            
        return msg_id, texto
    except:
        return None, ""

def main():
    os.system("taskkill /f /im chrome.exe >nul 2>&1") 
    driver = iniciar_driver()
    
    print("\n" + "="*50)
    print(" Bot de Reação Rápida para WhatsApp Web")
    print(f" Regras carregadas: {len(REGRAS_DE_ACEITE)} grupos")
    print("="*50 + "\n")
    
    if not abrir_conversa_inicial(driver):
        log("⚠️ Falha ao abrir grupo. Tentando continuar...")
    
    notificar_ntfy("Bot Reagir Iniciado", "Monitorando mensagens no grupo...", "eyes", "high")
    log("Monitoramento iniciado...")
    
    msgs_processadas = set()
    MODO_PAUSA = False
    alarme_disparado = False

    try:
        while True:
            clicar_botao_scroll_baixo(driver)
            
            # A. Verifica Analista
            analista_chamando = verificar_lateral_por_analista(driver)

            if analista_chamando:
                if not MODO_PAUSA:
                    log(f"🚨 O {NOME_DO_ANALISTA} CHAMOU! 🚨")
                    MODO_PAUSA = True
                
                if not alarme_disparado:
                    disparar_alarme_total("MENSAGEM DO ANALISTA")
                    alarme_disparado = True 
                
                time.sleep(2)
                continue
            
            # Se leu a mensagem do analista -> Volta ao normal
            if not analista_chamando and MODO_PAUSA:
                MODO_PAUSA = False
                desligar_pc_protocolo()
            
            # B. Se não está pausado, continua reagindo
            if not MODO_PAUSA:
                # Busca mensagens (apenas as últimas 5 para ser MUITO rápido)
                msgs = driver.find_elements(By.XPATH, '//div[contains(@class, "message-out") or contains(@class, "message-in")]')
                
                # Itera de trás para frente (da mais recente para a mais antiga)
                # Isso garante que a gente pegue a msg nova primeiro!
                for msg in reversed(msgs[-5:]):
                    try:
                        start_time = time.time() # Medidor de performance
                        msg_id, texto = obter_id_e_texto(msg)
                        
                        if not msg_id or msg_id in msgs_processadas:
                            continue

                        log(f"👀 Lendo: '{texto[:60]}...'")

                        deu_match, motivo = verificar_regras(texto)

                        if deu_match:
                            log(f"{motivo} Iniciando reação...")
                            
                            sucesso = reagir_mensagem_rapido(driver, msg)
                            
                            tempo = time.time() - start_time
                            if sucesso:
                                log(f"✅ REAGIDO em {tempo:.2f}s!")
                            else:
                                log("❌ Falha ao reagir")
                        elif "Bloqueado" in str(motivo):
                            log(f"{motivo}")
                        
                        msgs_processadas.add(msg_id)
                        
                    except Exception:
                        continue
            
            time.sleep(0.3) 
            
    except KeyboardInterrupt:
        log("Bot encerrado pelo usuário.")
        notificar_ntfy("Bot Encerrado", "Bot de reação foi desligado", "zzz")
        try:
            driver.quit()
        except:
            pass

if __name__ == "__main__":
    main()
