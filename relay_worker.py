from asyncio import Queue, StreamReader, StreamWriter, start_server, CancelledError, wait_for, TimeoutError
from constants.enums import Action
from utils.logger import CustomLogger
import json
import csv
import time
import sys
import os
import threading
from pathlib import Path
from collections import deque
import pandas as pd
import numpy as np
from pathlib import Path


sys.path.append(os.path.abspath("/home/xilinx/"))
from Neural_network_accel.pl_accelerator import FPGAAcceleratedNN
from Neural_network_accel.imu_model import IMUModel
from test_dummy.test_csv import add_new_data, write_to_csv


class RelayServer:
    def __init__(
        self, 
        host: str,
        port: int,
        data_to_ai_queue: Queue,
        p1_data_from_ai_queue: Queue,
        p2_data_from_ai_queue: Queue,
        p1_action_queue: Queue,
        p2_action_queue: Queue,
        p1_get_shot_queue: Queue,
        p2_get_shot_queue: Queue,
        data_from_relay_nodes_queue: Queue,
        data_to_relay_nodes_queue: Queue
    ):
        self.host = host
        self.port = port
        self.curr_player = 1
        self.data_to_ai_queue = data_to_ai_queue
        self.p1_data_from_ai_queue = p1_data_from_ai_queue
        self.p1_data_from_ai_queue = p2_data_from_ai_queue
        self.p1_action_queue = p1_action_queue
        self.p2_action_queue = p2_action_queue
        self.p1_get_shot_queue = p1_get_shot_queue
        self.p2_get_shot_queue = p2_get_shot_queue
        self.data_from_relay_nodes_queue = data_from_relay_nodes_queue
        self.data_to_relay_nodes_queue = data_to_relay_nodes_queue
        self.logger = CustomLogger(self.__class__.__name__).get_logger()
        self.server = None  # Placeholder for the server instance
        self.model = IMUModel("/home/xilinx/jupyter_notebooks/plot_signals/model_32_16_8.weights.h5")
        self.mapping =  {
            -1 : "no_action",
            0 : Action.BOMB.value,
            1 : Action.SHIELD.value,
            2 : Action.BOXING.value,
            3 : Action.BADMINTON.value,
            4 : Action.FENCING.value,
            5 : Action.RELOAD.value,
            6 : Action.GOLF.value,
            7 : Action.LOGOUT.value,
        }
    
    async def send_message(self ,writer: StreamWriter, message: str):
        if writer:
            formatted_msg =str(len(message)) + "_" + message
            writer.write(formatted_msg.encode())
            await writer.drain()
            print(f"Relay worker sent message : {formatted_msg}")
    
    async def read_exact_bytes(self, reader: StreamReader, num_bytes: int, timeout=60):
        """Reads exactly num_bytes from the reader with a timeout."""
        data = b""
        while len(data) < num_bytes:
            chunk = await wait_for(reader.read(num_bytes - len(data)), timeout)
            if not chunk:
                raise ConnectionError("Relay Client disconnected while reading data.")
            data += chunk
        return data
    
    async def clear_reader(self,reader: StreamReader):
        try:
            while not reader.at_eof():
                chunk = await wait_for(reader.read(1024), timeout=0.1)  # Timeout added
                self.logger.info(f"{len(chunk)}  bytes of buffer cleared")
                if not chunk:
                    break
        except TimeoutError:
            print("Timeout while clearing reader buffer")

    def switch_player_turn(self):
        self.curr_player = 1 if self.curr_player == 2 else 2

    async def recv_message(self, reader: StreamReader):
        length_data = b""
        while not length_data.endswith(b"_"):
            chunk = await reader.read(1)
            if not chunk:
                raise ConnectionError("Relay Client disconnected while reading length prefix.")
            length_data += chunk
        length_data = length_data.decode("utf-8")
        message_length = int(length_data[:-1])
        # print(f"len(data) expected in bytes : {message_length}, {length_data}")
        message_data = await self.read_exact_bytes(reader, message_length)

        message = message_data.decode("utf-8")
        return message

    async def clear_relay_nodes_queue(self) :
        while not self.data_from_relay_nodes_queue.empty() :
            await self.data_from_relay_nodes_queue.get()

    async def handle_client(self, reader: StreamReader, writer: StreamWriter):
        """Handles a single client connection asynchronously."""
        addr = writer.get_extra_info('peername')
        self.logger.info(f"Connected by {addr}")
        imu_p1_buffer = []
        imu_p2_buffer = []
        is_p1_done = False
        is_p2_done = False
        try:
            while True:
                data = await self.recv_message(reader)
                received_dict = json.loads(data)
               
                # self.logger.info(f"Received from Relay Node client:\n {json.dumps(received_dict, indent=4)}")
                # print(received_dict["timestamp"])
                if (received_dict['player_id'] == 1) :
                    if(received_dict["type"] == "I") :
                        imu_p1_buffer.append(received_dict["values"][0])
                        
                    elif(received_dict["type"] == "S") :
                        self.logger.info(f"Received from Relay Node client:\n {json.dumps(received_dict, indent=4)}")
                        print(f"imu 1 buffer length : {len(imu_p1_buffer)}")
                        if len(imu_p1_buffer) > 50 :
                            imu_p1_buffer = imu_p1_buffer[-60:]
                            df = pd.DataFrame(imu_p1_buffer, columns=["Accel_X", "Accel_Y", "Accel_Z", "Gyro_X", "Gyro_Y", "Gyro_Z"])
                            predictions = self.model.predict(df)
                            # my_file = Path("one_data.csv")
                            # df2 = pd.read_csv("one_data.csv") if my_file.is_file() else pd.DataFrame()
                            # if 'Unnamed: 0' in df2.columns:
                            #     df2.drop(columns=["Unnamed: 0"], inplace=True)
                            #     df = pd.concat([df, df2])
                            # print(len(df))
                            # df.to_csv("one_data.csv") # comment/ remove later
                            imu_p1_buffer = []
                            print(predictions)
                            action = self.mapping[max(set(predictions), key = predictions.count)]
                            self.logger.info(f"whole predictions , action : {action}")
                            
                            await self.data_from_relay_nodes_queue.put(json.dumps(
                                {
                                    'player_id' : received_dict['player_id'],
                                    'predicted_action' : action
                                }
                            ))
                            corrected_game_state = await self.data_to_relay_nodes_queue.get()         
                            await self.send_message(writer, corrected_game_state)
                            # await self.clear_relay_nodes_queue()
                            # await self.clear_reader(reader)

                            if (is_p2_done) :
                                await self.clear_reader(reader)
                                self.logger.info("p2 was previously done and p1 is now done, clearing leftover data in socket")
                                is_p2_done = False
                                is_p1_done = False
                                continue
                            is_p1_done = True
                        else :
                            imu_p1_buffer = []
                    elif(received_dict['type'] == 'T') :
                        self.logger.info("received gun transmitter")
                        await self.data_from_relay_nodes_queue.put(json.dumps(
                            {
                                'player_id' : received_dict['player_id'],
                                'predicted_action' : Action.SHOOT.value
                            }
                        ))
                        corrected_game_state = await self.data_to_relay_nodes_queue.get()
                        await self.send_message(writer, corrected_game_state)
                        # await self.clear_relay_nodes_queue()
                        # await self.clear_reader(reader)
                        imu_p1_buffer = []
                        self.can_send_to_game_engine = True
                        continue

                elif (received_dict['player_id'] == 2) :
                    if(received_dict["type"] == "I") :
                        imu_p2_buffer.append(received_dict["values"][0])
                        
                    elif(received_dict["type"] == "S") :
                        self.logger.info(f"Received from Relay Node client:\n {json.dumps(received_dict, indent=4)}")
                        print(f"imu 2 buffer length : {len(imu_p2_buffer)}")
                        if len(imu_p2_buffer) > 50 :
                            imu_p2_buffer = imu_p2_buffer[-60:]
                            df = pd.DataFrame(imu_p2_buffer, columns=["Accel_X", "Accel_Y", "Accel_Z", "Gyro_X", "Gyro_Y", "Gyro_Z"])
                            predictions = self.model.predict(df)
                            # my_file = Path("one_data_p2.csv")
                            # df2 = pd.read_csv("one_data_p2.csv") if my_file.is_file() else pd.DataFrame()
                            # if 'Unnamed: 0' in df2.columns:
                            #     df2.drop(columns=["Unnamed: 0"], inplace=True)
                            #     df = pd.concat([df, df2])
                            # print(len(df))
                            # df.to_csv("one_data_p2.csv") # comment/ remove later
                            imu_p2_buffer = []
                            print(predictions)
                            action = self.mapping[max(set(predictions), key = predictions.count)]
                            self.logger.info(f"whole predictions , action : {action}")
                            
                            await self.data_from_relay_nodes_queue.put(json.dumps(
                                {
                                    'player_id' : received_dict['player_id'],
                                    'predicted_action' : action
                                }
                            ))
                            corrected_game_state = await self.data_to_relay_nodes_queue.get()          
                            await self.send_message(writer, corrected_game_state)
                            # await self.clear_relay_nodes_queue()
                            # await self.clear_reader(reader)
                            if (is_p1_done) :
                                await self.clear_reader(reader)
                                self.logger.info("p1 was previously done and p2 is now done, clearing leftover data in socket")
                                is_p1_done = False
                                is_p2_done = False
                                continue
                            is_p2_done = True
                        else :
                            imu_p2_buffer = []
                    elif(received_dict['type'] == 'T') :
                        self.logger.info("received gun transmitter")
                        await self.data_from_relay_nodes_queue.put(json.dumps(
                            {
                                'player_id' : received_dict['player_id'],
                                'predicted_action' : Action.SHOOT.value
                            }
                        ))
                        corrected_game_state = await self.data_to_relay_nodes_queue.get()
                        await self.send_message(writer, corrected_game_state)
                        # await self.clear_relay_nodes_queue()
                        # await self.clear_reader(reader)
                        imu_p2_buffer = []
                        self.can_send_to_game_engine = True
                        continue
    
        except Exception as e:
            self.logger.info(f"Exception occured when handling connection from relay node : {e}",exc_info=True)
        finally:
            writer.close()
            await writer.wait_closed()
            self.logger.info("Connection closed.")

    async def start(self):
        self.server = await start_server(self.handle_client, self.host, self.port)
        addr = self.server.sockets[0].getsockname()
        self.logger.info(f"TCP Server for Relay Node listening on {addr}")

        async with self.server:
            await self.server.serve_forever()  # Run the server indefinitely

async def relay_worker(
    host: int,
    port: int,
    data_to_ai: Queue,
    data_from_ai_p1: Queue,
    data_from_ai_p2: Queue,
    p1_action_queue: Queue,
    p2_action_queue: Queue,
    p1_get_shot_queue: Queue,
    p2_get_shot_queue: Queue,
    data_from_relay_nodes_queue: Queue,
    data_to_relay_nodes_queue: Queue,
):
    server = RelayServer(
        host,
        port,
        data_to_ai,
        data_from_ai_p1,
        data_from_ai_p2,
        p1_action_queue,
        p2_action_queue,
        p1_get_shot_queue,
        p2_get_shot_queue,
        data_from_relay_nodes_queue,
        data_to_relay_nodes_queue
    )
    threading.Thread(target=write_to_csv, daemon=True).start()
    await server.start() 