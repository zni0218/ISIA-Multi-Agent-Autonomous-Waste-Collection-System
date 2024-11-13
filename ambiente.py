from imports import *

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