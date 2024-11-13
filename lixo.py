from imports import *


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