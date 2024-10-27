
import multiprocessing
import sys
from src.config_parser import Config_Parser
from src.peer_node import Peer_Node

def main():
    print("""
                                222222222222222                        
                                2:::::::::::::::22                      
                                2::::::222222:::::2                     
                                2222222     2:::::2                     
            ppppp   ppppppppp               2:::::2 ppppp   ppppppppp   
            p::::ppp:::::::::p              2:::::2 p::::ppp:::::::::p  
            p:::::::::::::::::p          2222::::2  p:::::::::::::::::p 
            pp::::::ppppp::::::p    22222::::::22   pp::::::ppppp::::::p
            p:::::p     p:::::p  22::::::::222      p:::::p     p:::::p
            p:::::p     p:::::p 2:::::22222         p:::::p     p:::::p
            p:::::p     p:::::p2:::::2              p:::::p     p:::::p
            p:::::p    p::::::p2:::::2              p:::::p    p::::::p
            p:::::ppppp:::::::p2:::::2       222222 p:::::ppppp:::::::p
            p::::::::::::::::p 2::::::2222222:::::2 p::::::::::::::::p 
            p::::::::::::::pp  2::::::::::::::::::2 p::::::::::::::pp  
            p::::::pppppppp    22222222222222222222 p::::::pppppppp    
            p:::::p                                 p:::::p            
            p:::::p                                 p:::::p            
            p:::::::p                               p:::::::p           
            p:::::::p                               p:::::::p           
            p:::::::p                               p:::::::p           
            ppppppppp                               ppppppppp           
        """)
    
    topology = Config_Parser.read_topology('topologia.txt')
    config = Config_Parser.read_config('config.txt')
    metadata = Config_Parser.read_metadata(sys.argv[1])

    # Criando N processos para cada peer
    processes = []
    for node_id in config:
        # Criando um processo para cada nodo
        p = multiprocessing.Process(target=Peer_Node.peer_node, args=(node_id, config, topology, metadata))
        processes.append(p)
        p.start()
    
    # Esperando que todos os processos terminem
    for p in processes:
        p.join()
        
    print("Todos os processos foram finalizados.")

if __name__ == "__main__":
    main()
