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
import psutil

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

def definir_prioridade_alta():
    try:
        pid = os.getpid()
        py_process = psutil.Process(pid)
        py_process.nice(psutil.HIGH_PRIORITY_CLASS)
        log("🚀 Prioridade de CPU definida para ALTA!")
    except Exception as e:
        log(f"⚠️ Não foi possível definir prioridade alta: {e}")    

# --- FUNÇÕES DE SISTEMA ---

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
        except: pass

def disparar_alarme_total(motivo="ALERTA"):
    log(f"🚨 ATIVANDO PROTOCOLO DE ACORDAR! Motivo: {motivo} 🚨")
    if LINK_ALEXA_MONKEY:
        try:
            req = urllib.request.Request(LINK_ALEXA_MONKEY)
            req.add_header("User-Agent", "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/91.0.4472.124 Safari/537.36")
            urllib.request.urlopen(req, timeout=5)
        except Exception as e: log(f"⚠️ FALHA ALEXA: {e}")

    notificar_ntfy("ACORDA AGORA!", f"{motivo} Detectado!", "rotating_light", "high")
    try:
        for _ in range(5): winsound.Beep(1500, 300)
    except: pass

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

def enviar_relatorio_final(estatisticas):
    if TOPICO_NTFY:
        try:
            log("📊 Gerando relatório final...")
            msg = f"Resumo da Madrugada:\n"
            msg += f"Total Encontradas: {estatisticas.get('total', 0)}\n"
            msg += f"Total com Match: {estatisticas.get('match', 0)}\n\n"
            
            if estatisticas.get('historico'):
                msg += "Detalhes:\n"
                msg += "\n".join(estatisticas['historico'])
            else:
                msg += "Nenhuma rota marcada hoje."

            notificar_ntfy("Relatorio Final", msg, "clipboard",)
            log("✅ Relatório enviado!")
        except Exception as e:
            log(f"⚠️ Erro relatório: {e}") 

# --- FUNÇÕES DE PDF E ESCALA ---

def limpar_downloads_antigos():
    try:
        padrao = os.path.join(PASTA_DOWNLOADS, f"*{TERMO_BUSCA_ARQUIVO}*.pdf")
        for arq in glob.glob(padrao):
            try: os.remove(arq)
            except: pass
    except: pass

def esperar_download_concluir(timeout=60):
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
    log(f"📖 Lendo PDF: {os.path.basename(caminho_pdf)}...")
    try:
        leitor = pypdf.PdfReader(caminho_pdf)
        texto_completo = ""
        for pagina in leitor.pages:
            texto_completo += pagina.extract_text() + "\n"
        return NOME_COMPLETO_NA_ESCALA.upper() in texto_completo.upper()
    except Exception as e:
        log(f"❌ Erro ao ler PDF: {e}")
        return False

def verificar_horario_limite():
    agora = datetime.datetime.now()
    h, m = map(int, HORARIO_LIMITE_ESCALA.split(":"))
    return agora > agora.replace(hour=h, minute=m, second=0, microsecond=0)

def fase_monitorar_escala(driver):
    log(f"⏳ FASE 1: Aguardando Escala até {HORARIO_LIMITE_ESCALA}...")
    limpar_downloads_antigos()
    msgs_pdf_processadas = set()

    while True:
        if verificar_horario_limite():
            log(f"⏰ Horário limite atingido! Escala não chegou.")
            return "TIMEOUT"

        try:
            # Busca Otimizada: Procura apenas nas últimas mensagens visíveis
            xpath_title = f'//div[contains(@title, "Baixar")]'
            xpath_texto = f'//span[contains(translate(text(), "ABCDEFGHIJKLMNOPQRSTUVWXYZ", "abcdefghijklmnopqrstuvwxyz"), "{TERMO_BUSCA_ARQUIVO.lower()}")]'
            
            candidatos = driver.find_elements(By.XPATH, xpath_title) + driver.find_elements(By.XPATH, xpath_texto)
            
            if candidatos:
                alvo = candidatos[-1]
                if alvo.id not in msgs_pdf_processadas:
                    log(f"📄 PDF Detectado! Baixando...")
                    try:
                        driver.execute_script("arguments[0].click();", alvo)
                    except:
                        try: driver.execute_script("arguments[0].click();", alvo.find_element(By.XPATH, "./.."))
                        except: pass
                    
                    # Pausa curta para garantir início do download
                    time.sleep(2)
                    caminho = esperar_download_concluir()
                    if caminho:
                        log("✅ Download concluído.")
                        if ler_pdf_procurar_nome(caminho):
                            return "ESCALADO"
                        else:
                            return "NAO_ESCALADO"
                    
                    msgs_pdf_processadas.add(alvo.id)
        except: pass
        time.sleep(1.5) # Delay maior na fase de escala, pois não precisa ser instantâneo

# --- FUNÇÕES DE ENQUETE (OTIMIZADAS) ---

def iniciar_driver():
    chrome_options = Options()
    caminho_perfil = os.path.join(os.getcwd(), NOME_DO_PERFIL)
    chrome_options.add_argument(f"user-data-dir={caminho_perfil}")
    chrome_options.add_argument("--disable-blink-features=AutomationControlled")
    chrome_options.add_argument("--log-level=3") 
    chrome_options.add_argument("--silent")
    chrome_options.add_argument("--start-maximized")
    
    prefs = {
        "download.default_directory": PASTA_DOWNLOADS,
        "download.prompt_for_download": False,
        "download.directory_upgrade": True,
        "plugins.always_open_pdf_externally": True 
    }
    chrome_options.add_experimental_option("prefs", prefs)
    
    log("🌐 Iniciando ChromeDriver...")
    try:
        service = Service(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=chrome_options)
        driver.set_page_load_timeout(120)  # Timeout de 2 minutos para carregar página
        log("✅ ChromeDriver iniciado!")
    except Exception as e:
        log(f"❌ Erro ao iniciar ChromeDriver: {e}")
        raise
    
    log("📱 Abrindo WhatsApp Web...")
    driver.get("https://web.whatsapp.com")
    driver.implicitly_wait(0)
    
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

def verificar_regras(texto):
    texto = texto.lower().strip()
    # Verifica proibições primeiro (mais rápido)
    for p in PALAVRAS_PROIBIDAS:
        if p.lower() in texto: return False, f"🚫 BLOQUEADO: '{p}'"
    # Verifica aceites
    for g in REGRAS_DE_ACEITE:
        if all(p.lower() in texto for p in g): return True, f"✅ APROVADO: {g}"
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
    
def verificar_lateral_por_analista(driver):
    try:
        # 1. Pega APENAS as conversas (linhas) que têm a bolinha verde de "não lida"
        xpath_nao_lidas = '//div[@id="pane-side"]//div[@role="row"][.//span[contains(@aria-label, "não lida")]]'
        conversas_nao_lidas = driver.find_elements(By.XPATH, xpath_nao_lidas)
        
        for conversa in conversas_nao_lidas:
            # 2. Puxa todo o texto visível daquela conversa e quebra em linhas
            texto_visivel = conversa.text.split('\n')
            
            if len(texto_visivel) > 0:
                # 3. A linha [0] é SEMPRE o Nome do Título da Conversa (Contato ou Grupo)
                nome_da_conversa = texto_visivel[0].strip()
                
                # 4. Verifica se a palavra Analista está NO NOME DA CONVERSA
                if NOME_DO_ANALISTA.lower() in nome_da_conversa.lower():
                    return True
                    
        return False
    except: 
        return False

def clicar_botao_scroll_baixo(driver):
    try:
        btn = driver.find_element(By.CSS_SELECTOR, 'button[aria-label="Deslizar para o fim da página"]')
        driver.execute_script("arguments[0].click();", btn)
    except: pass

# --- LOOP PRINCIPAL ---
def executar_bot():
    try:
        driver = iniciar_driver()
        print("\n" + "="*50); print(f" 📜 BOT V8 BITURBO INICIADO"); print("="*50 + "\n")
        
        if not abrir_conversa_inicial(driver): log("⚠️ Falha ao abrir grupo.")
        notificar_ntfy("Sexta Feira Iniciada", "Aguardando Escala...", "eyes", "high")

        # FASE 1: MONITORAR ESCALA
        res = fase_monitorar_escala(driver)
        if res == "ESCALADO":
            disparar_alarme_total("VOCE ESTA NA ESCALA!")
            time.sleep(10)
            desligar_pc_protocolo("Nome na escala")
        elif res == "NAO_ESCALADO":
            log("❌ Nome não encontrado.")
            notificar_ntfy("Nao Escalado", "Monitorando Enquetes!", "muscle", "high")
        elif res == "TIMEOUT":
            log("⏰ Tempo esgotado.")
            notificar_ntfy("Sem Escala", "Tempo limite. Iniciando Enquetes.", "hourglass", "high")

        # FASE 2: MONITORAR ENQUETES (OTIMIZADA)
        log("➡️ MODO VELOCIDADE MÁXIMA ATIVADO...")
        
        # Garante que estamos lá embaixo
        clicar_botao_scroll_baixo(driver)
        
        msgs_processadas = set()
        MODO_PAUSA = False
        alarme_disparado = False 
        stats = {"total": 0, "match": 0, "historico": []}

        xpath_msgs_recentes = '(//div[contains(@class, "message-out") or contains(@class, "message-in")])[last()]'

        while True:

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

            # 2. BUSCA E VOTAÇÃO ULTRA RÁPIDA
            try:
                # Pega a ÚLTIMA mensagem recebida instantaneamente
                msg = driver.find_element(By.XPATH, xpath_msgs_recentes)
                
                if msg.id in msgs_processadas:
                    time.sleep(0.05) 
                    continue

                votou, motivo, titulo = analisar_e_votar_rapido(driver, msg)
                
                if votou:
                    log(f"✅ VOTO REALIZADO: {titulo}")
                    stats["match"] += 1
                    stats["historico"].append(f"{titulo} - {datetime.datetime.now().strftime('%H:%M:%S')}")
                    # Dá um tempo para o clique ser registrado pelo servidor do Whats
                    time.sleep(0.5)
                elif "BLOQUEADO" in motivo:
                    log(f"{motivo} - {datetime.datetime.now().strftime('%H:%M:%S')}")
                
                # Marca como processada para não ler de novo no próximo loop
                msgs_processadas.add(msg.id)
                stats["total"] += 1

            except NoSuchElementException:
                pass # Nenhuma mensagem encontrada (chat vazio?)
            except StaleElementReferenceException:
                pass # O DOM atualizou enquanto líamos, tenta de novo na próxima volta
            except Exception as e:
                log(f"Erro no loop: {e}")
                pass

    except KeyboardInterrupt: log("🛑 Bot parado.")
    except Exception as e:
        log(f"❌ CRASH GERAL: {e}")
        notificar_ntfy("CRASH", f"Erro: {str(e)[:50]}", "skull", "high")
        time.sleep(15)
    finally:
        if driver: 
            try: 
                driver.quit(); 
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