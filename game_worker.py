from asyncio import Queue
from json import dumps, loads
from constants.constants import DUMMY_GAME_STATE
from utils.game_state import GameState
from utils.logger import CustomLogger

class GameEngine:
    def __init__(
        self,
        p1_action_queue: Queue,
        p2_action_queue: Queue,
        p1_get_shot_queue: Queue,
        p2_get_shot_queue: Queue,
        data_from_visualizer_queue: Queue,
        data_to_visualizer_queue: Queue,
        data_to_relay_nodes_queue: Queue,
        game_engine_eval_queue: Queue,
        eval_game_engine_queue: Queue,
    ):
        self.p1_action_queue = p1_action_queue
        self.p2_action_queue = p2_action_queue
        self.p1_get_shot_queue = p1_get_shot_queue
        self.p2_get_shot_queue = p2_get_shot_queue
        self.data_from_visualizer_queue = data_from_visualizer_queue
        self.data_to_visualizer_queue = data_to_visualizer_queue
        self.data_to_relay_nodes_queue = data_to_relay_nodes_queue
        self.game_engine_eval_queue = game_engine_eval_queue
        self.eval_game_engine_queue = eval_game_engine_queue
        self.game_state = GameState()
        self.logger = CustomLogger(self.__class__.__name__).get_logger()
        self.curr_player = 1
        self.curr_round = 1

    async def get_predicted_action (self):
        predicted_action = ""
        if self.curr_player == 1:
            predicted_action = await self.p1_action_queue.get()
        else:
            predicted_action = await self.p2_action_queue.get()
        self.logger.info(f"Game engine for player {self.curr_player} received action {predicted_action} from the queue")
        return predicted_action

    def switch_player_turn(self):
        self.curr_player = 1 if self.curr_player == 2 else 2

    async def get_visibility_snow_state(self): 
        #needa clear queue
        await self.data_to_visualizer_queue.put(
            dumps(
                {
                    "topic" : "request/visibilities",
                    "data": ""
                }
            )
        )
        players_visibility = loads(await self.data_from_visualizer_queue.get())
        opp_id = "p1" if self.curr_player == 2 else "p2"
        self.logger.info(f"Received player_visibility : \n {dumps(players_visibility, indent=4)} ")
        return players_visibility[opp_id]["is_visible"],players_visibility[opp_id]["walks_on_snow"]



    async def get_corrected_state_from_eval_server(self, predicted_action):
        await self.game_engine_eval_queue.put(
            dumps(
                 {
                    "player_id": self.curr_player,
                    "action": predicted_action,
                    "game_state": self.game_state.get_game_state()
                }
            )
        )
        corrected_game_state = await self.eval_game_engine_queue.get()
        self.logger.info(f"Game engine received corrected_game_state : \n {dumps(corrected_game_state, indent=4)}")
        return corrected_game_state
    
    async def update_visualizers(self, predicted_action):
        await self.data_to_visualizer_queue.put(
            dumps(
                {
                    "topic" : "corrected_game_state",
                    "data" : {
                        "player_id": self.curr_player,
                        "action": predicted_action,
                        "game_state": self.game_state.get_game_state() ,
                    }
                }
            )
        )
    
    async def update_relay_nodes(self):
        #assertion : gs is always the corrected_game_state returned by eval_server
        gs = self.game_state.get_game_state() 
        self.logger.info(f"Sending current (corrected) game state to relay node : \n {dumps(gs, indent = 4)}")
        await self.data_to_relay_nodes_queue.put(dumps(gs))
        

    async def run(self):
        while True:
            self.logger.info(f"Player {self.curr_player}'s turn")
            predicted_action = await self.get_predicted_action()
            (is_opponent_visible, is_opponent_in_bomb) =  await self.get_visibility_snow_state()
            self.game_state.execute_action(
                predicted_action,
                self.curr_player,
                is_opponent_visible,
                is_opponent_in_bomb
            )
            corrected_game_state = await self.get_corrected_state_from_eval_server(predicted_action)
            if self.game_state.is_same_game_state(corrected_game_state) :
                self.logger.info("No discrepancy in game state hence no update needed, yey!") 
            else:
                self.logger.info("Discrepancy in the game state received, updating to the corrected state, oops") 
                self.game_state.update_game_state(corrected_game_state)
            await self.update_visualizers(predicted_action)
            await self.update_relay_nodes()
            self.switch_player_turn()




async def game_worker(
    p1_action_queue: Queue,
    p2_action_queue: Queue,
    p1_get_shot_queue: Queue,
    p2_get_shot_queue: Queue,
    data_from_visualizer_queue: Queue,
    data_to_visualizer_queue: Queue,
    data_to_relay_nodes_queue: Queue,
    game_engine_eval_queue: Queue,
    eval_game_engine_queue: Queue,
):
    game_engine = GameEngine(
        p1_action_queue,
        p2_action_queue,
        p1_get_shot_queue,
        p2_get_shot_queue,
        data_from_visualizer_queue,
        data_to_visualizer_queue,
        data_to_relay_nodes_queue,
        game_engine_eval_queue,
        eval_game_engine_queue,
    )
    await game_engine.run()
