from asyncio import Queue, StreamReader, StreamWriter, start_server, CancelledError, wait_for
from constants.enums import Action
from utils.logger import CustomLogger
import json

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
        data_to_relay_nodes_queue: Queue
    ):
        self.host = host
        self.port = port
        self.data_to_ai_queue = data_to_ai_queue
        self.p1_data_from_ai_queue = p1_data_from_ai_queue
        self.p1_data_from_ai_queue = p2_data_from_ai_queue
        self.p1_action_queue = p1_action_queue
        self.p2_action_queue = p2_action_queue
        self.p1_get_shot_queue = p1_get_shot_queue
        self.p2_get_shot_queue = p2_get_shot_queue
        self.data_to_relay_nodes_queue = data_to_relay_nodes_queue
        self.logger = CustomLogger(self.__class__.__name__).get_logger()
        self.server = None  # Placeholder for the server instance
    
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

    async def recv_message(self, reader: StreamReader):
        length_data = b""
        while not length_data.endswith(b"_"):
            chunk = await reader.read(1)
            if not chunk:
                raise ConnectionError("Relay Client disconnected while reading length prefix.")
            length_data += chunk
        length_data = length_data.decode("utf-8")
        message_length = int(length_data[:-1])
        print(f"len(data) expected in bytes : {message_length}, {length_data}")
        message_data = await self.read_exact_bytes(reader, message_length)

        message = message_data.decode("utf-8")
        return message

    async def handle_client(self, reader: StreamReader, writer: StreamWriter):
        """Handles a single client connection asynchronously."""
        addr = writer.get_extra_info('peername')
        self.logger.info(f"Connected by {addr}")

        try:
            while True:
                data = await self.recv_message(reader)
                print(data)
                received_dict = json.loads(data)
                self.logger.info(f"Received from Relay Node client:\n {json.dumps(received_dict, indent=4)}")
               

                #feed to ai then get the predicted_action, then send to eval
                #action = get_prediction_from_ai
                action = Action.random_action()
                self.logger.info(f"Predicted AI action (random for now): {action}")

                if received_dict['player_id'] == 1 :
                    await self.p1_action_queue.put(action) 
                else :
                    await self.p2_action_queue.put(action)

                corrected_game_state = await self.data_to_relay_nodes_queue.get()
                await self.send_message(writer,corrected_game_state)

        except Exception as e:
            self.logger.info(f"Exception occured when handling connection from relay node : {e}")
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
        data_to_relay_nodes_queue
    )
    await server.start()