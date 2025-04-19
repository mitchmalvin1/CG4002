import asyncio
import json
import base64
from Crypto import Random
from Crypto.Cipher import AES
from Crypto.Util.Padding import pad
from utils.logger import CustomLogger


CLIENT_PASSWORD = "1234567890123456"
VERIFY_HANDSHAKE_PHRASE = "hello"

class EvalClient:
    def __init__(self, 
        target_ip, 
        target_port,
        game_engine_eval_queue,
        eval_game_engine_queue
    ):
        self.target_ip = target_ip
        self.target_port = target_port
        self.game_engine_eval_queue = game_engine_eval_queue
        self.eval_game_engine_queue = eval_game_engine_queue
        self.logger = CustomLogger(self.__class__.__name__).get_logger()

        self.reader = None
        self.writer = None
    
    async def tcp_connect(self):
        self.reader, self.writer = await asyncio.wait_for(
                asyncio.open_connection(self.target_ip, self.target_port),
                timeout= 5
        )
        print("successfully connected to eval server")
      
    def aes_encrypt_encode(self, data):
        iv = Random.new().read(AES.block_size)
        cipher = AES.new(CLIENT_PASSWORD.encode(), AES.MODE_CBC, iv)
        encoded = base64.b64encode(iv + cipher.encrypt(pad(data.encode(), AES.block_size)))
        return encoded

    async def send_message(self, message):
        encrypted_message = self.aes_encrypt_encode(message)
        formatted_message = (str(len(encrypted_message)) + "_").encode() + encrypted_message
        print(formatted_message)
        self.writer.write(formatted_message)
        await self.writer.drain()

    async def read_exact_bytes(self, num_bytes: int, timeout=3):
        """Reads exactly num_bytes from the reader with a timeout."""
        data = b""
        while len(data) < num_bytes:
            chunk = await asyncio.wait_for(self.reader.read(num_bytes - len(data)), timeout)
            if not chunk:
                raise ConnectionError("Eval Server disconnected while reading.")
            data += chunk
        return data

    async def recv_message(self):
        length_data = b""
        while not length_data.endswith(b"_"):
            # chunk = await self.reader.read(1)
            chunk = await asyncio.wait_for(self.reader.read(1), timeout=3)
            # self.logger.info("Received first byte:", chunk.decode())
            length_data += chunk
            # try:
            #     chunk = await asyncio.wait_for(self.reader.read(1), timeout=1)
            #     self.logger.info("Received first byte:", data.decode())
            #     length_data += chunk
            # except asyncio.TimeoutError:
            #     self.logger.info("Eval server timed out")
            #     return None
           
            # if not chunk:
            #     raise ConnectionError("Eval Server disconnected while reading prefix.")

        length_data = length_data.decode("utf-8")
        message_length = int(length_data[:-1])
        print(f"len(data) expected in bytes : {message_length}, {length_data}")
        message_data = await self.read_exact_bytes(message_length)

        message = message_data.decode("utf-8")
        return message
        
    async def initialize_handshake(self):
        await self.tcp_connect() 
        print("successfully connected")
        await self.send_message(VERIFY_HANDSHAKE_PHRASE) 

    async def run(self):
        try:
            await self.initialize_handshake()
            print(f"Connected to {self.target_ip}:{self.target_port}")

            self.logger.info("Handshake with eval_server established")
        except asyncio.TimeoutError :
            print(f"Eval server timed out")
            return
        except ConnectionRefusedError:
            print(f"Connection to {self.target_ip}:{self.target_port} was refused (eval server not listening).")
            return
        except OSError as e:
            print(f"Failed to connect to {self.target_ip}:{self.target_port}: {e}")
            return
        except Exception as e:
            print(f"Failed to connect to {self.target_ip}:{self.target_port}: {e}")
            return

        while True:
            game_state = await self.game_engine_eval_queue.get()
            self.logger.info(f"Fetched from game engine queue : \n  {json.dumps(json.loads(game_state), indent=4)} ")
         
            try :
                await self.send_message(game_state)
                self.logger.info("Message has been sent to eval_servr")
                eval_resp = await self.recv_message() 
            except asyncio.TimeoutError :
                self.logger.info("eval server timed out")
                continue
            except Exception:
                self.logger.info("eval server exception")
                continue
            self.logger.info(f"Received msg from eval_server : \n {json.dumps(json.loads(eval_resp), indent=4)} ")
            if eval_resp is not None :
                await self.eval_game_engine_queue.put(json.loads(eval_resp))
            else :
                await self.eval_game_engine_queue.put("")
      

async def evaluate_worker(
    game_engine_eval_queue : asyncio.Queue,
    eval_game_engine_queue : asyncio.Queue,
    host,
    port
):
    eval_client = EvalClient(
        host, 
        port,
        game_engine_eval_queue,
        eval_game_engine_queue
    )


    await eval_client.run()

        







    

