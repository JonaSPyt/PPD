import socket
import threading
import json
from copy import deepcopy

TAMANHO_TABULEIRO = 5

class JogoSeega:
    def __init__(self):
        self.reiniciar_jogo()

    def reiniciar_jogo(self):
        self.tabuleiro = [['-' for _ in range(TAMANHO_TABULEIRO)] for _ in range(TAMANHO_TABULEIRO)]
        self.bloqueio_central = True
        self.inicializar_centro()
        self.fase = 1
        self.jogador_atual = 'P1'
        self.peças_p1 = 12
        self.peças_p2 = 12
        self.peças_tabuleiro_p1 = 0
        self.peças_tabuleiro_p2 = 0
        self.vencedor = None
        self.contador_colocacao = 0
        self.ultima_peça_capturadora = None

    def inicializar_centro(self):
        self.tabuleiro[2][2] = 'X' if self.bloqueio_central else '-'

    def coordenadas_validas(self, linha, coluna):
        return 0 <= linha < TAMANHO_TABULEIRO and 0 <= coluna < TAMANHO_TABULEIRO

    def colocar_peca(self, destino):
        linha, coluna = destino
        if not self.coordenadas_validas(linha, coluna) or self.tabuleiro[linha][coluna] != '-' or (linha, coluna) == (2, 2):
            return False

        if self.jogador_atual == 'P1' and self.peças_p1 > 0:
            self.tabuleiro[linha][coluna] = 'P'
            self.peças_p1 -= 1
            self.peças_tabuleiro_p1 += 1
            self.contador_colocacao += 1
        elif self.jogador_atual == 'P2' and self.peças_p2 > 0:
            self.tabuleiro[linha][coluna] = 'B'
            self.peças_p2 -= 1
            self.peças_tabuleiro_p2 += 1
            self.contador_colocacao += 1
        else:
            return False

        if self.contador_colocacao == 2:
            self.mudar_jogador()
            self.contador_colocacao = 0

        if self.peças_p1 == 0 and self.peças_p2 == 0:
            self.fase = 2
            self.bloqueio_central = False
            self.inicializar_centro()
        return True

    def verificar_movimento_valido(self, origem, destino):
        origem_linha, origem_coluna = origem
        destino_linha, destino_coluna = destino

        if origem_linha != destino_linha and origem_coluna != destino_coluna:
            return False

        passo_linha = 0 if origem_linha == destino_linha else (1 if destino_linha > origem_linha else -1)
        passo_coluna = 0 if origem_coluna == destino_coluna else (1 if destino_coluna > origem_coluna else -1)
        
        x, y = origem_linha + passo_linha, origem_coluna + passo_coluna
        while (x, y) != (destino_linha, destino_coluna):
            if self.tabuleiro[x][y] != '-':
                return False
            x += passo_linha
            y += passo_coluna

        return self.tabuleiro[destino_linha][destino_coluna] == '-'

    def mover_peca(self, origem, destino):
        if not self.verificar_movimento_valido(origem, destino):
            return False

        peça = self.tabuleiro[origem[0]][origem[1]]
        self.tabuleiro[origem[0]][origem[1]] = '-'
        self.tabuleiro[destino[0]][destino[1]] = peça

        capturas = self.verificar_capturas_sanduiche(destino)
        for x, y in capturas:
            self.tabuleiro[x][y] = '-'
            if self.jogador_atual == 'P1':
                self.peças_tabuleiro_p2 -= 1
            else:
                self.peças_tabuleiro_p1 -= 1

        self.verificar_vencedor()
        if not capturas:
            self.mudar_jogador()
        else:
            self.ultima_peça_capturadora = destino
        return True

    def verificar_capturas_sanduiche(self, destino):
        capturas = []
        jogador = 'P' if self.jogador_atual == 'P1' else 'B'
        inimigo = 'B' if jogador == 'P' else 'P'
        direcoes = [(-1,0), (1,0), (0,-1), (0,1)]
        
        for dx, dy in direcoes:
            x, y = destino[0] + dx, destino[1] + dy
            x2, y2 = x + dx, y + dy
            if self.coordenadas_validas(x, y) and self.coordenadas_validas(x2, y2):
                if self.tabuleiro[x][y] == inimigo and self.tabuleiro[x2][y2] == jogador:
                    capturas.append((x, y))
        return capturas

    def mudar_jogador(self):
        self.jogador_atual = 'P2' if self.jogador_atual == 'P1' else 'P1'
        self.ultima_peça_capturadora = None

    def verificar_vencedor(self):
        if self.peças_tabuleiro_p1 == 0:
            self.vencedor = 'P2'
        elif self.peças_tabuleiro_p2 == 0:
            self.vencedor = 'P1'


class SeegaServer:
    def __init__(self, host='0.0.0.0', porta=12345):
        self.jogo = JogoSeega()
        self.lock = threading.Lock()
        self.chat_history = []
        self.conexoes = []
        self.server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server.bind((host, porta))
        self.server.listen(2)
        print(f"Servidor Seega na porta {porta}")

    def iniciar(self):
        while True:
            try:
                conn, addr = self.server.accept()  # desempacota socket e endereço
            except Exception as e:
                print(f"Erro ao aceitar conexão: {e}")
                continue

            with self.lock:
                if len(self.conexoes) < 2:
                    jogador = 'P1' if len(self.conexoes) == 0 else 'P2'
                    self.conexoes.append((conn, jogador))
                    conn.send(f"JOGADOR:{jogador}".encode())
                    threading.Thread(target=self.handle_client, args=(conn, jogador), daemon=True).start()

    def handle_client(self, conn, jogador):
        try:
            while True:
                data = conn.recv(4096).decode()
                if not data:
                    break

                if data.startswith("MOVIMENTO:"):
                    tipo, origem, destino = json.loads(data[len("MOVIMENTO:"):])
                    with self.lock:
                        if self.jogo.jogador_atual != jogador:
                            continue

                        sucesso = False
                        if tipo == 'colocacao':
                            sucesso = self.jogo.colocar_peca(destino)
                        elif tipo == 'movimento':
                            sucesso = self.jogo.mover_peca(origem, destino)

                        if sucesso:
                            self.broadcast_estado()
                            if self.jogo.vencedor:
                                self.broadcast(f"VENCEDOR:{self.jogo.vencedor}")

                elif data.startswith("CHAT:"):
                    msg = data[len("CHAT:"):]
                    with self.lock:
                        self.chat_history.append(msg)
                        self.broadcast(f"CHAT:{msg}")

        finally:
            with self.lock:
                self.conexoes = [c for c in self.conexoes if c[0] != conn]
            conn.close()

    def broadcast_estado(self):
        estado = {
            'tabuleiro': self.jogo.tabuleiro,
            'jogador_atual': self.jogo.jogador_atual,
            'fase': self.jogo.fase,
            'vencedor': self.jogo.vencedor,
            'pecas_p1': self.jogo.peças_p1,
            'pecas_p2': self.jogo.peças_p2
        }
        self.broadcast(f"ESTADO:{json.dumps(estado)}")

    def broadcast(self, mensagem):
        for conn, _ in list(self.conexoes):
            try:
                conn.send(mensagem.encode())
            except Exception:
                pass


if __name__ == '__main__':
    server = SeegaServer()
    server.iniciar()
