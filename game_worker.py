from asyncio import Queue,TimeoutError,wait_for
from json import dumps, loads
from constants.constants import DUMMY_GAME_STATE
from constants.enums import Action
from utils.game_state import GameState
from utils.logger import CustomLogger
import time

class GameEngine:
    def __init__(
        self,
        p1_action_queue: Queue,
        p2_action_queue: Queue,
        p1_get_shot_queue: Queue,
        p2_get_shot_queue: Queue,
        data_from_visualizer_queue: Queue,
        data_to_visualizer_queue: Queue,
        data_from_relay_nodes_queue: Queue,
        data_to_relay_nodes_queue: Queue,
        game_engine_eval_queue: Queue,
        eval_game_engine_queue: Queue,
    ):
        # self.p1_action_queue = p1_action_queue
        # self.p2_action_queue = p2_action_queue
        self.p1_get_shot_queue = p1_get_shot_queue
        self.p2_get_shot_queue = p2_get_shot_queue
        self.data_from_visualizer_queue = data_from_visualizer_queue
        self.data_to_visualizer_queue = data_to_visualizer_queue
        self.data_from_relay_nodes_queue = data_from_relay_nodes_queue
        self.data_to_relay_nodes_queue = data_to_relay_nodes_queue
        self.game_engine_eval_queue = game_engine_eval_queue
        self.eval_game_engine_queue = eval_game_engine_queue
        self.game_state = GameState()
        self.logger = CustomLogger(self.__class__.__name__).get_logger()
        self.curr_player = 1
        self.curr_round = 1

    async def clear_relay_nodes_queue(self) :
        while not self.data_from_relay_nodes_queue.empty() :
            await self.data_from_relay_nodes_queue.get()

    async def get_predicted_action (self):
        predicted_action = ""
        relay_data = loads(await self.data_from_relay_nodes_queue.get())
        # if self.curr_round == 23 :
        #     # self.logger.info(f"{self.curr_round} return logout")
        #     return "logout"
        # while not self.data_from_relay_nodes_queue.empty() :
        #     if relay_data['predicted_action'] == Action.SHOOT.value :
        #         await self.clear_relay_nodes_queue()
        #     relay_data = loads(await self.data_from_relay_nodes_queue.get())
            
        predicted_action = relay_data['predicted_action']
        self.curr_player = relay_data['player_id']
        self.logger.info(f"Game engine for player {self.curr_player} received action {predicted_action} from the queue")
        return predicted_action

    def switch_player_turn(self):
        self.curr_player = 1 if self.curr_player == 2 else 2

    async def get_visibility_snow_state(self): 
        curr = "p1" if self.curr_player == 1 else "p2"
        #needa clear queue
        await self.data_to_visualizer_queue.put(
            dumps(
                {
                    "topic" : f"request/visibilities",
                    "data": curr
                }
            )
        )
        try:
            players_visibility = loads(await wait_for(self.data_from_visualizer_queue.get(), timeout=2))
            self.logger.info(f"Received player_visibility : \n {dumps(players_visibility, indent=4)} ")
            return players_visibility[curr]["is_visible"],players_visibility[curr]["no_snow_bombs"]
            # process the item
        except TimeoutError:
            self.logger.info("Times out waiting for visibility response, returning True,0 by default")
            return True,0
           
        # players_visibility = loads(await self.data_from_visualizer_queue.get())
        # # opp_id = "p1" if self.curr_player == 2 else "p2"
        # self.logger.info(f"Received player_visibility : \n {dumps(players_visibility, indent=4)} ")
        # return players_visibility["p1"]["is_visible"],players_visibility["p1"]["no_snow_bombs"]
        # return True,0


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
        try :
            corrected_game_state = await wait_for(self.eval_game_engine_queue.get(), timeout=2)
            self.logger.info(f"Game engine received corrected_game_state : \n {dumps(corrected_game_state, indent=4)}")
            return corrected_game_state
        except TimeoutError : 
            self.logger.info("eval server times out, using own internal game state instead")
            return self.game_state.get_game_state()
     
    async def update_visualizers(self, predicted_action):
        await self.data_to_visualizer_queue.put(
            dumps(
                {
                    "topic" : "corrected_game_state",
                    "data" : {
                        "player_id": "p1" if self.curr_player == 1 else "p2",
                        "action": predicted_action,
                        "game_state": self.game_state.get_game_state() ,
                    }
                }
            )
        )
    
    async def update_relay_nodes(self,gs):
        #assertion : gs is always the corrected_game_state returned by eval_server
        # gs = self.game_state.get_game_state() 
        self.logger.info(f"Sending current (corrected) game state to relay node : \n {dumps(gs, indent = 4)}")
        await self.data_to_relay_nodes_queue.put(dumps(gs))
    
    async def check_opp_got_shot(self):
        opp_queue = (
            self.p1_get_shot_queue
            if self.curr_player == 2
            else self.p2_get_shot_queue
        )
        if opp_queue.empty() :
            self.logger.info(f"Opp_got_shot queue is empty")
            return False
        else :
            while not opp_queue.empty() :
                await opp_queue.get()
            self.logger.info(f"Opp_got_shot queue is not empty")
            return True
    
    async def run(self):
        while True:
            predicted_action = await self.get_predicted_action()
            # got_shot = False
            # if (predicted_action == Action.SHOOT.value) :
            #     time.sleep(0.1)
            #     got_shot = await self.check_opp_got_shot()
            (is_opponent_visible, no_snow_bombs) =  await self.get_visibility_snow_state()
            action_status = self.game_state.execute_action(
                predicted_action,
                self.curr_player,
                # True if predicted_action == Action.SHOOT.value else is_opponent_visible,
                is_opponent_visible,
                no_snow_bombs
            )
            self.logger.info(f"Round {self.curr_round}, action {predicted_action} executed with status {action_status}")
            corrected_game_state = await self.get_corrected_state_from_eval_server(predicted_action)
            await self.update_relay_nodes(corrected_game_state)
            if self.game_state.is_same_game_state(corrected_game_state) :
                self.logger.info("No discrepancy in game state hence no update needed, yey!") 
            else:
                self.logger.info("Discrepancy in the game state received, updating to the corrected state, oops") 
                self.game_state.update_game_state(corrected_game_state)
            await self.update_visualizers(predicted_action)
            self.curr_round += 1
            # self.switch_player_turn()


async def game_worker(
    p1_action_queue: Queue,
    p2_action_queue: Queue,
    p1_get_shot_queue: Queue,
    p2_get_shot_queue: Queue,
    data_from_visualizer_queue: Queue,
    data_to_visualizer_queue: Queue,
    data_from_relay_nodes_queue: Queue,
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
        data_from_relay_nodes_queue,
        data_to_relay_nodes_queue,
        game_engine_eval_queue,
        eval_game_engine_queue,
    )
    await game_engine.run()
