import cv2
import numpy as np
import mss
import time
import pytesseract
import re

# ⚠️ O caminho do seu Tesseract (Não esqueça de manter)
pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'

PORCENTAGEM_ESQUERDA = 0.30 

def radar_de_novas_mensagens():
    print("="*50)
    print(" 🎯 RADAR DE CONTATOS - COM MEMÓRIA DE HORÁRIO")
    print("="*50)

    try:
        ancora_analista = cv2.imread('ancora_analista.png', 0)
        w_ancora, h_ancora = ancora_analista.shape[::-1]
        
        bolinha_verde = cv2.imread('bolinha_verde.png', 0)
        w_verde, h_verde = bolinha_verde.shape[::-1]
    except:
        print("❌ ERRO: Faltam 'ancora_analista.png' ou 'bolinha_verde.png' na pasta!")
        return

    print("🔎 Monitorando a lista de contatos... (Aperte Q para sair)")
    
    # 🧠 O CÉREBRO DA ESQUERDA
    contatos_resolvidos = set()

    with mss.mss() as sct:
        monitor = sct.monitors[1] 

        while True:
            img_inteira = np.array(sct.grab(monitor))
            linha_de_corte = int(img_inteira.shape[1] * PORCENTAGEM_ESQUERDA)
            
            img_esquerda = img_inteira[:, :linha_de_corte]
            gray_esquerda = cv2.cvtColor(img_esquerda, cv2.COLOR_BGRA2GRAY)

            res_ancora = cv2.matchTemplate(gray_esquerda, ancora_analista, cv2.TM_CCOEFF_NORMED)
            loc_ancora = np.where(res_ancora >= 0.85)

            for pt in zip(*loc_ancora[::-1]):
                x_ancora = pt[0]
                y_ancora = pt[1]
                
                # Quadrado VERDE no nome (GPS)
                cv2.rectangle(img_esquerda, (x_ancora, y_ancora), (x_ancora + w_ancora, y_ancora + h_ancora), (0, 255, 0), 2)

                # =======================================================
                # CAIXA DE BUSCA DA MENSAGEM NÃO LIDA (Bolinha)
                # =======================================================
                y_busca_inicio = max(0, y_ancora - 10)
                y_busca_fim = y_ancora + 60
                x_busca_inicio = x_ancora + 250   
                x_busca_fim = linha_de_corte - 5 
                
                # Retângulo AZUL da bolinha
                cv2.rectangle(img_esquerda, (x_busca_inicio, y_busca_inicio), (x_busca_fim, y_busca_fim), (255, 0, 0), 1)

                area_busca_verde = gray_esquerda[y_busca_inicio:y_busca_fim, x_busca_inicio:x_busca_fim]
                
                res_verde = cv2.matchTemplate(area_busca_verde, bolinha_verde, cv2.TM_CCOEFF_NORMED)
                loc_verde = np.where(res_verde >= 0.75)
                pontos_verde = list(zip(*loc_verde[::-1]))

                if pontos_verde:
                    vx_local, vy_local = pontos_verde[0]
                    x_verde_real = x_busca_inicio + vx_local
                    y_verde_real = y_busca_inicio + vy_local
                    
                    # Retângulo VERMELHO GROSSO na bolinha verde!
                    cv2.rectangle(img_esquerda, (x_verde_real, y_verde_real), 
                                  (x_verde_real + w_verde, y_verde_real + h_verde), (0, 0, 255), 3)
                    
                    # =======================================================
                    # MENSAGEM ACHADA! AGORA VAMOS LER A HORA PARA A MEMÓRIA
                    # =======================================================
                    # A hora fica na mesma altura do nome, mas encostada na direita
                    y_hora_c = max(0, y_ancora - 10)
                    y_hora_f = y_ancora + 25
                    x_hora_c = x_ancora + 270  # Pula o nome e vai bem pra direita
                    x_hora_f = linha_de_corte - 25
                    
                    # 🟨 Retângulo AMARELO (Onde ele está lendo a hora)
                    cv2.rectangle(img_esquerda, (x_hora_c, y_hora_c), (x_hora_f, y_hora_f), (0, 255, 255), 1)
                    
                    recorte_hora = gray_esquerda[y_hora_c:y_hora_f, x_hora_c:x_hora_f]
                    
                    # Usa as mesmas técnicas do Sniper de Enquetes (Zoom + Threshold)
                    zoom_hora = cv2.resize(recorte_hora, None, fx=3, fy=3, interpolation=cv2.INTER_CUBIC)
                    _, hora_tratada = cv2.threshold(zoom_hora, 130, 255, cv2.THRESH_BINARY_INV)
                    
                    config_ocr = r'--psm 7 -c tessedit_char_whitelist=0123456789:'
                    texto_hora = pytesseract.image_to_string(hora_tratada, lang='eng', config=config_ocr).replace('\n', ' ').strip()
                    
                    # Extrai a hora
                    hora_encontrada = re.search(r'\b\d{1,2}:\d{2}\b', texto_hora)
                    hora_exata = hora_encontrada.group(0) if hora_encontrada else texto_hora[:5]

                    # Cria o RG do contato
                    rg_contato = f"Analista_{hora_exata}"

                    # Checa a Memória!
                    if rg_contato not in contatos_resolvidos:
                        print(f"🚨 NOVA MENSAGEM! | Contato: Analista | Hora: {hora_exata}")
                        
                        # Salva na memória para não fludar o terminal
                        contatos_resolvidos.add(rg_contato)

            cv2.imshow("RADAR ESQUERDO (Aperte Q para sair)", cv2.resize(img_esquerda, (0, 0), fx=0.8, fy=0.8))

            if cv2.waitKey(1) & 0xFF == ord('q'):
                break

    cv2.destroyAllWindows()

if __name__ == "__main__":
    radar_de_novas_mensagens()