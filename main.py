
import multiprocessing
from config_parser import Config_Parser
from peer_node import Peer_Node

def main():
    topology = Config_Parser.read_topology('configs/topologia.txt')
    config = Config_Parser.read_config('configs/config.txt')
    
    # Criando N processos para cada peer
    processes = []
    for node_id in config:
        # Criando um processo para cada nodo
        p = multiprocessing.Process(target=Peer_Node.peer_node, args=(node_id, config, topology))
        processes.append(p)
        p.start()
    
    # Esperando que todos os processos terminem
    for p in processes:
        p.join()
        
    print("Todos os processos foram finalizados.")

if __name__ == "__main__":
    main()
