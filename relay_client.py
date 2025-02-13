import asyncio 
from constants.constants import DUMMY_RELAY_NODE_DATA_P1, DUMMY_RELAY_NODE_DATA_P2
import json

class AsyncTCPClient:
    def __init__(self, server_ip: str, server_port: int):
        self.server_ip = server_ip
        self.server_port = server_port
        self.reader = None
        self.writer = None

    async def connect(self):
        self.reader, self.writer = await asyncio.open_connection(self.server_ip, self.server_port)
        print(f"Connected to server at {self.server_ip}:{self.server_port}")

    async def send_message(self, message: str):
        if self.writer:
            formatted_msg =str(len(message)) + "_" + message
            self.writer.write(formatted_msg.encode())
            await self.writer.drain()
            print(f"Relay node sent message : {formatted_msg}")
    
    async def read_exact_bytes(self, num_bytes: int, timeout=60):
        """Reads exactly num_bytes from the reader with a timeout."""
        data = b""
        while len(data) < num_bytes:
            chunk = await asyncio.wait_for(self.reader.read(num_bytes - len(data)), timeout)
            if not chunk:
                raise ConnectionError("Client disconnected while reading.")
            data += chunk
        return data

    async def recv_message(self):
        length_data = b""
        while not length_data.endswith(b"_"):
            chunk = await self.reader.read(1)
            if not chunk:
                raise ConnectionError("Client disconnected while reading prefix.")
            length_data += chunk
        length_data = length_data.decode("utf-8")
        print(length_data)
        message_length = int(length_data[:-1])
        print(f"len(data) expected in bytes : {message_length}, {length_data}")
        message_data = await self.read_exact_bytes(message_length)

        message = message_data.decode("utf-8")
        return message

    async def receive_message(self) -> str:
        if self.reader:
            response = await self.recv_message()
            print(f"Received: {response}")
            return response
        return ""

    async def close(self):
        if self.writer:
            self.writer.close()
            await self.writer.wait_closed()
            print("Connection closed")

async def initialize_tcp_client_socket():
    client = AsyncTCPClient("172.26.190.97", 12345)
    is_p1 = True
    await client.connect()
    while True :
        user_input = await asyncio.to_thread(input, "Enter any key to send a random packet: ")
        data = DUMMY_RELAY_NODE_DATA_P1 if is_p1 else DUMMY_RELAY_NODE_DATA_P2
        await client.send_message(json.dumps(data))
        response = await client.receive_message()
        is_p1 = not is_p1
    await client.close()

if __name__ == "__main__":
    asyncio.run(initialize_tcp_client_socket())
