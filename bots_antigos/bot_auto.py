import time
import os
import datetime
import winsound
import urllib.request
import urllib.parse 
import sys
import glob
import pypdf
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys 
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import StaleElementReferenceException, NoSuchElementException
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

# --- CONFIGURAÇÕES DE USUÁRIO ---
NOME_COMPLETO_NA_ESCALA = "SAMUEL VITOR GOMES DE CARVALHO"
PASTA_DOWNLOADS = r"C:\Users\Meu_PC\Downloads"
TERMO_BUSCA_ARQUIVO = "Escala"
HORARIO_LIMITE_ESCALA = "03:30"

# --- CONFIGURAÇÕES DE ROTA (Fase 2) ---
REGRAS_DE_ACEITE = [
    ["Betim"], ["Sarzedo"],
    ["Brumadinho Central"],
    ["Niterói"], ["Niteroi"], ["Santo Afonso"], ["Petrovale"],
    ["PTB"], ["Cruzeiro"], ["Dom Bosco"], ["Vianópolis"], ["Vianopolis"],
]

PALAVRAS_PROIBIDAS = [
    "fiorino", "teresópolis", "teresopolis", "citrolândia", "citrolandia",
]

NOME_DO_ANALISTA = "Analista"
NOME_DO_GRUPO = "Drivers Betim" 
NOME_DO_PERFIL = "zap_profile" 
TOPICO_NTFY = os.getenv("TOPICO_NTFY", "")
LINK_ALEXA_MONKEY = os.getenv("LINK_ALEXA_MONKEY", "")

def log(mensagem):
    hora = datetime.datetime.now().strftime("%H:%M:%S") 
    print(f"[{hora}] {mensagem}")

# --- FUNÇÕES DE PDF E ESCALA ---

def limpar_downloads_antigos():
    """Remove PDFs antigos de escala da pasta download para não confundir"""
    try:
        padrao = os.path.join(PASTA_DOWNLOADS, f"*{TERMO_BUSCA_ARQUIVO}*.pdf")
        arquivos = glob.glob(padrao)
        for arq in arquivos:
            try: os.remove(arq)
            except: pass
    except: pass

def esperar_download_concluir(timeout=60):
    """Espera o arquivo .pdf aparecer na pasta de downloads"""
    fim = time.time() + timeout
    while time.time() < fim:
        padrao = os.path.join(PASTA_DOWNLOADS, f"*{TERMO_BUSCA_ARQUIVO}*.pdf")
        arquivos = glob.glob(padrao)

        if arquivos:
            arquivo_recente = max(arquivos, key=os.path.getctime)

            if not arquivo_recente.endswith('.crdownload'):
                return arquivo_recente
        time.sleep(1)
    return None

def ler_pdf_procurar_nome(caminho_pdf):
    """Abre o PDF e procura o nome do usuário"""
    log(f"📖 Lendo PDF: {os.path.basename(caminho_pdf)}...")
    try:
        leitor = pypdf.PdfReader(caminho_pdf)
        texto_completo = ""
        for pagina in leitor.pages:
            texto_completo += pagina.extract_text() + "\n"
        
        if NOME_COMPLETO_NA_ESCALA.upper() in texto_completo.upper():
            return True
        return False
    except Exception as e:
        log(f"❌ Erro ao ler PDF: {e}")
        return False
    
def verificar_horario_limite():
    """Retorna True se já passou do horário limite (03:30)"""
    agora = datetime.datetime.now()
    hora_limite = int(HORARIO_LIMITE_ESCALA.split(":")[0])
    minuto_limite = int(HORARIO_LIMITE_ESCALA.split(":")[1])
    
    limite_hoje = agora.replace(hour=hora_limite, minute=minuto_limite, second=0, microsecond=0)
    
    if agora > limite_hoje:
        return True
    return False

def fase_monitorar_escala(driver):
    log(f"⏳ FASE 1: Aguardando Escala até {HORARIO_LIMITE_ESCALA}...")
    limpar_downloads_antigos()
    msgs_pdf_processadas = set()

    while True:
        if verificar_horario_limite():
            log(f"⏰ Horário limite atingido! Escala não chegou.")
            return "TIMEOUT"

        try:
            # ESTRATÉGIA DE BUSCA AGRESSIVA (3 TENTATIVAS)
            
            # 1. Busca pelo atributo TITLE (Botão de download explícito) - Igual ao seu print
            # Procura div que tenha "Baixar"
            xpath_title = f'//div[contains(@title, "Baixar")]'
            
            # 2. Busca pelo texto visual (Caso não tenha botão)
            xpath_texto = f'//span[contains(translate(text(), "ABCDEFGHIJKLMNOPQRSTUVWXYZ", "abcdefghijklmnopqrstuvwxyz"), "{TERMO_BUSCA_ARQUIVO.lower()}")]'
            
            candidatos = driver.find_elements(By.XPATH, xpath_title) + driver.find_elements(By.XPATH, xpath_texto)
            
            if not candidatos:
                time.sleep(2)
                continue

            alvo = candidatos[-1]
            
            if alvo.id in msgs_pdf_processadas:
                time.sleep(2)
                continue
            
            log(f"📄 PDF Detectado! Elemento: {alvo.tag_name}")
            
            # Tenta clicar de todas as formas possíveis
            baixou = False
            try:
                # Clique JS direto no elemento
                driver.execute_script("arguments[0].click();", alvo)
                baixou = True
            except:
                try:
                    # Clique no pai (caso o alvo seja apenas o texto interno)
                    pai = alvo.find_element(By.XPATH, "./..")
                    driver.execute_script("arguments[0].click();", pai)
                    baixou = True
                except:
                    log("❌ Falha ao clicar no PDF.")

            if baixou:
                # Espera o arquivo aparecer na pasta
                time.sleep(2) # Dá um respiro pro download começar
                caminho_arquivo = esperar_download_concluir()
                
                if caminho_arquivo:
                    log(f"✅ Arquivo baixado: {os.path.basename(caminho_arquivo)}")
                    nome_encontrado = ler_pdf_procurar_nome(caminho_arquivo)
                    
                    if nome_encontrado:
                        log(f"🎉 NA ESCALA: {NOME_COMPLETO_NA_ESCALA}")
                        return "ESCALADO"
                    else:
                        log(f"⚠️ FORA DA ESCALA. Iniciando Enquetes...")
                        return "NAO_ESCALADO"
            
            msgs_pdf_processadas.add(alvo.id)
            
        except Exception as e:
            log(f"DEBUG: Erro no loop: {e}")
            pass
        
        time.sleep(2)

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

# --- FUNÇÕES DE SISTEMA (NOTIFICAÇÃO/ALARME) ---

def notificar_ntfy(titulo, mensagem, tags, prioridade="default"):
    if TOPICO_NTFY:
        try:
            url = f"https://ntfy.sh/{TOPICO_NTFY}"
            data = mensagem.encode('utf-8')
            req = urllib.request.Request(url, data=data, method='POST')
            req.add_header("User-Agent", "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/91.0.4472.124 Safari/537.36")
            req.add_header("Title", titulo)
            req.add_header("Priority", prioridade)
            req.add_header("Tags", tags)
            urllib.request.urlopen(req)
        except Exception as e:
            log(f"⚠️ Erro NTFY: {e}")

def disparar_alarme_total(motivo="ALERTA"):
    log(f"🚨 ATIVANDO PROTOCOLO DE ACORDAR! Motivo: {motivo} 🚨")
    
    # 1. Alexa com Máscara
    if LINK_ALEXA_MONKEY:
        try:
            log("🐵 Chamando Alexa...")
            req = urllib.request.Request(LINK_ALEXA_MONKEY)
            req.add_header("User-Agent", "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/91.0.4472.124 Safari/537.36")
            urllib.request.urlopen(req, timeout=5)
        except Exception as e:
            log(f"⚠️ FALHA ALEXA: {e}")

    # 2. Celular
    notificar_ntfy("ACORDA AGORA!", f"{motivo} Detectado! Vá ao PC.", "rotating_light", "high")

    # 3. PC
    try:
        for _ in range(5): winsound.Beep(1500, 300)
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

            notificar_ntfy("Relatorio Final", msg, "clipboard", "high")
            log("✅ Relatório enviado!")
        except Exception as e:
            log(f"⚠️ Erro relatório: {e}") 

def desligar_pc_protocolo(mensagem_final):
    log("👋 ENCERRANDO OPERAÇÃO...")
    
    notificar_ntfy("Desligando PC", f"{mensagem_final}. Desligando em 30s...", "zzz")
    
    try:
        winsound.Beep(1000, 100)
        winsound.Beep(1500, 300)
    except: pass
    
    log("🔌 Shutdown em 30s...")
    os.system("shutdown /s /f /t 30")
    sys.exit(0)

# --- FUNÇÕES DE ENQUETE (Fase 2) ---

def iniciar_driver():
    chrome_options = Options()
    caminho_perfil = os.path.join(os.getcwd(), NOME_DO_PERFIL)
    chrome_options.add_argument(f"user-data-dir={caminho_perfil}")
    chrome_options.add_argument("--disable-blink-features=AutomationControlled")
    chrome_options.add_argument("--start-maximized") 
    chrome_options.add_argument("--log-level=3")
    chrome_options.add_argument("--silent")
    chrome_options.add_argument("--start-maximized")
    
    # Configura pasta de download automática
    prefs = {
        "download.default_directory": PASTA_DOWNLOADS,
        "download.prompt_for_download": False,
        "download.directory_upgrade": True,
        "plugins.always_open_pdf_externally": True 
    }
    chrome_options.add_experimental_option("prefs", prefs)
    
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
        time.sleep(1.5) 
        
        xpath_resultado = f'//span[contains(@title, "{NOME_DO_GRUPO}")]'
        grupo_alvo = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.XPATH, xpath_resultado))
        )
        grupo_alvo.click()
        ActionChains(driver).send_keys(Keys.ENTER).perform()
        
        WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.ID, "main")))
        
        try:
            xpath_botao_x = '//button[@aria-label="Cancelar pesquisa"]'
            driver.find_element(By.XPATH, xpath_botao_x).click()
        except:
            ActionChains(driver).send_keys(Keys.ESCAPE).perform()
            
        log("✅ Grupo aberto! Iniciando vigilância.")
        return True
    except Exception as e:
        log(f"❌ Erro ao abrir grupo: {e}")
        return False

def verificar_lateral_por_analista(driver):
    try:
        xpath_aviso = f'//div[@id="pane-side"]//div[@role="row"][.//span[contains(@title, "{NOME_DO_ANALISTA}")] and .//span[contains(@aria-label, "não lida")]]'
        return bool(driver.find_elements(By.XPATH, xpath_aviso))
    except: return False

def verificar_regras(texto):
    texto = texto.lower().strip()
    for p in PALAVRAS_PROIBIDAS:
        if p.lower().strip() in texto: return False, f"🚫 BLOQUEADO: '{p}'"
    for g in REGRAS_DE_ACEITE:
        if all(p.lower().strip() in texto for p in g): return True, f"✅ APROVADO: {g}"
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

# --- LOOP PRINCIPAL ---

def executar_bot():
    try:
        os.system("taskkill /f /im chrome.exe >nul 2>&1") 
        driver = iniciar_driver()
        
        print("\n" + "="*50)
        print(f" 📜 BOT ESCALA + VIGIA: Iniciando...")
        print("="*50 + "\n")
        
        if not abrir_conversa_inicial(driver):
            log("⚠️ Falha ao abrir grupo. Tentando continuar...")

        notificar_ntfy("Bot Iniciado", "Aguardando Escala...", "eyes", "high")

        # FASE 1: MONITORAR ESCALA
        res = fase_monitorar_escala(driver)
        
        if res == "ESCALADO":
            disparar_alarme_total("VOCE ESTA NA ESCALA!")
            time.sleep(10)
            desligar_pc_protocolo("Nome na escala")
        elif res == "NAO_ESCALADO":
            log("❌ Nome não encontrado na escala.")
            notificar_ntfy("Nao Escalado", "Nome fora da lista. Monitorando Enquetes!", "muscle", "high")
        elif res == "TIMEOUT":
            log(f"⏰ Deu {HORARIO_LIMITE_ESCALA} e a escala não apareceu.")
            notificar_ntfy("Tempo Esgotado", "Escala não chegou. Iniciando enquetes às cegas!", "hourglass", "high")
        
        # FASE 2: MONITORAR ENQUETES
        log("➡️ MODO GUERRA ATIVADO: Monitorando Enquetes...")
        msgs_processadas = set()
        MODO_PAUSA = False
        alarme_disparado = False 
        stats = {"total_encontradas": 0, "total_marcadas": 0, "historico": []}

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
            
            if not analista_chamando and MODO_PAUSA:
                enviar_relatorio_final(stats)
                desligar_pc_protocolo("Mensagem do analista lida")

            # B. Votação
            xpath_msgs_recentes = '(//div[contains(@class, "message-in")])[last()]'
            try:
                msg = driver.find_element(By.XPATH, xpath_msgs_recentes)
                
                if msg.id in msgs_processadas:
                    time.sleep(0.05) 
                    continue

                votou, motivo, titulo = analisar_e_votar_rapido(driver, msg)
                
                if votou:
                    log(f"✅ VOTO REALIZADO: {titulo}")
                    stats["total_marcadas"] += 1
                    stats["historico"].append(f"{titulo} - {datetime.datetime.now().strftime('%H:%M:%S')}")
                    time.sleep(0.5)
                elif "BLOQUEADO" in motivo:
                    log(f"{motivo} - {datetime.datetime.now().strftime('%H:%M:%S')}")
                
                msgs_processadas.add(msg.id)
                stats["total_encontradas"] += 1

            except NoSuchElementException:
                pass
            except StaleElementReferenceException:
                pass
            except Exception as e:
                log(f"Erro no loop: {e}")
                pass

    except SystemExit: raise
    except Exception as e: raise e 
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
            break
        except Exception as e:
            tentativas += 1
            log(f"❌ CRASH DETECTADO (Tentativa {tentativas}): {e}")
            notificar_ntfy("CRASH NO BOT", f"Reiniciando... Erro: {str(e)[:50]}", "skull")
            
            os.system("taskkill /f /im chrome.exe >nul 2>&1")
            os.system("taskkill /f /im chromedriver.exe >nul 2>&1")
            
            log("⏳ Reiniciando em 5 segundos...")
            time.sleep(5)

if __name__ == "__main__":
    supervisor()