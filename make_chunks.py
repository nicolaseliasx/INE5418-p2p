import os
import re

def prepare_peer_files(peer_dirs):
    """
    Verifica e divide arquivos em chunks para cada peer e registra o número de chunks de cada arquivo.
    :param peer_dirs: Dicionário com ID dos peers e seus diretórios de arquivos.
    :return: Dicionário com o número de chunks para cada arquivo.
    """
    file_chunks_count = {}  # Dicionário para armazenar o número de chunks para cada arquivo

    for node_id, directory in peer_dirs.items():
        # Garante que o diretório do peer exista
        os.makedirs(directory, exist_ok=True)

        # Verifica e divide cada arquivo presente no diretório do peer
        for file_name in os.listdir(directory):
            file_path = os.path.join(directory, file_name)
            
            # Verifica se é um arquivo regular e não um diretório de chunks
            if os.path.isfile(file_path) and not file_name.endswith("_chunks"):
                total_chunks = split_file(file_path)  # Divide o arquivo em chunks
                file_chunks_count[file_name] = total_chunks  # Armazena o total de chunks para o arquivo

    return file_chunks_count  # Retorna o dicionário com a contagem de chunks para cada arquivo


def split_file(file_path, chunk_size=1024 * 1024):  # Por padrão, tamanho de 1 MB
    """
    Divide um arquivo em chunks de tamanho fixo.
    :param file_path: Caminho do arquivo original a ser dividido.
    :param chunk_size: Tamanho de cada chunk em bytes.
    :return: Número total de chunks gerados.
    """
    file_name = os.path.basename(file_path)  # Nome do arquivo sem o caminho
    file_dir = os.path.dirname(file_path)  # Diretório do arquivo

    # Abre o arquivo original para leitura
    with open(file_path, 'rb') as file:
        chunk_id = 0
        while True:
            # Lê o próximo pedaço do arquivo
            chunk_data = file.read(chunk_size)
            if not chunk_data:
                break  # Fim do arquivo

            # Salva o chunk diretamente na raiz do diretório do peer
            chunk_path = os.path.join(file_dir, f"{file_name}.ch{chunk_id}")
            with open(chunk_path, 'wb') as chunk_file:
                chunk_file.write(chunk_data)
            
            print(f"Chunk {chunk_id} criado em {chunk_path}")
            chunk_id += 1  # Incrementa o ID do chunk

    return chunk_id  # Retorna o total de chunks gerados

def delete_all_chunks(peer_dirs):
    """
    Deleta todos os chunks de arquivos em cada diretório de peers especificado.
    :param peer_dirs: Dicionário com os IDs dos peers e seus respectivos diretórios.
    """
    # Expressão regular para identificar arquivos de chunks (ex: .ch0, .ch1, etc.)
    chunk_pattern = re.compile(r'\.ch\d+$')

    for node_id, directory in peer_dirs.items():  # Certifique-se de usar apenas o directory
        # Garante que o diretório do peer exista
        if os.path.exists(directory):
            # Percorre todos os arquivos no diretório do peer
            for file_name in os.listdir(directory):
                # Verifica se o arquivo é um chunk pelo padrão .ch<numero>
                if chunk_pattern.search(file_name):
                    file_path = os.path.join(directory, file_name)
                    os.remove(file_path)  # Remove o chunk
