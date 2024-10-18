# Parser for the configuration files
class Config_Parser:

    # Parser for the topologia.txt file
    @staticmethod
    def read_topology(file_path):
        topology = {}
        with open(file_path, 'r') as f:
            for line in f:
                parts = line.strip().split(maxsplit=1)
                if len(parts) < 2:
                    continue  # Skip lines without neighbors
                node = int(parts[0])
                # Ensure we filter out any empty strings from the neighbors list
                neighbors = [int(neighbor.strip()) for neighbor in parts[1].split(',') if neighbor]
                topology[node] = neighbors
        return topology

    # Parser for the config.txt file
    @staticmethod
    def read_config(file_path):
        config = {}
        with open(file_path, 'r') as f:
            for line in f:
                parts = line.strip().split(maxsplit=1)
                if len(parts) < 2:
                    # Skip lines that are not correctly formatted
                    continue
                try:
                    node = int(parts[0])  # First part is the node ID
                    ip, port, capacity = parts[1].split(',')  # Split IP, port and capacity
                    config[node] = {
                        'ip': ip.strip(),
                        'udp_port': int(port.strip()),
                        'capacity': int(capacity.strip())
                    }
                except ValueError:
                    print(f"Error parsing line: {line.strip()} - Skipping this line.")
                    continue
        return config