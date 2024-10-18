import socket
import time
import threading
import json
import os

class Peer_Node:
    @staticmethod
    def peer_node(node_id, config, topology):
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

        def receive_flooding():
            while True:
                try:
                    data, addr = udp_socket.recvfrom(1024)  # Buffer de 1024 bytes
                    message = json.loads(data.decode())  # Converte de volta para dict
                    print(f"Peer {node_id} recebeu mensagem UDP de {addr}: {message}")
                    
                    if message['type'] == 'search':
                        # Continua com o flooding
                        file_name = message['file_name']
                        if os.path.exists(f"{node_id}/{file_name}"):
                            print(f"Peer {node_id} tem o arquivo '{file_name}', notificando o peer solicitante")
                            # Enviar uma resposta para o peer solicitante
                            response_message = {
                                'type': 'response',
                                'file_name': file_name,
                                'peer_ip': config[node_id]['ip'],  # IP deste peer que tem o arquivo
                                'tcp_port': config[node_id]['udp_port'],  # Porta TCP deste peer que tem o arquivo
                                'file_found': True
                            }
                            udp_socket.sendto(json.dumps(response_message).encode(), addr)  # Envia a resposta ao peer solicitante

                        elif message['ttl'] > 0:
                            print(f"Peer {node_id} processando busca de arquivo '{file_name}' com TTL {message['ttl']}")
                            # Reduz o TTL e reenvia a mensagem para os vizinhos
                            forward_message(node_id, topology, udp_socket, config, message)

                    elif message['type'] == 'response':
                        # Tratando a resposta quando o arquivo foi encontrado
                        print(f"Peer {node_id} recebeu resposta: O peer {message['peer_ip']} tem o arquivo '{message['file_name']}'")
                        
                        # Agora este peer vai solicitar o chunk via TCP
                        request_chunk(
                            peer_ip=message['peer_ip'],
                            peer_port=message['tcp_port'],
                            chunk_name=message['file_name'],
                            file_name=message['file_name'],
                            # AJUSTAR ESSES VALORES
                            chunk_id=0,  # Para simplificar, vamos usar 0 como ID de chunk
                            total_chunks=1  # Vamos considerar 1 chunk para simplificação
                        )

                except Exception as e:
                    print(f"Erro no peer {node_id} ao receber UDP: {e}")

        def forward_message(node_id, topology, udp_socket, config, message):
            """
            Reenvia a mensagem para os vizinhos com TTL decrementado.
            """
            if message['file_found']:
                print(f"Arquivo '{message['file_name']}' já foi encontrado. Não propagar mais.")
                return

            message['ttl'] -= 1  # Decrementa o TTL
            if message['ttl'] <= 0:
                return  # Não reenvia se o TTL for 0 ou negativo

            # Envia para cada vizinho após 1 segundo de atraso
            time.sleep(1)
            for neighbor in topology[node_id]:
                neighbor_ip = config[neighbor]['ip']
                neighbor_port = config[neighbor]['udp_port']
                udp_socket.sendto(json.dumps(message).encode(), (neighbor_ip, neighbor_port))
                print(f"Peer {node_id} enviou mensagem para Peer {neighbor}")

        def handle_tcp_connections():
            while True:
                conn, addr = tcp_socket.accept()
                print(f"Peer {node_id} aceitou conexão TCP de {addr}")
                
                # Receber o nome completo do chunk solicitado
                requested_chunk = conn.recv(1024).decode().strip()
                if requested_chunk:
                    print(f"Peer {node_id} recebeu pedido para o chunk: {requested_chunk}")
                    
                    # Enviar o chunk solicitado
                    send_chunk(conn, node_id, requested_chunk, capacity)
                else:
                    print(f"Erro: Nome do chunk recebido está vazio")

        def send_chunk(conn, node_id, chunk_name, capacity):
            """
            Envia um chunk de arquivo respeitando a capacidade do nodo.
            :param conn: Conexão TCP.
            :param node_id: ID do peer.
            :param chunk_name: Nome do chunk a ser enviado.
            :param capacity: Capacidade do peer em bytes por segundo.
            """
            chunk_path = f"{node_id}/{chunk_name}"  # Diretório com o ID do peer

            if not os.path.exists(chunk_path):
                conn.send(b'CHUNK_NOT_FOUND')
                conn.close()
                return
            
            print(f"Peer {node_id} começou a enviar o chunk {chunk_name} para o peer solicitante.")
            # Enviando o arquivo em pedaços respeitando a capacidade de envio (bytes/s)
            with open(chunk_path, 'rb') as f:
                while True:
                    data = f.read(capacity)  # Lê o número máximo de bytes permitido por segundo
                    if not data:
                        break  # Arquivo completamente enviado

                    conn.send(data)  # Envia os dados
                    time.sleep(1)  # Respeita a taxa de envio (espera 1 segundo antes do próximo envio)

            print(f"Peer {node_id} terminou de enviar o chunk {chunk_name}")
            conn.close()

        def receive_chunk(conn, file_name, chunk_id, total_chunks):
            """
            Função para receber um chunk via TCP e salvar no diretório do peer.
            :param conn: Conexão TCP.
            :param file_name: Nome do arquivo que está sendo transferido.
            :param chunk_id: O ID do chunk recebido.
            :param total_chunks: Total de chunks esperados para este arquivo.
            """
            chunk_path = f"received_chunks/{file_name}.ch{chunk_id}"  # Caminho para salvar o chunk
            with open(chunk_path, 'wb') as f:
                while True:
                    data = conn.recv(1024)  # Receber o chunk em pedaços
                    if not data:
                        break
                    f.write(data)
            
            print(f"Chunk {chunk_id + 1}/{total_chunks} do arquivo {file_name} recebido e salvo.")

        def concatenate_chunks(file_name, total_chunks):
            """
            Função para concatenar todos os chunks recebidos e formar o arquivo final.
            :param file_name: Nome do arquivo que está sendo montado.
            :param total_chunks: Total de chunks que foram recebidos.
            """
            final_path = f"{node_id}/received_files/{file_name}"  # Onde o arquivo final será salvo
            with open(final_path, 'wb') as final_file:
                for chunk_id in range(total_chunks):
                    chunk_path = f"received_chunks/{file_name}.ch{chunk_id}"
                    with open(chunk_path, 'rb') as chunk_file:
                        final_file.write(chunk_file.read())  # Adiciona o conteúdo do chunk ao arquivo final
            
            print(f"Arquivo {file_name} montado com sucesso a partir dos {total_chunks} chunks.")

        
        def print_transfer_progress(current_chunk, total_chunks):
            """
            Função para imprimir o progresso da transferência.
            :param current_chunk: O número atual de chunks recebidos.
            :param total_chunks: O total de chunks a serem recebidos.
            """
            progress = (current_chunk / total_chunks) * 100
            print(f"Progresso da transferência: {current_chunk}/{total_chunks} chunks recebidos ({progress:.2f}%)")


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
                # Estabelece a conexão TCP com o peer que tem o chunk
                tcp_conn = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                tcp_conn.connect((peer_ip, peer_port))
                print(f"Conexão TCP estabelecida com o peer {peer_ip}:{peer_port}")
                
                # Solicita o chunk enviando seu nome
                tcp_conn.sendall(chunk_name.encode())  # Envia o nome do chunk que está sendo solicitado
                print(f"Solicitando chunk {chunk_name} do arquivo {file_name}")
                
                # Agora, receber o chunk e salvar
                receive_chunk(tcp_conn, file_name, chunk_id, total_chunks)
                
                tcp_conn.close()
            except Exception as e:
                print(f"Erro ao solicitar o chunk {chunk_name}: {e}")

        def receive_chunk(conn, file_name, chunk_id, total_chunks):
            """
            Função para receber um chunk via TCP e salvar no diretório do peer.
            :param conn: Conexão TCP.
            :param file_name: Nome do arquivo que está sendo transferido.
            :param chunk_id: O ID do chunk recebido.
            :param total_chunks: Total de chunks esperados para este arquivo.
            """
            chunk_path = f"received_chunks/{file_name}.ch{chunk_id}"  # Caminho para salvar o chunk
            with open(chunk_path, 'wb') as f:
                while True:
                    data = conn.recv(1024)  # Receber o chunk em pedaços
                    if not data:
                        break
                    f.write(data)
            
            print(f"Chunk {chunk_id + 1}/{total_chunks} do arquivo {file_name} recebido e salvo.")



        # Iniciando a thread para receber mensagens de busca
        threading.Thread(target=receive_flooding).start()

        # Iniciando a thread para lidar com conexões TCP
        threading.Thread(target=handle_tcp_connections).start()

        # Simulação da busca de arquivo iniciada por este nodo
        # Apenas para teste, o peer 0 inicia a busca de um arquivo
        if node_id == 1:
            message = {
                'type': 'search',
                'file_name': 'file.txt',
                'ttl': 4,
                'tcp_port': tcp_port,
                'file_found': False
            }
            forward_message(node_id, topology, udp_socket, config, message)
