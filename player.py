import pygame
import socket
import threading
import json
import sys
from pygame.locals import *

# Configurações gráficas
LARGURA = 600
ALTURA = 800
TAMANHO_CELULA = 120
TAMANHO_TABULEIRO = 5

CORES = {
    'PRETO': (0, 0, 0),
    'BRANCO': (255, 255, 255),
    'CINZA': (100, 100, 100),
    'CINZA_ESCURO': (150, 150, 150),
    'MARROM': (139, 69, 19),
    'MARROM_CLARO': (160, 82, 45),
    'VERDE_ESCURO': (50, 255, 0),
    'AZUL': (0, 0, 255),
    'VERMELHO': (255, 0, 0),
    'VERMELHO_CLARO': (200, 0, 0),
    'VERDE': (0, 255, 0),
    'AMARELO': (255, 255, 0)
}

# Rect do botão de desistir
RECT_DESISTIR = pygame.Rect(LARGURA - 120, 610, 100, 40)

FONTE_PADRAO = "freesansbold.ttf"

class TelaInicial:
    def __init__(self):
        pygame.init()
        self.tela = pygame.display.set_mode((400, 300))
        self.fonte = pygame.font.Font(FONTE_PADRAO, 28)
        self.ip = ''
        self.nome = ''
        self.campo_ativo = 'ip'
        self.erro = ''

    def desenhar(self):
        self.tela.fill((30, 30, 30))
        titulo = self.fonte.render('Configuração da Partida', True, CORES['BRANCO'])
        self.tela.blit(titulo, (20, 20))

        pygame.draw.rect(self.tela, (100, 100, 100) if self.campo_ativo == 'ip' else (70, 70, 70), (20, 80, 360, 40))
        texto_ip = self.fonte.render(f'IP: {self.ip}', True, CORES['BRANCO'])
        self.tela.blit(texto_ip, (30, 90))

        pygame.draw.rect(self.tela, (100, 100, 100) if self.campo_ativo == 'nome' else (70, 70, 70), (20, 150, 360, 40))
        texto_nome = self.fonte.render(f'Nome: {self.nome}', True, CORES['BRANCO'])
        self.tela.blit(texto_nome, (30, 160))

        pygame.draw.rect(self.tela, CORES['VERDE'], (20, 220, 360, 50))
        texto_botao = self.fonte.render('CONECTAR', True, CORES['BRANCO'])
        self.tela.blit(texto_botao, (150, 235))

        if self.erro:
            texto_erro = self.fonte.render(self.erro, True, CORES['VERMELHO'])
            self.tela.blit(texto_erro, (20, 270))

        pygame.display.flip()

    def executar(self):
        executando = True
        while executando:
            for evento in pygame.event.get():
                if evento.type == QUIT:
                    pygame.quit()
                    sys.exit()
                if evento.type == MOUSEBUTTONDOWN:
                    x, y = evento.pos
                    if 20 <= x <= 380 and 220 <= y <= 270:
                        if self.ip and self.nome:
                            executando = False
                        else:
                            self.erro = 'Preencha ambos os campos!'
                    elif 20 <= y <= 120:
                        self.campo_ativo = 'ip'
                    elif 150 <= y <= 190:
                        self.campo_ativo = 'nome'
                if evento.type == KEYDOWN:
                    if evento.key == K_TAB:
                        self.campo_ativo = 'nome' if self.campo_ativo == 'ip' else 'ip'
                    elif evento.key == K_RETURN:
                        if self.ip and self.nome:
                            executando = False
                        else:
                            self.erro = 'Preencha ambos os campos!'
                    elif evento.key == K_BACKSPACE:
                        if self.campo_ativo == 'ip':
                            self.ip = self.ip[:-1]
                        else:
                            self.nome = self.nome[:-1]
                    else:
                        if evento.unicode.isprintable():
                            if self.campo_ativo == 'ip' and len(self.ip) < 15:
                                self.ip += evento.unicode
                            elif self.campo_ativo == 'nome' and len(self.nome) < 20:
                                self.nome += evento.unicode
                    self.erro = ''
            self.desenhar()
        return self.ip.strip(), self.nome.strip()

class ClienteSeega:
    def __init__(self, ip, nome):
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.connect((ip, 12345))
        self.nome = nome
        self.jogador_id = None
        self.estado = {
            'tabuleiro': [['-' for _ in range(TAMANHO_TABULEIRO)] for _ in range(TAMANHO_TABULEIRO)],
            'jogador_atual': 'P1',
            'fase': 1,
            'vencedor': None,
            'pecas_p1': 12,
            'pecas_p2': 12
        }
        self.chat = []
        self.input_chat = ''
        self.selecionado = None
        self.movimentos_validos = []

        threading.Thread(target=self.receber_dados, daemon=True).start()
        self.iniciar_interface()

    def receber_dados(self):
        while True:
            try:
                data = self.sock.recv(4096).decode()
                if not data:
                    break
                if data.startswith("ESTADO:"):
                    estado_recebido = json.loads(data[len("ESTADO:"):])
                    self.estado.update({
                        'tabuleiro': estado_recebido.get('tabuleiro', self.estado['tabuleiro']),
                        'jogador_atual': estado_recebido.get('jogador_atual', self.estado['jogador_atual']),
                        'fase': estado_recebido.get('fase', self.estado['fase']),
                        'vencedor': estado_recebido.get('vencedor', self.estado['vencedor']),
                        'pecas_p1': estado_recebido.get('pecas_p1', self.estado['pecas_p1']),
                        'pecas_p2': estado_recebido.get('pecas_p2', self.estado['pecas_p2'])
                    })
                    self.atualizar_movimentos_validos()
                elif data.startswith("CHAT:"):
                    self.chat.append(data[len("CHAT:"):])
                elif data.startswith("JOGADOR:"):
                    self.jogador_id = data[len("JOGADOR:"):]
                elif data.startswith("VENCEDOR:"):
                    self.estado['vencedor'] = data[len("VENCEDOR:"):]
                elif data.startswith("DESISTIU:"):
                    vencedor = data[len("DESISTIU:"):]
                    print(f"Jogador {vencedor} venceu por desistência!")
                    break
            except Exception as e:
                print(f"Erro na conexão: {e}")
                break

    def enviar(self, mensagem):
        try:
            self.sock.send(mensagem.encode())
        except:
            print("Erro ao enviar mensagem")

    def enviar_movimento(self, tipo, origem, destino):
        self.enviar(f"MOVIMENTO:{json.dumps((tipo, origem, destino))}")

    def enviar_chat(self, texto):
        self.enviar(f"CHAT:{self.nome}: {texto}")

    def desistir(self):
        self.enviar(f"DESISTIU:{self.jogador_id}")
        pygame.quit()
        sys.exit()

    def atualizar_movimentos_validos(self):
        self.movimentos_validos = []
        if self.estado['fase'] != 2:
            return
        for i in range(TAMANHO_TABULEIRO):
            for j in range(TAMANHO_TABULEIRO):
                if self.estado['tabuleiro'][i][j] == ('P' if self.jogador_id == 'P1' else 'B'):
                    for dx, dy in [(-1,0), (1,0), (0,-1), (0,1)]:
                        dist = 1
                        while True:
                            ni, nj = i + dx*dist, j + dy*dist
                            if not (0 <= ni < TAMANHO_TABULEIRO and 0 <= nj < TAMANHO_TABULEIRO) or self.estado['tabuleiro'][ni][nj] != '-':
                                break
                            self.movimentos_validos.append((ni, nj))
                            dist += 1

    def desenhar_tabuleiro(self, tela):
        tela.fill(CORES['MARROM_CLARO'])
        for i in range(TAMANHO_TABULEIRO):
            for j in range(TAMANHO_TABULEIRO):
                cor = CORES['MARROM_CLARO'] if (i+j) % 2 == 0 else CORES['MARROM']
                pygame.draw.rect(tela, cor, (j*TAMANHO_CELULA, i*TAMANHO_CELULA, TAMANHO_CELULA, TAMANHO_CELULA))
                c = self.estado['tabuleiro'][i][j]
                centro = (j*TAMANHO_CELULA + TAMANHO_CELULA//2, i*TAMANHO_CELULA + TAMANHO_CELULA//2)
                if c == 'P':
                    pygame.draw.circle(tela, CORES['PRETO'], centro, 25)
                elif c == 'B':
                    pygame.draw.circle(tela, CORES['BRANCO'], centro, 25)
                elif c == 'X':
                    pygame.draw.rect(tela, CORES['CINZA_ESCURO'], (j*TAMANHO_CELULA, i*TAMANHO_CELULA, TAMANHO_CELULA, TAMANHO_CELULA))
                if self.selecionado == (i, j):
                    pygame.draw.rect(tela, CORES['AMARELO'], (j*TAMANHO_CELULA+3, i*TAMANHO_CELULA+3, TAMANHO_CELULA-6, TAMANHO_CELULA-6), 3)

    def desenhar_ui(self, tela):
        fonte = pygame.font.Font(None, 36)
        # Exibe apenas informação de turno
        atual = self.estado['jogador_atual']
        turno_txt = f"Seu turno: {self.nome}" if atual == self.jogador_id else f"Turno de: {atual}"
        texto_turno = fonte.render(turno_txt, True, CORES['VERDE'])
        tela.blit(texto_turno, (10, 610))

        # Botão Desistir
        pygame.draw.rect(tela, CORES['VERMELHO_CLARO'], RECT_DESISTIR)
        txt_desistir = fonte.render('Desistir', True, CORES['BRANCO'])
        tela.blit(txt_desistir, (RECT_DESISTIR.x + 5, RECT_DESISTIR.y + 5))

    def desenhar_chat(self, tela):
        pygame.draw.rect(tela, CORES['BRANCO'], (0, 600, LARGURA, 200))
        f = pygame.font.Font(None, 24)
        y = 610
        for msg in self.chat[-8:]:
            tela.blit(f.render(msg, True, CORES['PRETO']), (10, y))
            y += 20
        pygame.draw.rect(tela, CORES['CINZA'], (10, 760, 580, 30))
        tela.blit(f.render(f"> {self.input_chat}", True, CORES['PRETO']), (15, 765))

    def handle_clique(self, pos):
        x, y = pos
        if RECT_DESISTIR.collidepoint(x, y):
            self.desistir()
            return
        if y > 600 or self.estado.get('vencedor'):
            return
        lin, col = y // TAMANHO_CELULA, x // TAMANHO_CELULA
        if self.estado['fase'] == 1 and self.jogador_id == self.estado['jogador_atual']:
            self.enviar_movimento('colocacao', None, (lin, col))
        elif self.estado['fase'] == 2 and self.jogador_id == self.estado['jogador_atual']:
            if not self.selecionado:
                if self.estado['tabuleiro'][lin][col] == ('P' if self.jogador_id=='P1' else 'B'):
                    self.selecionado = (lin, col)
            else:
                if (lin, col) in self.movimentos_validos:
                    self.enviar_movimento('movimento', self.selecionado, (lin, col))
                self.selecionado = None

    def iniciar_interface(self):
        pygame.init()
        tela = pygame.display.set_mode((LARGURA, ALTURA))
        pygame.display.set_caption(f"Seega - {self.nome}")
        clock = pygame.time.Clock()
        chat_ativo = False
        while True:
            for evento in pygame.event.get():
                if evento.type == QUIT:
                    pygame.quit()
                    sys.exit()
                if evento.type == MOUSEBUTTONDOWN:
                    self.handle_clique(evento.pos)
                    chat_ativo = evento.pos[1] > 600
                if evento.type == KEYDOWN and chat_ativo:
                    if evento.key == K_RETURN and self.input_chat.strip():
                        self.enviar_chat(self.input_chat)
                        self.input_chat = ''
                    elif evento.key == K_BACKSPACE:
                        self.input_chat = self.input_chat[:-1]
                    else:
                        self.input_chat += evento.unicode

            self.desenhar_tabuleiro(tela)
            self.desenhar_chat(tela)
            self.desenhar_ui(tela)
            pygame.display.flip()
            clock.tick(30)

if __name__ == '__main__':
    tela_inicial = TelaInicial()
    ip, nome = tela_inicial.executar()
    pygame.quit()
    ClienteSeega(ip, nome)
