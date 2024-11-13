from imports import *
from ambiente import Environment
from camiao import TruckAgent
from lixo import BinAgent



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
