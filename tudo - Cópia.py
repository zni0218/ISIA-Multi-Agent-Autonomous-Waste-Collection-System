import random
import asyncio
import threading
import tkinter as tk
from spade.agent import Agent
from spade.behaviour import CyclicBehaviour
from PIL import Image, ImageTk

# Calcular a distância de Manhattan
def distancia_manhattan(pos1, pos2):
    return abs(pos1[0] - pos2[0]) + abs(pos1[1] - pos2[1])

# Ambiente
class Ambiente:
    def __init__(self, tamanho=10):
        self.tamanho = tamanho
        self.deposito_central = (tamanho // 2, tamanho // 2)
        self.roadblocks = set()  # Conjunto de bloqueios
        self.bins = set()
        self.bins_atribuidos = set()

    def posicao_aleatoria(self):
        return random.randint(0, self.tamanho - 1), random.randint(0, self.tamanho - 1)

    async def gerar_roadblocks_temporarios(self):
        self.roadblocks.clear()
        num_roadblocks = random.randint(10,15)
        posicoes_bins = {b.localizacao for b in self.bins}
        while len(self.roadblocks) < num_roadblocks:
            posicao = self.posicao_aleatoria()
            if posicao not in posicoes_bins and posicao != self.deposito_central:
                self.roadblocks.add(posicao)

        await asyncio.sleep(random.randint(5, 10))
        self.roadblocks.clear()


# Caminhão Agente
class CaminhaoAgente(Agent):
    def __init__(self, jid, senha, ambiente):
        super().__init__(jid, senha)
        self.ambiente = ambiente
        self.posicao = ambiente.posicao_aleatoria()
        self.gasolina = 20
        self.capacidade = 500
        self.carga_atual = 0
        self.bin_alvo = None

    class ColetaLixoComportamento(CyclicBehaviour):
        async def run(self):
            if self.agent.gasolina <= 0:
                print(f"{self.agent.name} sem combustível! Abortando missão e indo ao depósito.")
                await self.mover_para(self.agent.ambiente.deposito_central)
                return  # Se não tem combustível suficiente, aborta a missão e vai ao depósito

            # Verifica se o caminhão tem combustível suficiente para realizar a missão de coleta
            if self.agent.bin_alvo is None:
                bin_mais_proximo = None
                menor_distancia = float('inf')

                # Verifica todas as lixeiras viáveis
                for b in self.agent.ambiente.bins:
                    if b.nivel_lixo >= 75 and b not in self.agent.ambiente.bins_atribuidos:
                        # Calcular a distância até a lixeira
                        distancia_ate_bin = distancia_manhattan(self.agent.posicao, b.localizacao)

                        # Calcular a distância de ida e volta (ida até a lixeira e volta ao depósito)
                        distancia_necessaria = distancia_ate_bin + distancia_manhattan(b.localizacao, self.agent.ambiente.deposito_central)

                        # Verifica se o caminhão tem combustível suficiente para a ida e volta
                        if self.agent.gasolina >= distancia_necessaria and distancia_ate_bin < menor_distancia:
                            menor_distancia = distancia_ate_bin
                            bin_mais_proximo = b

                # Se o caminhão encontrar uma lixeira válida e viável
                if bin_mais_proximo:
                    self.agent.bin_alvo = bin_mais_proximo
                    self.agent.ambiente.bins_atribuidos.add(bin_mais_proximo)
                    print(f"{self.agent.name} targeting bin at {bin_mais_proximo.localizacao}")
                else:
                    # Se não há lixeiras viáveis devido à falta de combustível
                    print(f"{self.agent.name} não tem combustível suficiente para atingir qualquer lixeira.")
                    await self.mover_para(self.agent.ambiente.deposito_central)

            # Caso o caminhão tenha coletado lixo suficiente ou esteja sem combustível
            if self.agent.carga_atual >= self.agent.capacidade or self.agent.gasolina <= 0:
                if self.agent.posicao == self.agent.ambiente.deposito_central:
                    print(f"{self.agent.name} reabastecendo e descarregando no depósito.")
                    self.agent.carga_atual = 0
                    self.agent.gasolina = 20
                else:
                    print(f"{self.agent.name} indo ao depósito para reabastecer e descarregar.")
                    if self.agent.bin_alvo:
                        self.agent.ambiente.bins_atribuidos.discard(self.agent.bin_alvo)
                        self.agent.bin_alvo = None
                    # Verificar se o caminhão tem combustível suficiente para ir ao depósito
                    distancia_ate_deposito = distancia_manhattan(self.agent.posicao, self.agent.ambiente.deposito_central)
                    if self.agent.gasolina >= distancia_ate_deposito:
                        await self.mover_para(self.agent.ambiente.deposito_central)
                    else:
                        print(f"{self.agent.name} não tem combustível suficiente para voltar ao depósito.")
                        await self.mover_para(self.agent.ambiente.deposito_central)  # Sempre volta ao depósito

            # Caso o caminhão tenha um lixo alvo
            if self.agent.bin_alvo:
                await self.mover_para(self.agent.bin_alvo.localizacao)
                if self.agent.posicao == self.agent.bin_alvo.localizacao:
                    print(f"{self.agent.name} collected waste from bin at {self.agent.bin_alvo.localizacao}")
                    self.agent.carga_atual += self.agent.bin_alvo.quantidade_lixo  # Usando o lixo absoluto
                    self.agent.bin_alvo.respawn()
                    self.agent.ambiente.bins_atribuidos.discard(self.agent.bin_alvo)
                    self.agent.bin_alvo = None

            await asyncio.sleep(1)

        async def mover_para(self, destino):
            dx, dy = destino
            cx, cy = self.agent.posicao

            if (cx, cy) != (dx, dy):
                # Tentativa de mover-se
                if cx < dx and (cx + 1, cy) not in self.agent.ambiente.roadblocks:
                    cx += 1
                elif cx > dx and (cx - 1, cy) not in self.agent.ambiente.roadblocks:
                    cx -= 1
                elif cy < dy and (cx, cy + 1) not in self.agent.ambiente.roadblocks:
                    cy += 1
                elif cy > dy and (cx, cy - 1) not in self.agent.ambiente.roadblocks:
                    cy -= 1

                # Se houve movimento, atualizar a posição e consumir combustível
                if (cx, cy) != (self.agent.posicao[0], self.agent.posicao[1]):
                    self.agent.posicao = (cx, cy)
                    self.agent.gasolina -= 1  # Só consome combustível quando há movimento
                    print(f"{self.agent.name} movendo-se para {self.agent.posicao}")
                else:
                    print(f"{self.agent.name} está parado devido a bloqueio na rua.")
            else:
                print(f"{self.agent.name} já está na posição {self.agent.posicao}, sem movimento.")

                # Se o caminhão estiver no depósito central, ele reabastece
                if self.agent.posicao == self.agent.ambiente.deposito_central:
                    print(f"{self.agent.name} passou pelo depósito central: reabastecendo e descarregando lixo.")
                    self.agent.carga_atual = 0
                    self.agent.gasolina = 20


    async def setup(self):
        self.add_behaviour(self.ColetaLixoComportamento())

# Lixeira Agente
class LixeiraAgente:
    def __init__(self, ambiente):
        self.ambiente = ambiente
        self.localizacao = ambiente.posicao_aleatoria()
        self.nivel_lixo = random.randint(75, 100)  # Nível percentual de lixo
        self.quantidade_lixo = random.randint(50, 200)  # Quantidade absoluta de lixo

    def respawn(self):
        self.localizacao = self.ambiente.posicao_aleatoria()
        self.nivel_lixo = random.randint(75, 100)
        self.quantidade_lixo = random.randint(50, 200)  # Quantidade aleatória de lixo
        print(f"Bin respawned at {self.localizacao} with waste level {self.nivel_lixo}% and quantity {self.quantidade_lixo} units.")

# Função de GUI
# GUI Function
def iniciar_gui(ambiente, caminhao_agentes):
    root = tk.Tk()
    root.title("Waste Collection Simulation")
    canvas = tk.Canvas(root, width=500, height=500)
    canvas.pack()

    # Carregar a imagem do caminhão
    caminhao_img = Image.open("camiao.png").resize((50, 50), Image.LANCZOS)
    caminhao_img_tk = ImageTk.PhotoImage(caminhao_img)

    # Carregar a imagem do lixo uma vez
    lixo_img = Image.open("lixeira.png").resize((50, 50), Image.LANCZOS)
    lixo_img_tk = ImageTk.PhotoImage(lixo_img)

    def atualizar_interface():
        canvas.delete("all")
        depot_x, depot_y = ambiente.deposito_central
        canvas.create_rectangle(depot_x * 50, depot_y * 50, depot_x * 50 + 50, depot_y * 50 + 50, fill="red")
        canvas.create_text(depot_x * 50 + 25, depot_y * 50 + 25, text="Depot", fill="white")

        # Desenhar bloqueios (roadblocks)
        for block in ambiente.roadblocks:
            block_x, block_y = block
            canvas.create_rectangle(block_x * 50, block_y * 50, block_x * 50 + 50, block_y * 50 + 50, fill="gray")

        # Desenhar caminhões
        for caminhao in caminhao_agentes:
            x, y = caminhao.posicao
            canvas.create_image(x * 50, y * 50, anchor=tk.NW, image=caminhao_img_tk)
            canvas.create_text(x * 50 + 60, y * 50 + 10, text=f"Gas: {caminhao.gasolina}%", fill="black")
            canvas.create_text(x * 50 + 60, y * 50 + 30, text=f"Load: {caminhao.carga_atual}/{caminhao.capacidade}",
                               fill="black")

        # Desenhar lixeiras
        for i, b in enumerate(ambiente.bins):
            x, y = b.localizacao
            if b.nivel_lixo >= 75:
                canvas.create_image(x * 50, y * 50, anchor=tk.NW, image=lixo_img_tk)
                canvas.create_text(x * 50 + 25, y * 50 + 25, text=f"B{i} ({b.nivel_lixo}% - {b.quantidade_lixo} units)",
                                   fill="black")

        root.after(1000, atualizar_interface)

    # Inicializar a interface
    atualizar_interface()
    root.mainloop()


    atualizar_interface()
    root.mainloop()

async def main():
    ambiente = Ambiente()
    num_caminhoes = 3
    num_lixeiras = 5

    caminhao_agentes = [CaminhaoAgente(f"caminhao{i}@localhost", "senha_caminhao", ambiente) for i in range(num_caminhoes)]
    ambiente.bins = [LixeiraAgente(ambiente) for _ in range(num_lixeiras)]

    for agente in caminhao_agentes:
        await agente.start()

    gui_thread = threading.Thread(target=iniciar_gui, args=(ambiente, caminhao_agentes), daemon=True)
    gui_thread.start()

    try:
        while True:
            await ambiente.gerar_roadblocks_temporarios()
            await asyncio.sleep(10)
    except KeyboardInterrupt:
        for agente in caminhao_agentes:
            await agente.stop()

if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    loop.create_task(main())
    loop.run_forever()
