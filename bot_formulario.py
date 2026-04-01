import sys
import time
import os
import re
import datetime
import urllib.request
import winsound
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
            with open(caminho, "r", encoding="utf-8") as f:
                for linha in f:
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

# ==============================================================
# ⚙️  CONFIGURAÇÕES
# ==============================================================

NOME_DO_GRUPO  = "PM MOTORISTAS"
NOME_DO_PERFIL = "zap_profile"
NOME_DO_ANALISTA = "Analista"
TOPICO_NTFY    = os.getenv("TOPICO_NTFY", "")
LINK_ALEXA_MONKEY = os.getenv("LINK_ALEXA_MONKEY", "")

# --- Dados fixos do Formulario ---
DRIVER_ID    = os.getenv("DRIVER_ID", "")
PHONE_NUMBER = os.getenv("PHONE_NUMBER", "")

CLUSTERS_ACEITOS = [
    "Sede",
    "Niteroi",
    "Niterói",
    "Nazareno",
    "PTB",
    "Senhora das Graças",
    "Santo Afonso",
    "São Caetano",
    "Sao Caetano",
]

REGEX_FORMS = re.compile(r'https://docs\.google\.com/forms/[^\s]+', re.IGNORECASE)

# ==============================================================

def log(msg):
    hora = datetime.datetime.now().strftime("%H:%M:%S")
    print(f"[{hora}] {msg}")

def notificar_ntfy(titulo, mensagem, tags, prioridade="default"):
    if not TOPICO_NTFY:
        return
    try:
        url = f"https://ntfy.sh/{TOPICO_NTFY}"
        req = urllib.request.Request(url, data=mensagem.encode("utf-8"), method="POST")
        req.add_header("User-Agent", "Mozilla/5.0")
        req.add_header("Title", titulo)
        req.add_header("Priority", prioridade)
        req.add_header("Tags", tags)
        urllib.request.urlopen(req)
    except Exception as e:
        log(f"⚠️ Erro NTFY: {e}")

# ==============================================================
# 🌐  DRIVER SELENIUM
# ==============================================================

def iniciar_driver():
    opts = Options()
    caminho_perfil = os.path.join(os.getcwd(), NOME_DO_PERFIL)
    opts.add_argument(f"user-data-dir={caminho_perfil}")
    opts.add_argument("--disable-blink-features=AutomationControlled")
    opts.add_argument("--disable-extensions")
    opts.add_argument("--no-sandbox")
    opts.add_argument("--disable-gpu")
    opts.add_argument("--start-maximized")
    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=opts)
    return driver

# ==============================================================
# 💬  WHATSAPP
# ==============================================================

def abrir_whatsapp_grupo(driver):
    log("🌐 Abrindo WhatsApp Web...")
    driver.get("https://web.whatsapp.com")

    try:
        WebDriverWait(driver, 15).until(EC.presence_of_element_located((By.TAG_NAME, "canvas")))
        log("⚠️ Escaneie o QR Code no celular...")
    except:
        pass
    WebDriverWait(driver, 90).until(EC.presence_of_element_located((By.ID, "pane-side")))
    log("✅ WhatsApp carregado!")

    log(f"🔍 Abrindo grupo '{NOME_DO_GRUPO}'...")
    xpath_busca = (
        "//input[@placeholder='Pesquisar ou começar uma nova conversa'] | "
        "//div[@id='side']//input[@type='text'] | "
        "//input[@data-tab='3'] | "
        "//div[@id='side']//div[@contenteditable='true']"
    )
    caixa = WebDriverWait(driver, 30).until(EC.element_to_be_clickable((By.XPATH, xpath_busca)))
    caixa.click()
    caixa.send_keys(NOME_DO_GRUPO)
    time.sleep(2)

    grupo = WebDriverWait(driver, 10).until(
        EC.presence_of_element_located((By.XPATH, f'//span[contains(@title, "{NOME_DO_GRUPO}")]'))
    )
    grupo.click()
    ActionChains(driver).send_keys(Keys.ENTER).perform()
    WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.ID, "main")))

    try:
        xpath_x = (
            '//button[@aria-label="End icon button"] | '
            '//button[@aria-label="Cancelar pesquisa"] | '
            '//span[@data-icon="x-alt"]/ancestor::button'
        )
        WebDriverWait(driver, 5).until(EC.element_to_be_clickable((By.XPATH, xpath_x))).click()
    except:
        ActionChains(driver).send_keys(Keys.ESCAPE).perform()

    log("✅ Grupo aberto! Monitorando mensagens...")

def extrair_link_forms(texto):
    match = REGEX_FORMS.search(texto)
    return match.group(0) if match else None

def obter_mensagens_recentes(driver, quantidade=10):
    msgs = driver.find_elements(
        By.XPATH,
        '//div[contains(@class, "message-out") or contains(@class, "message-in")]'
    )
    resultado = []
    for msg in msgs[-quantidade:]:
        try:
            parent = msg.find_element(By.XPATH, "./ancestor::div[@data-id]")
            msg_id = parent.get_attribute("data-id")
            try:
                texto = msg.find_element(By.CSS_SELECTOR, ".copyable-text").text
            except:
                texto = msg.text
            if msg_id and texto:
                resultado.append((msg_id, texto))
        except:
            continue
    return resultado

def verificar_lateral_por_analista(driver):
    try:
        xpath_linhas_com_msg = '//div[@id="pane-side"]//div[@role="row"][.//span[contains(translate(@aria-label, "NÃO LIDA", "não lida"), "não lida") or contains(translate(@aria-label, "UNREAD", "unread"), "unread")]]'
        
        linhas_nao_lidas = driver.find_elements(By.XPATH, xpath_linhas_com_msg)
        
        for linha in linhas_nao_lidas:
            try:
                xpath_titulo = './/span[@title and @dir="auto"]'
                elementos_titulo = linha.find_elements(By.XPATH, xpath_titulo)
                
                if elementos_titulo:
                    nome_da_conversa = elementos_titulo[0].get_attribute('title')
                    
                    if NOME_DO_ANALISTA.lower() in nome_da_conversa.lower():
                        return True
            except Exception as e:
                continue
                
        return False
    except Exception as e:
        log(f"⚠️ [DEBUG] Erro geral no radar da barra lateral: {e}")
        return False

def disparar_alarme_total(motivo="ALERTA"):
    log(f"🚨 ATIVANDO ALARME! Motivo: {motivo} 🚨")

    if LINK_ALEXA_MONKEY:
        try:
            log("🐵 Enviando sinal para Alexa...")
            req = urllib.request.Request(LINK_ALEXA_MONKEY)
            req.add_header("User-Agent", "Mozilla/5.0")
            resp = urllib.request.urlopen(req, timeout=5)
            log(f"✅ Alexa respondeu: {resp.getcode()}")
        except Exception as e:
            log(f"⚠️ FALHA NA ALEXA (Erro {e}). Verifique token ou URL.")

    notificar_ntfy("ANALISTA CHAMANDO!", "Mensagem do analista detectada apos envio do formulario.", "rotating_light", "high")

    try:
        for _ in range(5):
            winsound.Beep(1500, 300)
    except Exception:
        pass

def desligar_pc_protocolo(mensagem="MENSAGEM DO ANALISTA LIDA"):
    log(f"👋 Protocolo de encerramento iniciado: {mensagem}")
    notificar_ntfy("Desligando PC", f"{mensagem}. Desligando em 30s...", "zzz", "high")
    try:
        winsound.Beep(1000, 120)
        winsound.Beep(1500, 320)
    except Exception:
        pass
    log("🔌 Encerrando bot e agendando desligamento do Windows...")
    os.system("shutdown /s /f /t 30")
    sys.exit(0)

# ==============================================================
# 📋  GOOGLE FORMS
# ==============================================================

def preencher_formulario(driver_principal, link_forms):
    log(f"📋 Abrindo Formulario: {link_forms}")

    driver_principal.execute_script(f"window.open('{link_forms}', '_blank');")
    time.sleep(0.7)
    driver_principal.switch_to.window(driver_principal.window_handles[-1])

    enviado_com_sucesso = False

    try:
        WebDriverWait(driver_principal, 20).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, 'div[role="listitem"]'))
        )
        log("✅ Formulario carregado!")

        listitems = driver_principal.find_elements(By.CSS_SELECTOR, 'div[role="listitem"]')
        blocos_pergunta = filtrar_blocos_pergunta(listitems)
        log(f"🔢 Total de listitems encontrados: {len(listitems)}")
        log(f"🧩 Total de blocos de pergunta: {len(blocos_pergunta)}")

        # 🔹 CAMPO 1 — Driver ID
        preencher_campo_texto(driver_principal, blocos_pergunta, indice=0, valor=DRIVER_ID)

        # 🔹 CAMPO 2 — Telefone
        preencher_campo_texto(driver_principal, blocos_pergunta, indice=1, valor=PHONE_NUMBER)

        # 🔹 CAMPO 3 — Disponibilidade
        preencher_campo_radio(driver_principal, blocos_pergunta, indice=2, opcao="Sim")

        # 🔹 CAMPO 4 — Clusters (checkboxes)
        preencher_campo_checkboxes(driver_principal, blocos_pergunta, indice=3, aceitos=CLUSTERS_ACEITOS)

        # 🔹 CAMPO 5 — Tempo de Chegada
        preencher_campo_radio(driver_principal, blocos_pergunta, indice=4, opcao="15 a 30 min")

        # 🔹 CAMPO 6 — Perfil do Veículo
        preencher_campo_radio(driver_principal, blocos_pergunta, indice=5, opcao="Hatch")

        # 🔹 CAMPO 7 — Modelo do Veículo
        preencher_campo_texto(driver_principal, blocos_pergunta, indice=6, valor="Palio")

        enviado_com_sucesso = enviar_formulario(driver_principal)

    except Exception as e:
        log(f"❌ Erro ao preencher Formulario: {e}")
        notificar_ntfy("Erro no Formulario", str(e), "x", "high")
    finally:
        try:
            driver_principal.close()
            driver_principal.switch_to.window(driver_principal.window_handles[0])
            log("🔙 Voltei para o WhatsApp.")
        except Exception as e:
            log(f"⚠️ Falha ao voltar para aba do WhatsApp: {e}")

    return enviado_com_sucesso

# ==============================================================
# 🛠️  HELPERS DE PREENCHIMENTO
# ==============================================================

def filtrar_blocos_pergunta(listitems):
    """
    Remove listitems que são apenas opções internas (ex.: cada checkbox)
    e mantém apenas blocos que representam uma pergunta completa.
    """
    blocos = []
    for item in listitems:
        radios = item.find_elements(By.CSS_SELECTOR, '[role="radio"]')
        checkboxes = item.find_elements(By.CSS_SELECTOR, '[role="checkbox"]')
        campos_texto = item.find_elements(By.CSS_SELECTOR, 'input[type="text"], textarea, div[contenteditable="true"]')

        # Opção isolada de checkbox costuma ter 1 checkbox e nenhum outro controle.
        if len(checkboxes) == 1 and not radios and not campos_texto:
            continue

        if radios or checkboxes or campos_texto:
            blocos.append(item)

    return blocos

def preencher_campo_texto(driver, listitems, indice, valor):
    """
    Preenche campo de texto (input ou textarea).
    Tenta dois seletores: o input direto e o div contenteditable
    que o Google Forms às vezes usa em campos de resposta longa.
    Em caso de falha, imprime diagnóstico do listitem.
    """
    try:
        item = listitems[indice]
        driver.execute_script("arguments[0].scrollIntoView({block:'center'});", item)
        time.sleep(0.2)

        # Estratégia 1: input[type=text] ou textarea (campos curtos/longos normais)
        try:
            campo = item.find_element(By.CSS_SELECTOR, 'input[type="text"], textarea')
            driver.execute_script("arguments[0].scrollIntoView({block:'center'});", campo)
            campo.click()
            campo.clear()
            campo.send_keys(valor)
            log(f"✏️  Campo {indice + 1} preenchido com: '{valor}'")
            return
        except:
            pass

        # Estratégia 2: div contenteditable (campo de texto rico do Forms)
        try:
            campo = item.find_element(By.CSS_SELECTOR, 'div[contenteditable="true"]')
            driver.execute_script("arguments[0].scrollIntoView({block:'center'});", campo)
            campo.click()
            campo.clear()
            campo.send_keys(valor)
            log(f"✏️  Campo {indice + 1} (contenteditable) preenchido com: '{valor}'")
            return
        except:
            pass

        # Diagnóstico
        log(f"⚠️  Campo {indice + 1}: nenhum input/textarea encontrado.")
        _diagnosticar_listitem(driver, item, indice)

    except Exception as e:
        log(f"⚠️  Erro ao preencher campo {indice + 1}: {e}")


def preencher_campo_radio(driver, listitems, indice, opcao):
    """
    Clica no radio cuja aria-label ou texto contenha 'opcao'.
    O Google Forms atual usa aria-label no role='radio', NÃO texto
    direto no span — por isso a função antiga falhava.
    Estratégias em ordem:
      1. role="radio" com aria-label contendo 'opcao'
      2. span/div com texto visível contendo 'opcao' (fallback legado)
    Em caso de falha total, imprime todos os radios encontrados.
    """
    try:
        item = listitems[indice]
        driver.execute_script("arguments[0].scrollIntoView({block:'center'});", item)
        time.sleep(0.2)

        opcao_lower = opcao.lower()

        # Estratégia 1: aria-label no role="radio" (padrão atual do Forms)
        radios = item.find_elements(By.CSS_SELECTOR, '[role="radio"]')
        for rb in radios:
            label = rb.get_attribute("aria-label") or ""
            if opcao_lower in label.lower():
                driver.execute_script("arguments[0].scrollIntoView({block:'center'});", rb)
                driver.execute_script("arguments[0].click();", rb)
                log(f"🔘 Campo {indice + 1} (radio) selecionado: '{label.strip()}'")
                return

        # Estratégia 2: texto visível no span (fallback)
        spans = item.find_elements(By.XPATH, './/span | .//div[@data-value]')
        for sp in spans:
            txt = (sp.text or "").strip()
            if txt and opcao_lower in txt.lower():
                driver.execute_script("arguments[0].scrollIntoView({block:'center'});", sp)
                driver.execute_script("arguments[0].click();", sp)
                log(f"🔘 Campo {indice + 1} (radio/span) selecionado: '{txt}'")
                return

        # Diagnóstico
        log(f"⚠️  Campo {indice + 1}: opção '{opcao}' não encontrada nos radios.")
        log(f"   🔍 Opções disponíveis neste listitem:")
        if radios:
            for rb in radios:
                log(f"      aria-label='{rb.get_attribute('aria-label')}'")
        else:
            log(f"      (nenhum role='radio' encontrado — verifique o índice)")
            _diagnosticar_listitem(driver, item, indice)

    except Exception as e:
        log(f"⚠️  Erro ao selecionar radio {indice + 1}: {e}")


def preencher_campo_checkboxes(driver, listitems, indice, aceitos):
    """
    Dentro do listitem[indice], lê o aria-label de cada checkbox
    e marca apenas os que contiverem alguma palavra de 'aceitos'.
    """
    try:
        item = listitems[indice]
        driver.execute_script("arguments[0].scrollIntoView({block:'center'});", item)
        time.sleep(0.3)

        checkboxes = item.find_elements(By.CSS_SELECTOR, '[role="checkbox"]')
        log(f"☑️  Campo {indice + 1} (checkboxes): {len(checkboxes)} opções encontradas.")

        marcados  = []
        ignorados = []

        for cb in checkboxes:
            label       = cb.get_attribute("aria-label") or ""
            label_lower = label.lower()
            deve_marcar = any(p.lower() in label_lower for p in aceitos)

            if deve_marcar:
                if cb.get_attribute("aria-checked") != "true":
                    driver.execute_script("arguments[0].scrollIntoView({block:'center'});", cb)
                    driver.execute_script("arguments[0].click();", cb)
                    time.sleep(0.15)
                marcados.append(label.strip())
            else:
                ignorados.append(label.strip())

        log(f"   ✅ Marcados  : {marcados}")
        log(f"   ⏭️  Ignorados : {ignorados}")

    except Exception as e:
        log(f"⚠️  Erro ao preencher checkboxes (campo {indice + 1}): {e}")


def _diagnosticar_listitem(driver, item, indice):
    """
    Ferramenta de debug: imprime no terminal os elementos interativos
    encontrados dentro de um listitem para ajudar a mapear campos novos.
    """
    try:
        log(f"   🔬 Diagnóstico do listitem {indice + 1}:")
        for role in ["radio", "checkbox", "listbox", "combobox", "textbox"]:
            els = item.find_elements(By.CSS_SELECTOR, f'[role="{role}"]')
            if els:
                for el in els:
                    log(f"      role={role} | aria-label='{el.get_attribute('aria-label')}' | texto='{el.text[:60]}'")
        inputs = item.find_elements(By.CSS_SELECTOR, "input, textarea")
        for inp in inputs:
            log(f"      <{inp.tag_name}> type='{inp.get_attribute('type')}' | placeholder='{inp.get_attribute('placeholder')}'")
    except:
        pass


def enviar_formulario(driver):
    try:
        xpath_enviar = (
            '//div[@role="button" and .//span[contains(text(),"Enviar")]] | '
            '//div[@role="button" and .//span[contains(text(),"Submit")]]'
        )
        btn = WebDriverWait(driver, 10).until(EC.element_to_be_clickable((By.XPATH, xpath_enviar)))
        driver.execute_script("arguments[0].scrollIntoView({block:'center'});", btn)
        btn.click()
        time.sleep(2)
        log("🚀 Formulario enviado!")
        notificar_ntfy("Formulario Enviado!", "Preenchimento automático concluído.", "white_check_mark", "high")
        return True
    except Exception as e:
        log(f"❌ Erro ao enviar Formulario: {e}")
        return False

# ==============================================================
# 🔁  LOOP PRINCIPAL
# ==============================================================

def main():
    os.system("taskkill /f /im chrome.exe >nul 2>&1")
    driver = iniciar_driver()

    print("\n" + "=" * 50)
    print("  Bot de Formulario — WhatsApp Web")
    print("=" * 50 + "\n")

    abrir_whatsapp_grupo(driver)
    notificar_ntfy("Bot Formulario Iniciado", "Monitorando links de Formulario...", "eyes", "default")

    msgs_processadas = set()
    monitorar_analista = False
    alarme_disparado = False

    try:
        while True:
            if monitorar_analista:
                analista_chamando = verificar_lateral_por_analista(driver)
                if analista_chamando and not alarme_disparado:
                    disparar_alarme_total("MENSAGEM DO ANALISTA")
                    alarme_disparado = True
                elif analista_chamando:
                    time.sleep(2)
                    continue
                elif not analista_chamando and alarme_disparado:
                    desligar_pc_protocolo("Mensagem do analista foi lida")

            mensagens = obter_mensagens_recentes(driver, quantidade=10)

            for msg_id, texto in mensagens:
                if msg_id in msgs_processadas:
                    continue

                link = extrair_link_forms(texto)

                if link:
                    log(f"🔗 Link de Formulario detectado! ID: {msg_id}")
                    notificar_ntfy("Formulario Detectado", "Iniciando preenchimento...", "pencil", "high")
                    msgs_processadas.add(msg_id)
                    enviado = preencher_formulario(driver, link)

                    if enviado and not monitorar_analista:
                        monitorar_analista = True
                        log(f"🛡️ Formulario enviado. Vigilância do analista ativada para '{NOME_DO_ANALISTA}'.")
                        notificar_ntfy("Vigilância Ativada", "Monitoramento de mensagem do analista ativado após envio.", "shield", "default")
                else:
                    msgs_processadas.add(msg_id)

            time.sleep(2)

    except KeyboardInterrupt:
        log("Bot encerrado pelo usuário.")
        notificar_ntfy("Bot Encerrado", "Bot de Formulario foi desligado.", "zzz")
        try:
            driver.quit()
        except:
            pass

if __name__ == "__main__":
    main()