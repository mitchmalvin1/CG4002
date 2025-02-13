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

    # async def handle_message(self, message):
    #     """Async function to handle incoming messages."""
    #     topic = message.topic.value
    #     payload = message.payload.decode()

    #     if topic == "M2MQTT_Unity/test":
    #         # Discard old messages
    #         while not self.data_from_visualizer_queue.empty():
    #             await self.data_from_visualizer_queue.get_nowait()
    #             self.data_from_visualizer_queue.task_done()

    #         # Log and add the new message
    #         self.logger.info(f"Received from visualizer: {payload}")
    #         await self.data_from_visualizer_queue.put(payload)

    # async def broadcast(self, client):
    #     """Broadcast data asynchronously."""
    #     data = loads(await self.data_to_visualizer_queue.get())
    #     if data["topic"] == "broadcast/new_action":
    #         await client.publish(data["topic"], dumps(data["payload"]))
    #         self.logger.info("Message broadcasted")

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
        data = loads(await self.data_to_visualizer_queue.get())
        self.logger.info(f"Received from to_visualizer queue : \n {dumps(data, indent=4)}")
        await self.client.publish(data["topic"], payload=dumps(data["payload"]))
        self.logger.info(f"Successfully published to visualizer with topic {data['topic']}")

    async def start(self):
        """Start the MQTT client."""
        try:
            await self.client.subscribe("response/visibilities")
            self.logger.info("Successfully subscribed to topic response/visibilities")
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
    """Initialize and run the MQTT client in an async environment."""
    async with aiomqtt.Client("test.mosquitto.org") as client:
        mqtt_client = MqttClient(
            data_from_visualizer_queue,
            data_to_visualizer_queue,
            host,
            port,
            client
        )
        await mqtt_client.start()
        # await client.subscribe("M2MQTT_Unity/test")
        # async for message in client.messages:
        #     print(message.payload)
    # async def on_connect_async(client, userdata, flags, result) :
    #     await client.asyncio_subscribe("M2MQTT_Unity/test")

    # async def on_message_async(client, userdata, msg):
    #     print("hmm")
    #     self.logger.info(f"Received from {msg.topic}: {str(msg.payload)}")

    # async with asyncio_paho.AsyncioPahoClient() as client:
    #     client.asyncio_listeners.add_on_connect(on_connect_async)
    #     client.asyncio_listeners.add_on_message(on_message_async)
    #     await client.asyncio_connect(host)
    # async with asyncio_paho.AsyncioPahoClient() as client:
    #     mqtt_client = MqttClient(
    #         data_from_visualizer_queue,
    #         data_to_visualizer_queue,
    #         host,
    #         port,
    #         client
    #     )

    #     await mqtt_client.start()

    #     client.asyncio_add_on_connect_listener(on_connect_async)
    #     await client.asyncio_connect(host,port)
    # mqtt_client = MqttClient(
    #     data_from_visualizer_queue,
    #     data_to_visualizer_queue,
    #     host,
    #     port,
    # )
    # await mqtt_client.start()
