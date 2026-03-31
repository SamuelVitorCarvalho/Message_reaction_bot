import cv2
import numpy as np
import mss
import time
import pytesseract

# ==========================================
# CONFIGURAÇÕES
# ==========================================
# ⚠️ O caminho do seu Tesseract
pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'
PORCENTAGEM_ESQUERDA = 0.30 

def calibrar_leitura_titulo():
    print("="*50)
    print(" 🔬 LABORATÓRIO DE OCR - DEBUG DE TÍTULO")
    print("="*50)
    print("Aperte 'q' nas janelas para sair.\n")

    try:
        ancora_img = cv2.imread('ancora_enquete.png', 0)
    except:
        print("❌ ERRO: Faltou a 'ancora_enquete.png' na pasta!")
        return

    ultimo_print = time.time()

    with mss.mss() as sct:
        monitor = sct.monitors[1] 

        while True:
            img_inteira = np.array(sct.grab(monitor))
            linha_de_corte = int(img_inteira.shape[1] * PORCENTAGEM_ESQUERDA)
            
            img_direita = img_inteira[:, linha_de_corte:]
            gray_direita = cv2.cvtColor(img_direita, cv2.COLOR_BGRA2GRAY)

            res_ancora = cv2.matchTemplate(gray_direita, ancora_img, cv2.TM_CCOEFF_NORMED)
            loc_ancora = np.where(res_ancora >= 0.85)
            
            pontos = list(zip(*loc_ancora[::-1]))

            if pontos:
                # Pega a primeira âncora que achar
                x_ancora, y_ancora = pontos[0]

                # 1. Recorta a área do Título
                y_tit_inicio = max(0, y_ancora - 45) 
                y_tit_fim = y_ancora                
                x_tit_inicio = max(0, x_ancora - 10) 
                x_tit_fim = x_ancora + 350          
                
                recorte_titulo = gray_direita[y_tit_inicio:y_tit_fim, x_tit_inicio:x_tit_fim]

                # 2. Aplica o Zoom (aumentei de 3x para 4x para testarmos)
                zoom_titulo = cv2.resize(recorte_titulo, None, fx=4, fy=4, interpolation=cv2.INTER_CUBIC)
                
                # 3. FILTRO DE ALTO CONTRASTE (Igual fizemos com a hora)
                # O que for mais claro que 130 vira preto (texto), o que for escuro vira branco (fundo)
                _, titulo_tratado = cv2.threshold(zoom_titulo, 130, 255, cv2.THRESH_BINARY_INV)

                # Mostra na tela a imagem exata que o robô vai ler
                cv2.imshow("VISÃO DO ROBO (Preto e Branco)", titulo_tratado)

                # 4. Lê a imagem a cada 1.5 segundos para você conseguir ler no terminal
                if time.time() - ultimo_print > 1.5:
                    # --psm 7 avisa o Tesseract que é uma linha única de texto
                    # Se tiver o pacote de português instalado, mude lang='eng' para lang='por'
                    config_ocr = r'--psm 7' 
                    texto_lido = pytesseract.image_to_string(titulo_tratado, lang='eng', config=config_ocr).strip()
                    texto_limpo = texto_lido.replace('\n', ' ')
                    
                    print(f"📖 LENDO: [{texto_limpo}]")
                    ultimo_print = time.time()

            cv2.imshow("TELA DIREITA", cv2.resize(img_direita, (0, 0), fx=0.6, fy=0.6))

            if cv2.waitKey(1) & 0xFF == ord('q'):
                break

    cv2.destroyAllWindows()

if __name__ == "__main__":
    calibrar_leitura_titulo()