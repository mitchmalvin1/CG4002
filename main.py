from evaluation_worker import evaluate_worker
from relay_worker import relay_worker
from game_worker import game_worker
from game_worker_free import game_worker_free
from visualizer_worker import visualizer_worker
import asyncio
import socket
import threading
import sys
import os

sys.path.append(os.path.abspath("/home/xilinx/"))
from Neural_network_accel.pl_accelerator import FPGAAcceleratedNN

async def main():
    game_engine_eval_queue = asyncio.Queue()
    eval_game_engine_queue = asyncio.Queue()
    data_to_ai_queue = asyncio.Queue()
    p1_data_from_ai_queue = asyncio.Queue()
    p2_data_from_ai_queue = asyncio.Queue()
    p1_action_queue = asyncio.Queue()
    p2_action_queue = asyncio.Queue()
    p1_get_shot_queue = asyncio.Queue()
    p2_get_shot_queue = asyncio.Queue()
    data_from_relay_nodes_queue = asyncio.Queue()
    data_to_relay_nodes_queue = asyncio.Queue()
    data_from_visualizer_queue = asyncio.Queue()
    data_to_visualizer_queue = asyncio.Queue()
    data_from_ai_queue = asyncio.Queue()
    data_to_ai_queue = asyncio.Queue()


    def get_local_ip():
        try:
            # Create a temporary connection to an external address to get the machine's local IP
            # Google DNS (8.8.8.8) is a good candidate as it's always reachable
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            sock.connect(("8.8.8.8", 80))
            ip_address = sock.getsockname()[0]
            sock.close()
            print(f"Local ip address for TCP Socket Server : {ip_address}")
            return ip_address
        except Exception as e:
            return f"Error obtaining local IP: {str(e)}"

    EVAL_CLIENT_HOST = "127.0.0.1"
    EVAL_CLIENT_PORT = 8888
    TCP_SERVER_RELAY_HOST = get_local_ip()
    TCP_SERVER_RELAY_PORT = 12345
    MQTT_BROKER_HOST = "test.mosquitto.org"
    MQTT_BROKER_PORT = 1883

    evaluate_task = asyncio.create_task(evaluate_worker(
        game_engine_eval_queue,
        eval_game_engine_queue,
        EVAL_CLIENT_HOST,
        EVAL_CLIENT_PORT
    ))

    relay_task = asyncio.create_task(relay_worker(
        TCP_SERVER_RELAY_HOST,
        TCP_SERVER_RELAY_PORT,
        data_to_ai_queue,
        p1_data_from_ai_queue,
        p2_data_from_ai_queue,
        p1_action_queue,
        p2_action_queue,
        p1_get_shot_queue,
        p2_get_shot_queue,
        data_from_relay_nodes_queue,
        data_to_relay_nodes_queue,
    ))

    game_task = asyncio.create_task(game_worker(
        data_from_visualizer_queue,
        data_to_visualizer_queue,
        data_from_relay_nodes_queue,
        data_to_relay_nodes_queue,
        game_engine_eval_queue,
        eval_game_engine_queue
    ))

    # game_task_free = asyncio.create_task(game_worker_free(
    #     data_from_visualizer_queue,
    #     data_to_visualizer_queue,
    #     data_from_relay_nodes_queue,
    #     data_to_relay_nodes_queue,
    # ))

    visualizer_task = asyncio.create_task(visualizer_worker(
        data_from_visualizer_queue,
        data_to_visualizer_queue,
        MQTT_BROKER_HOST,
        MQTT_BROKER_PORT
    ))

 

    await asyncio.gather(evaluate_task, relay_task, game_task, visualizer_task)
    # await asyncio.gather(evaluate_task, relay_task, game_task)
    

### --- Run the Process and Event Loop --- ###
if __name__ == "__main__":
    # Start CPU-intensive task in a separate process
    # cpu_process = multiprocessing.Process(target=ai_process)
    # cpu_process.start()

    # Start asyncio event loop for I/O tasks
    asyncio.run(main())

    # Ensure CPU process finishes
    # cpu_process.join()