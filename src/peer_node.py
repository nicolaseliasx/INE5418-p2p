import json
import os
import socket
import threading
import time

class Peer_Node:

    @staticmethod
    def peer_node(node_id, config, topology, metadata):
        """
        Função que roda cada peer. Abre os sockets UDP e TCP e escuta por requisições.
        :param node_id: ID do nodo.
        :param config: Dicionário de configuração do nodo.
        :param topology: Dicionário de topologia indicando os vizinhos de cada nodo.
        """
        ip = config[node_id]['ip']
        udp_port = config[node_id]['udp_port']
        tcp_port = config[node_id]['udp_port']  # Usando a mesma porta para TCP
        capacity = config[node_id]['capacity']
        
        # Iniciando o socket UDP
        udp_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        udp_socket.bind((ip, udp_port))
        print(f"Peer {node_id} ouvindo requisições UDP na porta {udp_port}")

        # Iniciando o socket TCP para enviar e receber chunks
        tcp_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        tcp_socket.bind((ip, tcp_port))
        tcp_socket.listen(5)
        print(f"Peer {node_id} ouvindo requisições TCP para transferência de chunks na porta {tcp_port}")

        file_name = metadata['file_name']
        all_total_chunks = metadata['total_chunks']
        ttl = metadata['ttl']
        node_request = metadata['node_request'] # Nodo que solicitou o arquivo nova linha adicionada no arquivo de metadados

        chunks_available = {}  # Mapeia os chunks disponiveis e os peers que os possuem
        required_chunks = set(range(all_total_chunks))  # Conjunto dos IDs de chunks que faltam
        received_chunks = set()  # Conjunto dos chunks já recebidos

        # Variavel controle de logs de debugg
        debug = False

        visited_messages = set()  # Conjunto para armazenar mensagens já visitadas
        

        def receive_flooding():
            """
            Método principal para receber e processar mensagens de flooding.

            Este método escuta continuamente o socket UDP para receber mensagens de outros peers.
            Ele processa mensagens de busca (tipo 'search') e de resposta (tipo 'response'), 
            armazenando informações sobre os chunks disponíveis em outros peers.
            A mensagem é propagada para os vizinhos se o TTL for maior que zero.
            """
            while True:
                try:
                    data, addr = udp_socket.recvfrom(1024)
                    message = json.loads(data.decode())
                    if debug: print(f"DEBUG: Peer {node_id} recebeu mensagem UDP de {addr}: {message}")

                    message_id = f"{message['file_name']}-{message['tcp_port']}"
                    if message_id in visited_messages:
                        print(f"DEBUG: Mensagem '{message_id}' já processada por Peer {node_id}. Ignorando...")
                        continue

                    visited_messages.add(message_id)

                    # Verifica se é uma mensagem de busca
                    if message['type'] == 'search':
                        file_name = message['file_name']
                        available_chunks = [
                            i for i in range(all_total_chunks)
                            if os.path.exists(f"{node_id}/{file_name}.ch{i}")
                        ]
                        if debug: print(f"DEBUG: Peer {node_id} verificou chunks disponíveis: {available_chunks}")

                        # Se o peer possui algum chunk, envia uma resposta ao peer solicitante
                        if available_chunks:
                            response_message = {
                                'type': 'response',
                                'file_name': file_name,
                                'peer_ip': config[node_id]['ip'],
                                'tcp_port': config[node_id]['udp_port'],
                                'available_chunks': available_chunks
                            }
                            print(f"Peer {node_id} enviando resposta com chunks {available_chunks} para Peer {node_request}")
                            udp_socket.sendto(json.dumps(response_message).encode(), 
                                            (config[node_request]['ip'], config[node_request]['udp_port']))

                        # Propaga a mensagem se o TTL > 0
                        if message['ttl'] > 0:
                            if debug: print(f"DEBUG: TTL atual {message['ttl']} para mensagem '{message_id}'. Propagando...")
                            forward_message(node_id, topology, udp_socket, config, message, message_id)

                    # Trata a resposta somente se for o peer solicitante
                    elif message['type'] == 'response' and node_id == node_request:
                        file_name = message['file_name']
                        available_chunks = message['available_chunks']
                        if debug: print(f"DEBUG: Peer {node_id} (solicitante) recebeu resposta com chunks {available_chunks} do Peer {message['peer_ip']}")

                        # Atualiza `chunks_available` com os peers e chunks disponíveis
                        if file_name not in chunks_available:
                            chunks_available[file_name] = {}

                        for chunk_id in available_chunks:
                            if chunk_id not in chunks_available[file_name]:
                                chunks_available[file_name][chunk_id] = []
                            chunks_available[file_name][chunk_id].append({'peer_ip': message['peer_ip'], 'tcp_port': message['tcp_port']})

                        if debug:
                            chunks_found = set(chunks_available[file_name].keys())
                            print(f"DEBUG: Chunks encontrados até agora para '{file_name}': {chunks_found}. Ainda faltam: {required_chunks - chunks_found}")

                        # Se todos os chunks necessários foram encontrados, inicia a solicitação
                        if required_chunks.issubset(chunks_available[file_name].keys()):
                            print("Todos os chunks foram encontrados. Iniciando solicitação de chunks.")
                            request_chunks_sequentially(file_name, all_total_chunks)

                except Exception as e:
                    print(f"Erro no peer {node_id} ao receber UDP: {e}")


        def forward_message(node_id, topology, udp_socket, config, message, message_id):
            """
            Propaga uma mensagem para os vizinhos do peer atual, respeitando o TTL.

            Este método reduz o TTL da mensagem e a propaga para todos os vizinhos do peer atual
            se o TTL for maior que zero. Cada vizinho recebe uma cópia da mensagem via socket UDP,
            ajudando a disseminar a busca na rede.

            :param node_id: ID do peer atual que está propagando a mensagem.
            :param topology: Dicionário que mapeia cada peer aos seus vizinhos diretos.
            :param udp_socket: Socket UDP utilizado para enviar a mensagem aos vizinhos.
            :param config: Dicionário de configuração dos peers, contendo IPs e portas.
            :param message: Dicionário com os dados da mensagem a ser propagada, incluindo TTL.
            :param message_id: ID único da mensagem para controle de mensagens já processadas.
            """
            message['ttl'] -= 1
            if message['ttl'] <= 0:
                print(f"TTL expirado para a mensagem '{message_id}' em Peer {node_id}. Não será mais propagada.")
                return

            time.sleep(1)

            for neighbor in topology[node_id]:
                neighbor_ip = config[neighbor]['ip']
                neighbor_port = config[neighbor]['udp_port']
                udp_socket.sendto(json.dumps(message).encode(), (neighbor_ip, neighbor_port))
                print(f"Peer {node_id} enviou mensagem para Peer {neighbor}")


        def handle_tcp_connections():
            """
            Lida com conexões TCP recebidas para a transferência de chunks de arquivos.

            Este método espera e aceita conexões TCP de outros peers que estão solicitando chunks.
            Para cada conexão recebida, ele processa o pedido do chunk específico e chama a função 
            `send_chunk` para enviar o chunk solicitado ao peer solicitante.

            Conexão TCP estabelecida com o peer solicitante (fornecido automaticamente ao aceitar uma conexão).
            Endereço do peer solicitante (fornecido automaticamente ao aceitar uma conexão).
            """
            while True:
                conn, addr = tcp_socket.accept()
                print(f"Peer {node_id} aceitou conexão TCP de {addr}")
                
                # Receber o nome completo do chunk solicitado
                requested_chunk = conn.recv(1024).decode().strip()
                if requested_chunk:
                    print(f"Peer {node_id} recebeu pedido para o chunk: {requested_chunk}")
                    
                    # Enviar o chunk solicitado
                    send_chunk(conn, node_id, requested_chunk)
                else:
                    print(f"Erro: Nome do chunk recebido está vazio")


        def send_chunk(conn, node_id, chunk_name):
            """
            Envia um chunk de arquivo.
            :param conn: Conexão TCP.
            :param node_id: ID do peer.
            :param chunk_name: Nome do chunk a ser enviado.
            """
            chunk_path = f"{node_id}/{chunk_name}"  # Diretório com o ID do peer

            if debug: print(f"DEBUG: Peer {node_id} verificando a existência de {chunk_path}")
            if not os.path.exists(chunk_path):
                conn.send(b'CHUNK_NOT_FOUND')
                conn.close()
                return

            print(f"Peer {node_id} começou a enviar o chunk {chunk_name} para o peer solicitante.")

            total_size = os.path.getsize(chunk_path)  # Calcula o tamanho total do arquivo
            conn.send(f"{total_size}".encode()) # Envia o tamanho total do arquivo

            with open(chunk_path, 'rb') as f:
                while True:
                    data = f.read(capacity)
                    if not data:
                        break
                    conn.send(data)

            print(f"Peer {node_id} terminou de enviar o chunk {chunk_name}")
            conn.close()


        def receive_chunk(conn, node_id, file_name, chunk_id, total_chunks):
            """
            Recebe um chunk de arquivo via TCP e salva no diretório do peer.
            :param conn: Conexão TCP.
            :param node_id: ID do peer.
            :param file_name: Nome do arquivo que está sendo transferido.
            :param chunk_id: ID do chunk recebido.
            :param total_chunks: Total de chunks esperados para este arquivo.
            """
            directory = f"{node_id}/received_chunks"
            os.makedirs(directory, exist_ok=True)  # Cria o diretório, se necessário
            chunk_path = f"{directory}/{file_name}.ch{chunk_id}"

            # Recebe o tamanho total do chunk do remetente
            total_size = int(conn.recv(capacity).decode())
            total_received = 0  # Rastreia o número total de bytes recebidos

            print(f"Peer {node_id} começou a receber o chunk {chunk_id + 1}/{total_chunks} do arquivo '{file_name}'.")

            with open(chunk_path, 'wb') as f:
                while total_received < total_size:  # Continua até receber o tamanho total
                    data = conn.recv(capacity)
                    if not data:
                        break
                    f.write(data)
                    total_received += len(data)

                    # Calcula e exibe o progresso do chunk atual
                    progress = (total_received / total_size) * 100
                    print(f"Progresso: {progress:.2f}% ({total_received}/{total_size} bytes) recebidos")

            print(f"Peer {node_id} terminou de receber o chunk {chunk_id + 1}/{total_chunks} do arquivo '{file_name}' e o salvou em '{chunk_path}'.")
            conn.close()

        
        def request_chunks_sequentially(file_name, total_chunks):
            """
            Solicita os chunks de um arquivo de forma sequencial após todos os chunks terem sido localizados.

            Este método verifica os chunks que ainda não foram recebidos e solicita cada um deles
            ao peer que possui o chunk disponível, com base nas informações armazenadas em `chunks_available`.

            :param file_name: Nome do arquivo cujos chunks estão sendo solicitados.
            :param total_chunks: Número total de chunks que compõem o arquivo completo.
            """
            for chunk_id in sorted(required_chunks - received_chunks):
                peer_list = chunks_available[file_name].get(chunk_id, [])
                if peer_list:
                    selected_peer = peer_list[0]  # Seleciona o primeiro peer da lista
                    selected_peer_ip = selected_peer['peer_ip']
                    selected_peer_port = selected_peer['tcp_port']
                    print(f"Solicitando chunk {file_name}.ch{chunk_id} do peer {selected_peer_ip} na porta {selected_peer_port}")
                    request_chunk(selected_peer_ip, selected_peer_port, f"{file_name}.ch{chunk_id}", file_name, chunk_id, total_chunks)


        def request_chunk(peer_ip, peer_port, chunk_name, file_name, chunk_id, total_chunks):
            """
            Função para solicitar um chunk via TCP e recebê-lo.
            :param peer_ip: IP do peer que tem o chunk.
            :param peer_port: Porta TCP do peer que tem o chunk.
            :param chunk_name: Nome do chunk solicitado.
            :param file_name: Nome do arquivo principal.
            :param chunk_id: ID do chunk solicitado.
            :param total_chunks: Total de chunks esperados.
            """
            try:
                tcp_conn = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                tcp_conn.connect((peer_ip, peer_port))
                tcp_conn.sendall(chunk_name.encode())
                receive_chunk(tcp_conn, node_id, file_name, chunk_id, total_chunks)
                tcp_conn.close()

                received_chunks.add(chunk_id)  # Marca o chunk como recebido

                # Checa se todos os chunks foram recebidos para montar o arquivo
                if required_chunks == received_chunks:
                    concatenate_chunks(file_name, total_chunks, node_id)

            except Exception as e:
                print(f"Erro ao solicitar o chunk {chunk_name}: {e}")


        def concatenate_chunks(file_name, total_chunks, node_id):
            """
            Função para concatenar todos os chunks recebidos e formar o arquivo final.
            :param file_name: Nome do arquivo que está sendo montado.
            :param total_chunks: Total de chunks que foram recebidos.
            :param node_id: ID do nodo que armazena os chunks em seu diretório específico.
            """
            # Define o diretório final para o arquivo completo
            final_directory = f"{node_id}/received_files"
            os.makedirs(final_directory, exist_ok=True)  # Cria o diretório final, se necessário
            final_path = f"{final_directory}/{file_name}"

            # Abre o arquivo final e concatena os chunks
            with open(final_path, 'wb') as final_file:
                for chunk_id in range(total_chunks):
                    chunk_path = f"{node_id}/received_chunks/{file_name}.ch{chunk_id}"
                    with open(chunk_path, 'rb') as chunk_file:
                        final_file.write(chunk_file.read())

            print(f"Arquivo {file_name} montado com sucesso a partir dos {total_chunks} chunks.")
            print(f"FIM DA BUSCA: Arquivo {file_name} foi montado em {final_path}.")


        # Iniciando a thread para receber mensagens de flooding
        threading.Thread(target=receive_flooding).start()

        # Iniciando a thread para lidar com conexões TCP
        threading.Thread(target=handle_tcp_connections).start()

        # Mensagem inicial de busca, alterado o arquivo de metadados para ter mais uma linha informando qual nodo solicitou
        if node_id == node_request:
            message = {
                'type': 'search',
                'file_name': file_name,
                'ttl': ttl,
                'tcp_port': tcp_port,
            }
            message_id = f"{message['file_name']}-{message['tcp_port']}"
            forward_message(node_id, topology, udp_socket, config, message, message_id)
