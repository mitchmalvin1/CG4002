import asyncio
from json import dumps, loads
import aiomqtt
# import asyncio_paho
from utils.logger import CustomLogger


class MqttClient:
    def __init__(
        self,
        data_from_visualizer_queue: asyncio.Queue,
        data_to_visualizer_queue: asyncio.Queue,
        host: str,
        port: int,
        client
    ):
        self.data_from_visualizer_queue = data_from_visualizer_queue
        self.data_to_visualizer_queue = data_to_visualizer_queue
        self.logger = CustomLogger(self.__class__.__name__).get_logger()
        self.host = host
        self.port = port
        self.client = client


    async def connect(self):
        """Connect to the MQTT broker asynchronously and start handling messages."""
        self.logger.info("Connecting to MQTT broker...")
        await self.client.asyncio_connect(self.host)
        self.logger.info(f"Sucessfully connected to MQTT Broker {self.host}:{self.port}")
        
      

    async def listen(self):
        async for message in self.client.messages:
            if message.topic.matches("response/visibilities"):
                    formatted_msg = loads(message.payload.decode())
                    self.logger.info(f"Received msg from visualizer with topic response/visibilities : \n{dumps(formatted_msg, indent = 4)} ")

                    await self.data_from_visualizer_queue.put(dumps(formatted_msg))

    async def publish(self):
        while True :
            data = loads(await self.data_to_visualizer_queue.get())
            self.logger.info(f"Received from to_visualizer queue : \n {dumps(data, indent=4)}")
            await self.client.publish(data["topic"], payload=dumps(data["data"]))
            self.logger.info(f"Successfully published to visualizer with topic {data['topic']}")

    async def start(self):
        """Start the MQTT client."""
        try:
            await self.client.subscribe("response/visibilities")
            self.logger.info("Successfully subscribed to topic response/visibilities")
            await self.client.publish("request/visibilities", payload="dummy")
            listen_task = asyncio.create_task(self.listen())
            publish_task = asyncio.create_task(self.publish())

            await asyncio.gather(listen_task,publish_task)
            
        except Exception as e:
            self.logger.error(f"MQTT connection error: {e}")
            await asyncio.sleep(5)  # Retry delay
            await self.start()  # Restart the connection


async def visualizer_worker(
    data_from_visualizer_queue: asyncio.Queue,
    data_to_visualizer_queue: asyncio.Queue,
    host: str,
    port: int,
):
    try:
        hostname = "localhost"
        async with aiomqtt.Client(hostname=hostname, port=1883) as client:
            mqtt_client = MqttClient(
                data_from_visualizer_queue,
                data_to_visualizer_queue,
                hostname,
                port,
                client
            )
            await mqtt_client.start()
    except aiomqtt.MqttError as e:
        print(f"[ERROR] MQTT error: {e}")
    except asyncio.CancelledError:
        print("[INFO] Task cancelled. Cleaning up...")
    except Exception as e:
        print(f"[ERROR] Unexpected error: {e}")
    finally:
        print("[INFO] visualizer_worker shutting down...")