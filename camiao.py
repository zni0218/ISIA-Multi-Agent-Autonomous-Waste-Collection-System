from imports import *
from distancia import manhattan_distance

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