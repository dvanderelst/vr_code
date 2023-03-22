import tkinter as tk
import socket
import threading
import time
import tkinter.filedialog
from tkinter import S, N, W, E, END
from os.path import expanduser

import easygui
import traceback

import VrClient
import triad_openvr

def str2list(txt):
    lst = []
    txt = txt.rstrip(' ')
    parts = txt.split('  ')
    print(parts)
    for x in parts: lst.append(float(x))
    return lst

def list2str(lst):
    txt = ''
    for x in lst: txt += str(x) + '  '
    #txt = txt.rstrip(' ')
    return txt

def remap_coordinates(coordinates):
    x = coordinates[0]
    y = coordinates[1]
    z = coordinates[2]
    rot1 = coordinates[3]
    rot2 = coordinates[4]
    rot3 = coordinates[5]
    new_x = z
    new_y = x
    new_z = y
    new_yaw = -rot2
    new_pitch = (-rot3) + 90
    new_roll = -rot1
    return new_x, new_y, new_z, new_yaw, new_pitch, new_roll

# class StdoutRedirector:
#     def __init__(self, text_widget):
#         self.text_space = text_widget
#
#     def write(self, string):
#         self.text_space.insert('end', string)
#         self.text_space.see('end')

class VirtualRealitySystem:
    def __init__(self, dummy=False):
        self.dummy = dummy
        if not dummy: self.vr_system = triad_openvr.triad_openvr()

    def get_data(self):
        msg = ''
        if self.dummy: return 'x y z yaw pitch roll'
        #print(self.vr_system.devices)
        for i in self.vr_system.devices["tracker_1"].get_pose_euler(): msg += "%.3f " % i + " "
        msg.rstrip()
        return msg


class VirtualRealityServer:
    def __init__(self, port=9999, dummy=True):
        self.buffer = 1024
        self.break_character = '*'
        self.port = port
        self.dummy_vr = dummy
        self.vr = VirtualRealitySystem(dummy=dummy)
        self.socket = None

        # Open single socket
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        # '' means accept connections from any device
        self.socket.bind(('', self.port))
        self.socket.listen(5)

    def send(self, data, connection):
        data = data + self.break_character
        connection.send(data.encode())

    def receive(self, connection):
        data = ''
        counter = 0
        while 1:
            packet = connection.recv(self.buffer)
            data += packet.decode()
            if data.endswith(self.break_character): break
            counter = counter + 1
        data = data.rstrip(self.break_character + '\n')
        return data

    def disconnect(self):
        self.stop = True
        self.socket.close()

    def connect_and_serve(self, connection_id):
        # Wait for connection with blocking call
        connection, address = self.socket.accept()
        while 1:
            print('Listening on connection', connection_id, 'connected with ' + address[0] + ':' + str(address[1]))
            data = self.receive(connection)
            print('Connection', connection_id, 'data received:', data)
            
            if 'cds' in data:
                coordinates = self.vr.get_data()
                coordinates = str2list(coordinates)
                coordinates = remap_coordinates(coordinates)
                coordinates = list2str(coordinates)
                self.send(coordinates, connection)
                print(time.asctime(), 'Connection', str(connection_id), 'Data sent')
            
            if 'close' in data:
                print('Closing connection', connection_id)
                connection.close()
                self.start_single_thread(connection_id)
                print('Opened connection', connection_id)
                return
            
    def start_single_thread(self, connection_id):
        t = threading.Thread(target=self.connect_and_serve, args=[connection_id])
        t.daemon = True
        t.start()

    def start(self):
        for x in range(5):
            time.sleep(0.1)
            self.start_single_thread(x)
        print('Opened', x + 1, 'Connections. Waiting.')


class HelloApp:
    def __init__(self, master, dummy):
        # Define widgets
        self.master = master
        self.output = tk.Text(width=100)
        self.marked = tk.Text(width=100)
        self.get_button = tk.Button(master, text="Get Data")
        self.mark_obstacle = tk.Button(master, text="Mark Obstacle")
        self.mark_arena = tk.Button(master, text="Mark Arena")
        self.save = tk.Button(master, text="Save")

        # sys.stdout = StdoutRedirector(self.output)

        # Connect to server and all that
        self.server = VirtualRealityServer(dummy=dummy)
        self.server.start()
        self.server_port = self.server.port

        # internal connection, used to get data using the button
        self.internal_client = None

        # Add the widgets to their parents
        self.output.grid(row=0, column=0, columnspan=2, sticky=E + W + S + N)
        self.marked.grid(row=0, column=2, columnspan=2, sticky=E + W + S + N)

        self.get_button.grid(row=1, column=0, sticky=W + E + S + N)

        self.mark_obstacle.grid(row=1, column=2, sticky=W + E + S)
        self.mark_arena.grid(row=1, column=3, sticky=W + E + S)
        self.save.grid(row=2, column=2, columnspan=2, sticky=W + E + S)

        self.get_button.bind('<ButtonPress>', self.on_data_button)
        self.mark_obstacle.bind('<ButtonPress>', self.on_mark_obstacle_button)
        self.mark_arena.bind('<ButtonPress>', self.on_mark_arena_button)
        self.save.bind('<ButtonPress>', self.on_save_button)

        self.master.protocol("WM_DELETE_WINDOW", self.on_closing)

        self.master.grid_rowconfigure(0, weight=1)
        self.master.grid_columnconfigure(0, weight=1)
        self.master.grid_columnconfigure(1, weight=1)
        self.master.grid_columnconfigure(2, weight=1)
        self.master.grid_columnconfigure(3, weight=1)

    def on_data_button(self, event):
        data = self.get_data_internal()
        msg = time.asctime() + ' ' + str(data) + '\n'
        self.output.insert(END, msg)

    def on_mark_obstacle_button(self, event):
        data = self.get_data_internal()
        msg = 'obstacle' + ' ' + str(data) + '\n'
        self.marked.insert(END, msg)

    def on_mark_arena_button(self, event):
        data = self.get_data_internal()
        msg = 'arena' + ' ' + str(data) + '\n'
        self.marked.insert(END, msg)

    def on_save_button(self, event):
        home = expanduser("~")
        filename = tkinter.filedialog.asksaveasfilename(initialdir=home)
        text = self.marked.get(1.0, END)
        f = open(filename, 'w')
        f.write(text)
        f.close()

    def on_closing(self):
        self.server.disconnect()
        if self.internal_client is not None: self.internal_client.disconnect()
        self.master.destroy()

    def get_data_internal(self):
        # Connect internally to the server to be able to get data using the button
        print('<<<Getting data through internal connection>>>')
        if self.internal_client is None:
            self.internal_client = VrClient.Client('localhost')
            self.internal_client.connect()
            time.sleep(0.1)
        data = self.internal_client.get_coordinates(to_list=False)
        return data


if __name__ == "__main__":
    dummy = None
    if dummy is None: dummy = easygui.ynbox(msg='Connect to vr system?', title='connect')
    dummy = not dummy
    root = tk.Tk()
    app = HelloApp(root, dummy)
    root.mainloop()
