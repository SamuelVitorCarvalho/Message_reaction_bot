import time
import os
import datetime
import winsound
import urllib.request
import urllib.parse 
import sys
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys 
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import StaleElementReferenceException, WebDriverException
from webdriver_manager.chrome import ChromeDriverManager
from urllib3.exceptions import MaxRetryError 

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
TOPICO_NTFY = "alerta_de_rota_betim_Samuel_Carvalho"
LINK_ALEXA_MONKEY = "https://api-v2.voicemonkey.io/announcement?token=139b4eee6afcccd930c963d0f7203a07_e959829646e350bbcd8134d5a3377769&device=alarme" 

def log(mensagem):
    hora = datetime.datetime.now().strftime("%H:%M:%S") 
    print(f"[{hora}] {mensagem}")

def notificar_inicio_ntfy():
    if TOPICO_NTFY:
        try:
            log("🔔 Notificando início...")
            url = f"https://ntfy.sh/{TOPICO_NTFY}"
            mensagem = "A Sexta Feira está de olho nas enquetes! Bom descanso..."
            data = mensagem.encode('utf-8')
            req = urllib.request.Request(url, data=data, method='POST')
            req.add_header("Title", "Monitoramento Iniciado")
            req.add_header("Priority", "high")
            req.add_header("Tags", "robot")
            urllib.request.urlopen(req)
        except: pass

def notificar_erro_critico(erro):
    if TOPICO_NTFY:
        try:
            log(f"💀 ERRO CRITICO! Notificando celular: {erro}")
            url = f"https://ntfy.sh/{TOPICO_NTFY}"
            mensagem = f"A SEXTA FEIRA CAPOTOU! Erro: {str(erro)[:50]}... Verifique o PC!"
            data = mensagem.encode('utf-8')
            req = urllib.request.Request(url, data=data, method='POST')
            req.add_header("Title", "ERRO CRITICO - ROBO PAROU")
            req.add_header("Priority", "high")
            req.add_header("Tags", "rotating_light")
            urllib.request.urlopen(req)
        except Exception as e:
            log(f"⚠️ Falha ao enviar alerta de erro: {e}")
    try:
        for _ in range(3): winsound.Beep(500, 1000)
    except: pass

def enviar_relatorio_final(estatisticas):
    if TOPICO_NTFY:
        try:
            log("📊 Gerando relatório final...")
            msg = f"Resumo da Madrugada:\n"
            msg += f"Total Encontradas: {estatisticas['total_encontradas']}\n"
            msg += f"Total com Match: {estatisticas['total_marcadas']}\n\n"
            
            if estatisticas['historico']:
                msg += "Detalhes:\n"
                msg += "\n".join(estatisticas['historico'])
            else:
                msg += "Nenhuma rota marcada hoje."

            url = f"https://ntfy.sh/{TOPICO_NTFY}"
            data = msg.encode('utf-8')
            req = urllib.request.Request(url, data=data, method='POST')
            req.add_header("Title", "Relatorio Final de Rotas")
            req.add_header("Priority", "high")
            req.add_header("Tags", "clipboard")
            urllib.request.urlopen(req)
            log("✅ Relatório enviado!")
        except Exception as e:
            log(f"⚠️ Erro ao enviar relatório: {e}")    

def disparar_alarme_total():
    log("🚨 ATIVANDO PROTOCOLO DE ACORDAR! 🚨")
    if LINK_ALEXA_MONKEY:
        try:
            log("🐵 Chamando Alexa...")
            req = urllib.request.Request(LINK_ALEXA_MONKEY)
            req.add_header("User-Agent", "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36")
            
            resp = urllib.request.urlopen(req, timeout=5)
            log(f"✅ Alexa respondeu: {resp.getcode()}")
        except: pass

    if TOPICO_NTFY:
        try:
            url = f"https://ntfy.sh/{TOPICO_NTFY}"
            data = "A sexta feira conseguiu uma rota! Acorde para aceitar.".encode('utf-8')
            req = urllib.request.Request(url, data=data, method='POST')
            req.add_header("Title", "NOVA ROTA DETECTADA!")
            req.add_header("Priority", "high")
            req.add_header("Tags", "rotating_light")
            urllib.request.urlopen(req)
        except: pass

    try:
        for _ in range(5): winsound.Beep(1500, 300)
    except: pass

def clicar_botao_scroll_baixo(driver):
    try:
        seletor = 'button[aria-label="Deslizar para o fim da página"], span[data-icon="ic-chevron-down-wide"]'
        
        botoes = driver.find_elements(By.CSS_SELECTOR, seletor)
        
        for btn in botoes:
            if btn.is_displayed():
                driver.execute_script("arguments[0].click();", btn)
                log("⏬ Botão 'Deslizar para o fim' clicado com sucesso!")
                return True
    except Exception as e:
        log(f"DEBUG: Erro ao tentar rolar: {e}")
    return False

def desligar_pc_protocolo(estatisticas):
    log("👋 ROTA ACEITA! INICIANDO PROTOCOLO DE DESLIGAMENTO...")
    enviar_relatorio_final(estatisticas)

    if TOPICO_NTFY:
        try:
            url = f"https://ntfy.sh/{TOPICO_NTFY}"
            mensagem = "Desligando o PC em 30s..."
            data = mensagem.encode('utf-8')
            req = urllib.request.Request(url, data=data, method='POST')
            req.add_header("Title", "Encerrando Sistema")
            req.add_header("Tags", "zzz")
            urllib.request.urlopen(req)
        except: pass

    try:
        winsound.Beep(1000, 100)
        winsound.Beep(1500, 300)
    except: pass

    log("🔌 Enviando comando de shutdown...")
    os.system("shutdown /s /f /t 30")
    sys.exit(0)

def iniciar_driver():
    chrome_options = Options()
    caminho_perfil = os.path.join(os.getcwd(), NOME_DO_PERFIL)
    chrome_options.add_argument(f"user-data-dir={caminho_perfil}")
    chrome_options.add_argument("--disable-blink-features=AutomationControlled")
    chrome_options.add_argument("--start-maximized") 
    chrome_options.add_argument("--log-level=3")
    
    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=chrome_options)
    driver.get("https://web.whatsapp.com")
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
        
        log("🧹 Limpando busca...")
        try:
            xpath_botao_x = '//button[@aria-label="Cancelar pesquisa"]'
            btn_cancelar = WebDriverWait(driver, 5).until(
                EC.element_to_be_clickable((By.XPATH, xpath_botao_x))
            )
            btn_cancelar.click()
            notificar_inicio_ntfy()
            log("🚀 Monitoramento iniciado!")
            return True
        except:
            ActionChains(driver).send_keys(Keys.ESCAPE).perform()
            notificar_inicio_ntfy()
            return True
    except Exception as e:
        log(f"❌ Erro ao abrir grupo: {e}")
        return False

def verificar_lateral_por_analista(driver):
    try:
        xpath_aviso = f'//div[@id="pane-side"]//div[@role="row"][.//span[contains(@title, "{NOME_DO_ANALISTA}")] and .//span[contains(@aria-label, "não lida")]]'
        notificacoes = driver.find_elements(By.XPATH, xpath_aviso)
        if notificacoes: return True
    except: pass
    return False

def verificar_regras(texto):
    texto = texto.lower().strip()
    for proibida in PALAVRAS_PROIBIDAS:
        if proibida.lower().strip() in texto: return False, f"🚫 BLOQUEADO: '{proibida}'"
    for grupo in REGRAS_DE_ACEITE:
        if all(palavra.lower().strip() in texto for palavra in grupo): return True, f"✅ APROVADO: {grupo}"
    return False, "⚠️ IGNORADO"

def votar_primeira_opcao(driver, poll_element):
    max_tentativas = 3 
    for tentativa in range(max_tentativas):
        try:
            if tentativa > 0: time.sleep(1)
            driver.execute_script("arguments[0].scrollIntoView({block: 'center', inline: 'nearest'});", poll_element)
            inputs = poll_element.find_elements(By.XPATH, './/input[@type="checkbox"]')
            if not inputs: return False
            primeiro_input = inputs[0]
            if primeiro_input.get_attribute("aria-checked") == "true": return False
            driver.execute_script("arguments[0].click();", primeiro_input)
            return True
        except: return False
    return False

def analisar_enquete(msg_element):
    try:
        xpath_enquete = './/div[contains(@aria-label, "Enquete")]'
        poll_container = msg_element.find_element(By.XPATH, xpath_enquete)
        texto_completo = poll_container.text.lower()
        return True, texto_completo, poll_container
    except: return False, "", None

def executar_bot():
    driver = None
    try:
        os.system("taskkill /f /im chrome.exe >nul 2>&1") 
        driver = iniciar_driver()
        
        print("\n" + "="*50)
        print(f" ☢️ BOT VIGIA ESTÁVEL: Monitorando '{NOME_DO_ANALISTA}'")
        print("="*50 + "\n")
        
        if not abrir_conversa_inicial(driver):
            log("⚠️ FALHA AO ABRIR GRUPO. TENTANDO RODAR MESMO ASSIM...")
        
        msgs_processadas = set()
        MODO_PAUSA = False
        alarme_disparado = False 
        stats = {
            "total_encontradas": 0,
            "total_marcadas": 0,
            "historico": []
        }

        while True:
            clicar_botao_scroll_baixo(driver)
            
            # 1. VERIFICAÇÃO ANALISTA
            analista_chamando = verificar_lateral_por_analista(driver)

            if analista_chamando:
                if not MODO_PAUSA:
                    log(f"🚨🚨🚨 O {NOME_DO_ANALISTA} CHAMOU! 🚨🚨🚨")
                    MODO_PAUSA = True
                
                if not alarme_disparado:
                    disparar_alarme_total()
                    alarme_disparado = True 
                
                try: winsound.Beep(2000, 100)
                except: pass
                time.sleep(2)
                continue
            
            if not analista_chamando and MODO_PAUSA:
                desligar_pc_protocolo(stats)

            # 2. VOTAÇÃO (LÓGICA CLÁSSICA: CHECA ANTES DE CLICAR)
            msgs = driver.find_elements(By.XPATH, '//div[contains(@class, "message-out") or contains(@class, "message-in")]')
            for msg in reversed(msgs[-5:]):
                try:
                    try:
                        parent = msg.find_element(By.XPATH, "./ancestor::div[@data-id]")
                        msg_id = parent.get_attribute("data-id")
                    except: continue
                    
                    if not msg_id or msg_id in msgs_processadas: continue

                    eh_enquete, texto, element = analisar_enquete(msg)
                    if eh_enquete:
                        stats["total_encontradas"] += 1
                        hora_encontrada = datetime.datetime.now().strftime("%H:%M:%S")
                        
                        titulo = texto.split('\n')[0][:50]
                        log(f"📊 ENQUETE: '{titulo}...'")
                        
                        deu_match, motivo = verificar_regras(texto)
                        log(f"   Status: {motivo}")
                        
                        if deu_match:
                            if votar_primeira_opcao(driver, element):
                                log("✅ VOTO CONCLUÍDO!")
                                stats["total_marcadas"] += 1
                                hora_marcada = datetime.datetime.now().strftime("%H:%M:%S")
                                linha_relatorio = f"🔹 {titulo} - Rec: {hora_encontrada} / Marc: {hora_marcada}"
                                stats["historico"].append(linha_relatorio)
                                
                    msgs_processadas.add(msg_id)
                except: continue
            time.sleep(0.2)

    except SystemExit:
        raise
    except Exception as e:
        raise e 
    finally:
        if driver:
            try: driver.quit()
            except: pass

def supervisor():
    tentativas = 0
    while True:
        try:
            executar_bot()
        except (KeyboardInterrupt, SystemExit):
            log("🛑 Bot encerrado (Shutdown ou Usuário).")
            break
        except Exception as e:
            tentativas += 1
            log(f"❌ CRASH DETECTADO (Tentativa {tentativas}): {e}")
            notificar_erro_critico(e)
            log("⏳ Reiniciando em 15 segundos...")
            time.sleep(15)

if __name__ == "__main__":
    supervisor()