import socket
import logging
import sys
import time

class Client:
    def __init__(self, ip):
        # create logger with
        self.logger = logging.getLogger('vr client')
        self.logger.setLevel(logging.INFO)
        # create file handler which logs even debug messages
        self.file_logger = logging.FileHandler('client.log', mode='w')
        self.file_logger.setLevel(logging.INFO)
        # create console handler with a higher log level
        self.console_logger = logging.StreamHandler(sys.stdout)
        self.console_logger.setLevel(logging.INFO)
        # create formatter and add it to the handlers
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        self.file_logger.setFormatter(formatter)
        self.console_logger.setFormatter(formatter)
        # add the handlers to the logger
        #self.logger.addHandler(self.file_logger)
        self.logger.addHandler(self.console_logger)

        self.break_character = '*'
        self.socket = None
        self.remote = ip
        self.port = 9999
        self.buffer = 1024

    def connect(self):
        self.logger.info('Connecting')
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server_address = (self.remote, self.port)
        self.socket.connect(server_address)
        self.logger.info('Connected')

    def send(self, msg):
        msg = msg.rstrip(self.break_character)
        msg = msg + self.break_character
        self.socket.sendall(msg.encode())
        received = self.receive()
        return received

    def receive(self):
        data = ''
        while 1:
            packet = self.socket.recv(self.buffer)
            if not packet: break
            data += packet.decode()
            data = data.rstrip('\n')
            if data.endswith(self.break_character): break
        data = data.rstrip(self.break_character + '\n')
        return data

    def get_coordinates(self, to_list=True):
        coordinates = []
        data = self.send('cds')
        data = data.rstrip(' ')
        if not to_list: return data
        for x in range(10): data = data.replace('  ', ' ')
        data = data.split(' ')
        for x in data:
            try:
                n = float(x)
                coordinates.append(n)
            except:
                coordinates.append(x)
        return coordinates

    def disconnect(self):
        self.socket.close()

    def __del__(self):
        self.disconnect()


if __name__ == "__main__":
    c = Client('192.168.1.6')
    c.connect()
    while 1:
        received = c.get_coordinates()
        print(received)
        time.sleep(1)
