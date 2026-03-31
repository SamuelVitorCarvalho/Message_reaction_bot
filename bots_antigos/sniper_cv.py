import cv2
import numpy as np
import mss
import pyautogui
import time
import pytesseract
import winsound
import re

# ==========================================
# CONFIGURAÇÕES GERAIS E EXTREMAS
# ==========================================
pyautogui.PAUSE = 0 
pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'
PORCENTAGEM_ESQUERDA = 0.30 

REGRAS_DE_ACEITE = [
    ["Betim"], ["Juatuba_1"], ["Niterói"], ["Niteroi"], ["Pará de Minas"], ["Para de Minas"],
    ["Santo Afonso"], ["Petrovale"], ["PTB"], ["Cruzeiro"], ["Dom Bosco"],
]
PALAVRAS_PROIBIDAS = ["teresópolis", "teresopolis", "citrolândia", "citrolandia", "fiorino"]

def verificar_regras(texto):
    texto = texto.lower().strip()
    for proibida in PALAVRAS_PROIBIDAS:
        if proibida.lower().strip() in texto: return False, f"🚫 Proibida: {proibida}", None
    for grupo in REGRAS_DE_ACEITE:
        if all(palavra.lower().strip() in texto for palavra in grupo): return True, f"✅ Aprovado: {grupo}", str(grupo) 
    return False, "⚠️ Sem Match", None

def disparar_alarme_voto():
    try:
        for _ in range(3): winsound.Beep(1500, 200)
    except: pass

def disparar_alarme_emergencia():
    try:
        winsound.Beep(800, 1000) 
    except: pass

def iniciar_bot_paralelo():
    print("="*50)
    print(" 🚀 BOT PARALELO - SNIPER DE TIRO ÚNICO (V3 - LEITURA TURBINADA)")
    print("="*50)

    try:
        ancora_img = cv2.imread('ancora_enquete.png', 0)
        w_ancora, h_ancora = ancora_img.shape[::-1]
        bolinha_vazia = cv2.imread('bolinha_vazia.png', 0)
        w_vazia, h_vazia = bolinha_vazia.shape[::-1]
        
        ancora_analista = cv2.imread('ancora_analista.png', 0)
        w_analista, h_analista = ancora_analista.shape[::-1]
        bolinha_verde = cv2.imread('bolinha_verde.png', 0)
        w_verde, h_verde = bolinha_verde.shape[::-1]
    except:
        print("❌ ERRO: Faltam imagens na pasta!")
        return

    # 🧠 Memória: (Foto_do_Titulo, Texto_da_Hora)
    memoria_fotografica = []

    with mss.mss() as sct:
        monitor = sct.monitors[1] 
        
        # Clique de Foco Inicial
        img_teste = np.array(sct.grab(monitor))
        linha_de_corte = int(img_teste.shape[1] * PORCENTAGEM_ESQUERDA)
        
        print("🖱️ Focando a janela do WhatsApp automaticamente...")
        pyautogui.click(monitor["left"] + linha_de_corte + 200, monitor["top"] + 30)
        time.sleep(0.5) 
        print("✅ Radares ligados! Monitorando enquetes e vigiando o Analista...\n")

        while True:
            img_inteira = np.array(sct.grab(monitor))
            
            img_esquerda = img_inteira[:, :linha_de_corte]
            img_direita = img_inteira[:, linha_de_corte:]
            
            gray_esquerda = cv2.cvtColor(img_esquerda, cv2.COLOR_BGRA2GRAY)
            gray_direita = cv2.cvtColor(img_direita, cv2.COLOR_BGRA2GRAY)

            # =========================================================
            # 🛡️ FASE 1: O SENTINELA (FREIO DE MÃO DEFINITIVO)
            # =========================================================
            analista_chamando = False
            
            res_analista = cv2.matchTemplate(gray_esquerda, ancora_analista, cv2.TM_CCOEFF_NORMED)
            loc_analista = np.where(res_analista >= 0.85)

            for pt in zip(*loc_analista[::-1]):
                xa = pt[0]
                ya = pt[1]
                
                y_busca_inicio = max(0, ya - 10)
                y_busca_fim = ya + 60
                x_busca_inicio = xa + 150   
                x_busca_fim = linha_de_corte - 5 
                
                area_busca_verde = gray_esquerda[y_busca_inicio:y_busca_fim, x_busca_inicio:x_busca_fim]
                res_verde = cv2.matchTemplate(area_busca_verde, bolinha_verde, cv2.TM_CCOEFF_NORMED)
                
                if np.any(res_verde >= 0.75):
                    analista_chamando = True
                    break

            if analista_chamando:
                print("\n" + "🚨"*20)
                print(" [ALERTA] O ANALISTA MANDOU MENSAGEM!")
                print(" O alarme tocou 1 vez. O bot está TOTALMENTE PAUSADO.")
                print(" Vá ler a mensagem. Quando a bolinha verde sumir, o bot será encerrado.")
                print("🚨"*20 + "\n")
                
                disparar_alarme_emergencia() 
                
                while True:
                    time.sleep(1) 
                    img_coma = np.array(sct.grab(monitor))
                    gray_coma = cv2.cvtColor(img_coma[:, :linha_de_corte], cv2.COLOR_BGRA2GRAY)
                    
                    res_ana = cv2.matchTemplate(gray_coma, ancora_analista, cv2.TM_CCOEFF_NORMED)
                    loc_ana = np.where(res_ana >= 0.85)
                    
                    ainda_tem_bolinha = False
                    
                    for pt_c in zip(*loc_ana[::-1]):
                        xc, yc = pt_c
                        area_busca_coma = gray_coma[max(0, yc - 10):yc + 60, xc + 150:linha_de_corte - 5]
                        
                        if np.any(cv2.matchTemplate(area_busca_coma, bolinha_verde, cv2.TM_CCOEFF_NORMED) >= 0.75):
                            ainda_tem_bolinha = True
                            break 
                            
                    if not ainda_tem_bolinha:
                        print("✅ Você abriu a conversa do Analista! Assuma o controle.")
                        print("🤖 Encerrando o bot Sniper com sucesso. Até a próxima!")
                        return 

            # =========================================================
            # 🎯 FASE 2: O SNIPER (COM MEMÓRIA DUPLA)
            # =========================================================
            res_ancora = cv2.matchTemplate(gray_direita, ancora_img, cv2.TM_CCOEFF_NORMED)
            loc_ancora = np.where(res_ancora >= 0.85)

            ancoras_encontradas = list(zip(*loc_ancora[::-1]))
            ancoras_encontradas.sort(key=lambda p: p[1], reverse=True) 

            ancoras_principais = []
            ultimo_y = -1000
            for x, y in ancoras_encontradas:
                if abs(y - ultimo_y) > 80:
                    ancoras_principais.append((x, y))
                    ultimo_y = y

            for x_ancora, y_ancora in ancoras_principais:
                
                # 1. Tira a foto do título
                y_tit_inicio = max(0, y_ancora - 45) 
                y_tit_fim = y_ancora                
                x_tit_inicio = max(0, x_ancora - 10) 
                x_tit_fim = x_ancora + 350          
                recorte_titulo = gray_direita[y_tit_inicio:y_tit_fim, x_tit_inicio:x_tit_fim]

                # 2. Lê a HORA imediatamente (É super rápido)
                y_h_ini = y_ancora + 140
                y_h_fim = y_ancora + 220
                x_h_ini = x_ancora + 250
                x_h_fim = x_ancora + 400
                recorte_h = gray_direita[y_h_ini:y_h_fim, x_h_ini:x_h_fim]
                zoom_h = cv2.resize(recorte_h, None, fx=3, fy=3, interpolation=cv2.INTER_CUBIC)
                _, h_tratada = cv2.threshold(zoom_h, 130, 255, cv2.THRESH_BINARY_INV)
                config_ocr_h = r'--psm 7 -c tessedit_char_whitelist=0123456789:'
                texto_h_limpo = pytesseract.image_to_string(h_tratada, lang='eng', config=config_ocr_h).replace('\n', ' ').strip()

                hora_enc = re.search(r'\b\d{1,2}:\d{2}\b', texto_h_limpo)
                hora_exata_enq = hora_enc.group(0) if hora_enc else texto_h_limpo[:5]

                # 3. CHECA A MEMÓRIA DUPLA (Foto original + Hora)
                ja_conheco = False
                for foto_salva, hora_salva in memoria_fotografica:
                    if hora_exata_enq == hora_salva: 
                        try:
                            similaridade = cv2.matchTemplate(recorte_titulo, foto_salva, cv2.TM_CCOEFF_NORMED)
                            if np.max(similaridade) > 0.95: 
                                ja_conheco = True
                                break
                        except: pass
                
                if ja_conheco: continue

                # =========================================================
                # 4. LEITURA DE ALTO DESEMPENHO DO TÍTULO (A MÁGICA ESTÁ AQUI)
                # =========================================================
                # Aplicamos o zoom 4x e o threshold de 130 que testamos no laboratório
                zoom_titulo = cv2.resize(recorte_titulo, None, fx=4, fy=4, interpolation=cv2.INTER_CUBIC)
                _, titulo_tratado = cv2.threshold(zoom_titulo, 130, 255, cv2.THRESH_BINARY_INV)
                config_ocr_titulo = r'--psm 7'
                
                texto_titulo = pytesseract.image_to_string(titulo_tratado, lang='eng', config=config_ocr_titulo).replace('\n', ' ').strip()
                
                if not texto_titulo: continue

                match, motivo, chave_regra = verificar_regras(texto_titulo)

                if match:
                    print("\n" + "="*50)
                    print(f"🎯 ENQUETE ALVO: {motivo} | Hora: {hora_exata_enq}")
                    
                    y_bol_ini = y_ancora + h_ancora
                    y_bol_fim = y_ancora + 80            
                    x_bol_ini = max(0, x_ancora - 30)  
                    x_bol_fim = x_ancora + 60            
                    
                    area_bolinha = gray_direita[y_bol_ini:y_bol_fim, x_bol_ini:x_bol_fim]
                    res_bol = cv2.matchTemplate(area_bolinha, bolinha_vazia, cv2.TM_CCOEFF_NORMED)
                    loc_bol = np.where(res_bol >= 0.85)
                    pontos_bolinha = list(zip(*loc_bol[::-1]))

                    if pontos_bolinha:
                        pontos_bolinha.sort(key=lambda p: p[1])
                        bx_local, by_local = pontos_bolinha[0]
                        
                        x_clique_enq = monitor["left"] + linha_de_corte + x_bol_ini + bx_local + (w_vazia // 2)
                        y_clique_enq = monitor["top"] + y_bol_ini + by_local + (h_vazia // 2)
                        
                        # ⚡ TIRO ÚNICO CERTEIRO
                        pyautogui.click(x_clique_enq, y_clique_enq) 
                        
                        print("⚡ VOTO APLICADO COM SUCESSO!")
                        disparar_alarme_voto()

                    print("="*50)
                    time.sleep(0.5) 
                else:
                    print(f"🗑️ ENQUETE LIXO IGNORADA: {motivo} | Hora: {hora_exata_enq}")

                # 5. SALVA A COMBINAÇÃO NA MEMÓRIA
                # Salvamos o recorte_titulo original (sem filtro) pra comparação visual rápida
                memoria_fotografica.append((recorte_titulo, hora_exata_enq))
                if len(memoria_fotografica) > 20: 
                    memoria_fotografica.pop(0)

                break 
                    
            time.sleep(0.005)

if __name__ == "__main__":
    iniciar_bot_paralelo()