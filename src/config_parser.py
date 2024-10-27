class Config_Parser:

    # Faz a leitura de topologia.txt
    @staticmethod
    def read_topology(file_path):
        topology = {}
        with open(file_path, 'r') as f:
            for line in f:
                # Atualiza o separador para ':' entre o nó e a lista de vizinhos
                parts = line.strip().split(':', maxsplit=1)
                if len(parts) < 2:
                    continue  # Skip lines without neighbors
                try:
                    node = int(parts[0].strip())  # Converte o identificador do nó em inteiro
                    # Divide os vizinhos por vírgula e filtra strings vazias
                    neighbors = [int(neighbor.strip()) for neighbor in parts[1].split(',') if neighbor]
                    topology[node] = neighbors
                except ValueError:
                    print(f"Erro ao interpretar a linha: {line.strip()} - Esta linha será ignorada.")
                    continue
        return topology


    # Faz a leitura de config.txt
    @staticmethod
    def read_config(file_path):
        config = {}
        with open(file_path, 'r') as f:
            for line in f:
                # Ajuste para usar ':' como separador entre o nó e suas configurações
                parts = line.strip().split(':', maxsplit=1)
                if len(parts) < 2:
                    continue  # Ignora linhas que não estejam corretamente formatadas
                try:
                    node = int(parts[0].strip())  # Primeiro elemento é o ID do nó
                    ip, port, capacity = parts[1].split(',')  # Divide IP, porta e capacidade
                    config[node] = {
                        'ip': ip.strip(),
                        'udp_port': int(port.strip()),
                        'capacity': int(capacity.strip())
                    }
                except ValueError:
                    print(f"Erro ao interpretar a linha: {line.strip()} - Esta linha será ignorada.")
                    continue
        return config
    

    # Faz a leitura de <metadata>.p2p 
    @staticmethod
    def read_metadata(file_path):
        try:
            with open(file_path, 'r') as f:
                lines = f.readlines()

            # Verifica se há pelo menos 4 linhas para a entrada de metadados
            if len(lines) < 4:
                raise ValueError("Arquivo de metadados incompleto")

            file_name = lines[0].strip()
            total_chunks = int(lines[1].strip())
            ttl = int(lines[2].strip())
            node_request = int(lines[3].strip())

            # Retorna o dicionário com apenas um conjunto de metadados
            metadata = {
                'file_name': file_name,
                'total_chunks': total_chunks,
                'ttl': ttl,
                'node_request': node_request
            }

            return metadata

        except (IndexError, ValueError) as e:
                raise RuntimeError(f"Erro ao interpretar o arquivo de metadados: {e}.")
