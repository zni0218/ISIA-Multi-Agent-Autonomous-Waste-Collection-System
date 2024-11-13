import random
import asyncio
import threading
import tkinter as tk
from spade.agent import Agent
from spade.behaviour import CyclicBehaviour
#import json


#---FEITO:
#ambiente (tamanho, depot, roadblocks, bins existentes, bins atribuidos)
#truck (carga, combustivel, destino, movimento)
#bin (level, respawn)
#main (inica tudo, atualiza gui)
#ETC:
#impossivel 2 trucks focar mesmo bin
#faz o percurso para o centro sem teletransportar
#impossivel por roadblock em cima de bin/depot
#impossivel por bin em cima de roadblock/depot/bin
#numero de roadblocks aleatorio (entre 1 e 5) em vez de sempre 3 ao mesmo tempo


#---IMPORTANTE (objetivos em falta):
#bins devem ser agentes que periodicamente dizem a sua % de lixo, acionando pedido de recolha quando atingem um certo %!
#TALVEZ ADICIONAR: bins fixos (10) para cada vez q se corre o programa?? so muda o level (enche uma qantidade random entre 1-10 a cada 1     segundo)???
#TALVEZ ADICIONAR: bins nao dar respawn logo??
#falha aleatoria de agentes!
#collection time para cada bin (1 distancia corresponde a 1 tempo ~30km/h)!
#distancia percorrida para cada truck (1 bloco da grelha corresponde a 1 distancia ~1km)!


#---ADICIONAR:
#separar em varios files
#melhor gui (com fotos de lixo, camioes,...)
#tamanho variavel, depot variavel??


#---OTIMIZAR!!!:
#adicionar threshold de carga (o camiao vai p o depot quando tem load a mais, mas talvez pode carregar mais se passar por PERTO de um bin no caminho, trabalhar com radius??)
#se o camiao tiver perto do depot, aproveita e vai la (definir radius tipo 2)
#definir um percurso de bins para cada truck, e nao so um bin



#----------


#calcular distancia (manhattan tipo city layout)
def manhattan_distance(pos1, pos2):
    return abs(pos1[0] - pos2[0]) + abs(pos1[1] - pos2[1])



#----------



#AMBIENTE
class Environment:

    #inicia classe
    def __init__(self, size=10):
        self.size = size                                    #tamannho da grelha
        self.central_depot = (size // 2, size // 2)         #depot de combustivel/descarga no centro
        self.roadblocks = set()                             #conjunto de roadblocks no momento
        self.bins = set()                                   #conjunto de bins no momento
        self.assigned_bins = set()                          #conjunto de bins atribuidos no momento


    #gera posicao aleatoria
    def random_position(self):
        return random.randint(0, self.size - 1), random.randint(0, self.size - 1)



    #gera roadblocks aleatorios que desaparecem passado 5-10 segundos
    async def generate_temporary_roadblocks(self):
        self.roadblocks.clear()
        num_roadblocks = random.randint(1,5)
        bin_locations = {b.location for b in self.bins}
        while len(self.roadblocks)<num_roadblocks:
            position = self.random_position()
            if position not in bin_locations and position not in self.central_depot:
                self.roadblocks.add(position)

        await asyncio.sleep(random.randint(5, 10))
        self.roadblocks.clear()



#----------



#CAMIAO
class TruckAgent(Agent):

    #inicia XMPP jid/password, ambiente, posicao inicial, gas, capacidade, carga, alvo
    def __init__(self, jid, password, environment):
        super().__init__(jid, password)
        self.environment = environment
        self.position = environment.random_position()
        self.gas = 100
        self.capacity = 500
        self.current_load = 0
        self.target_bin = None


    #define comportamento
    class CollectWasteBehaviour(CyclicBehaviour):

        #correr
        async def run(self):

            #quando nao ha alvo
            if self.agent.target_bin is None:
                closest_bin = None
                min_distance = float('inf')
                for b in self.agent.environment.bins:
                    if b.waste_level >= 75 and b not in self.agent.environment.assigned_bins:
                        distance = manhattan_distance(self.agent.position, b.location)
                        if distance < min_distance:
                            min_distance = distance
                            closest_bin = b
                if closest_bin:
                    self.agent.target_bin = closest_bin
                    self.agent.environment.assigned_bins.add(closest_bin)
                    print(f"{self.agent.name} is targeting bin at {closest_bin.location}")


            #quando tem pouco combustivel e/ou carga a mais
            if (self.agent.current_load>=self.agent.capacity or self.agent.gas <=10) and self.agent.position != self.agent.environment.central_depot:
                print(f"{self.agent.name} is full or low on gas, heading to depot.")
                if self.agent.target_bin:
                    self.agent.environment.assigned_bins.discard(self.agent.target_bin)
                    self.agent.target_bin = None
                dx, dy = self.agent.environment.central_depot
                cx, cy = self.agent.position
                # gera probabilidade de atraso devido a transito (5%)
                if random.random() < 0.05:
                    delay = random.randint(1, 5)
                    print(f"{self.agent.name} is delayed by traffic for {delay} seconds.")
                    await asyncio.sleep(delay)
                else:
                    #se nao esta no destino, movimentar em direcao ao bin, evitando roadblocks
                    if (cx, cy) != (dx, dy):
                        if cx < dx and cx+1<self.agent.environment.size and (cx + 1, cy) not in self.agent.environment.roadblocks:
                            cx += 1
                        elif cx > dx and cx-1<self.agent.environment.size and (cx - 1, cy) not in self.agent.environment.roadblocks:
                            cx -= 1
                        elif cy < dy and cy+1<self.agent.environment.size and (cx, cy + 1) not in self.agent.environment.roadblocks:
                            cy += 1
                        elif cy > dy and cy-1<self.agent.environment.size and (cx, cy - 1) not in self.agent.environment.roadblocks:
                            cy -= 1
                        else:
                            print(f"{self.agent.name} encountered a roadblock at {(cx, cy)}; rerouting.")
                            return
                        #atualizar posicao e combustivel
                        self.agent.position = (cx, cy)
                        self.agent.gas -= 1
                        print(f"{self.agent.name} moving to {self.agent.position}")


            # quando chega ao destino (carrega lixo, respawn lixo, limpa alvo)
            if self.agent.position == self.agent.environment.central_depot:
                print(f"{self.agent.name} has reached the depot, unloading waste and refueling for 3 seconds")
                await asyncio.sleep(3)
                self.agent.current_load = 0
                self.agent.gas = 100

            #quando ha alvo
            if self.agent.target_bin:
                tx, ty = self.agent.target_bin.location
                cx, cy = self.agent.position
                #gera probabilidade de atraso devido a transito (5%)
                if random.random() < 0.05:
                    delay = random.randint(1, 5)
                    print(f"{self.agent.name} is delayed by traffic for {delay} seconds.")
                    await asyncio.sleep(delay)
                else:
                    #se nao esta no destino, movimentar em direcao ao bin, evitando roadblocks
                    if (cx, cy) != (tx, ty):
                        if cx < tx and cx+1<self.agent.environment.size and (cx + 1, cy) not in self.agent.environment.roadblocks:
                            cx += 1
                        elif cx > tx and cx-1<self.agent.environment.size and (cx - 1, cy) not in self.agent.environment.roadblocks:
                            cx -= 1
                        elif cy < ty and cy+1<self.agent.environment.size and (cx, cy + 1) not in self.agent.environment.roadblocks:
                            cy += 1
                        elif cy > ty and cy-1<self.agent.environment.size and (cx, cy - 1) not in self.agent.environment.roadblocks:
                            cy -= 1
                        else:
                            print(f"{self.agent.name} encountered a roadblock at {(cx, cy)}; rerouting.")
                            self.agent.environment.assigned_bins.discard(self.agent.target_bin)
                            self.agent.target_bin = None  # Unassign and let another truck handle it
                            return
                        #atualizar posicao e combustivel
                        self.agent.position = (cx, cy)
                        self.agent.gas -= 1
                        print(f"{self.agent.name} moving to {self.agent.position}")
                    #quando chega ao destino (carrega lixo, respawn lixo, limpa alvo)
                    elif (cx, cy) == (tx, ty):
                        print(f"{self.agent.name} collected waste from bin at {self.agent.target_bin.location}")
                        self.agent.current_load += self.agent.target_bin.waste_level
                        self.agent.target_bin.respawn()
                        self.agent.environment.assigned_bins.discard(self.agent.target_bin)
                        self.agent.target_bin = None


            await asyncio.sleep(1)


    #adiciona comportamento
    async def setup(self):
        self.add_behaviour(self.CollectWasteBehaviour())



#----------



#LIXO
class BinAgent:

    #inicia ambiente, localizacao, nivel de lixo
    def __init__(self, environment):
        self.environment = environment
        self.location = environment.random_position()
        self.waste_level = random.randint(75, 100)

    #gerar posicao valida
    def gen_valid_pos(self):
        position = self.environment.random_position()
        while position == self.environment.central_depot or position in self.environment.roadblocks or any(b.location==position for b in self.environment.bins):
            position=self.environment.random_position()
        return position

    #reiniciar lixo
    def respawn(self):
        self.location = self.gen_valid_pos()
        self.waste_level = random.randint(75, 100)
        print(f"Bin respawned at {self.location} with waste level {self.waste_level}%")



#----------



#MAIN
async def main(environment):

    num_trucks = 3
    num_bins = 5

    #cria camioes e ixos
    truck_agents = [TruckAgent(f"truck{i}@localhost", "truckpassword", environment) for i in range(num_trucks)]
    environment.bins = [BinAgent(environment) for _ in range(num_bins)]


    #comecar camioes
    for agent in truck_agents:
        await agent.start()


    #setup tkinter
    def start_tkinter():
        root = tk.Tk()
        root.title("Waste Collection Simulation")
        canvas = tk.Canvas(root, width=500, height=500)
        canvas.pack()


        #atualizacao do display
        def update_display(teste):
            canvas.delete("all")

            #desenha depot
            depot_x, depot_y = environment.central_depot
            canvas.create_rectangle(depot_x * 50, depot_y * 50, depot_x * 50 + 50, depot_y * 50 + 50, fill="red")
            canvas.create_text(depot_x * 50 + 25, depot_y * 50 + 25, text="Depot", fill="white")

            #desenha camioes
            for i, truck in enumerate(truck_agents):
                x, y = truck.position
                canvas.create_rectangle(x * 50, y * 50, x * 50 + 50, y * 50 + 50, fill="blue")
                canvas.create_text(x * 50 + 25, y * 50 + 25, text=f"T {i}\nL {truck.current_load}/{truck.capacity}\nG {truck.gas}", fill="white")

            #desenha lixos
            for i, b in enumerate(environment.bins):
                x, y = b.location
                if b.waste_level >= 75:
                    canvas.create_oval(x * 50 + 10, y * 50 + 10, x * 50 + 40, y * 50 + 40, fill="green")
                    canvas.create_text(x * 50 + 25, y * 50 + 25, text=f"B{i} ({b.waste_level}%)", fill="white")

            #desenha roadblocks
            for (rx, ry) in environment.roadblocks:
                canvas.create_rectangle(rx * 50 + 15, ry * 50 + 15, rx * 50 + 35, ry * 50 + 35, fill="black")

            root.after(10, update_display, "teste")

        root.after(10, update_display, "teste")
        root.mainloop()


    tk_thread = threading.Thread(target=start_tkinter)
    tk_thread.start()


    # Main loop to keep the environment updating roadblocks
    try:
        while True:
            await environment.generate_temporary_roadblocks()
            await asyncio.sleep(10)
    except KeyboardInterrupt:
        print("Stopping agents...")

    for agent in truck_agents:
        await agent.stop()



#----------



if __name__ == "__main__":
    asyncio.run(main(Environment()))
