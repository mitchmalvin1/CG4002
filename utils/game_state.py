from enum import Enum
from constants import constants
from constants.enums import ActionStatus, Action
import random

class Player:
    def __init__(self):
        self.deaths = 0
        self.reset_state()

    def get_state(self):
        state = {
            'hp'        : self.hp,
            'bullets'   : self.bullets,
            'bombs'     : self.bombs,
            'shield_hp' : self.shield_hp,
            'deaths'    : self.deaths,
            'shields'   : self.shields
        }

        return state

    def update_state(self, state):
        self.hp = state["hp"]
        self.shield_hp = state["shield_hp"]
        self.bullets = state["bullets"]
        self.shields = state["shields"]
        self.bombs = state["bombs"]
        self.deaths = state["deaths"]

    def is_same_state(self, state):
        return (
            self.hp == state["hp"] and
            self.shield_hp == state["shield_hp"]and 
            self.bullets == state["bullets"] and 
            self.shields == state["shields"] and
            self.bombs == state["bombs"] and
            self.deaths == state["deaths"]
        )
        
    #does not reset deaths
    def reset_state(self):
        self.hp = constants.INITIAL_HP
        self.shield_hp = 0
        self.bullets = constants.BULLET_PER_RELOAD
        self.shields = constants.INITIAL_SHIELDS
        self.bombs = constants.INITIAL_BOMBS
    
    def respawn(self):
        self.hp = constants.INITIAL_HP
        self.shield_hp = 0
        self.bullets = constants.BULLET_PER_RELOAD
        self.shields = constants.INITIAL_SHIELDS
        self.bombs = constants.INITIAL_BOMBS

    def incur_damage(self, dmg: int):
        if self.shield_hp > 0:
            if dmg >= self.shield_hp:
                dmg -= self.shield_hp
                self.shield_hp = 0
            else:
                self.shield_hp -= dmg
                return

        if dmg >= self.hp:
            self.hp = 0
            self.deaths += 1
            self.respawn()
        else:
            self.hp -= dmg
        print(f"Reducing hp by {dmg} to {self.hp}")
  
    def reload(self):
        if self.bullets <= 0:
            self.bullets = constants.BULLET_PER_RELOAD
            return True
        return False

    def try_shield(self):
        if self.shields <= 0:
            return False
        if self.shield_hp > 0 :
            return True

        self.shields -= 1
        self.shield_hp = constants.SHIELD_HP
        return True

    def try_shoot(self, 
        opponent: "Player", 
        is_opponent_visible: bool
    ):
        if self.bullets <= 0:
            return False
        self.bullets -= 1
        if is_opponent_visible:
            opponent.incur_damage(constants.BULLET_DAMAGE)
        return True

    def try_bomb(self, 
        opponent: "Player", 
        is_opponent_visible: bool
    ):
        if self.bombs <= 0:
            return False
        self.bombs -= 1
        if is_opponent_visible:
            opponent.incur_damage(constants.BOMB_DAMAGE)
        return True

    def try_bomb_after_effect(self, 
        opponent: "Player", 
    ):
        opponent.incur_damage(constants.BOMB_DAMAGE)

    def try_action_attack(self, 
        opponent: "Player", 
        is_opponent_visible: bool
    ):
        if is_opponent_visible:
            opponent.incur_damage(constants.ACTION_DAMAGE)
            return True
        return False


class GameState:
    def __init__(self):
        self.player_1 = Player()
        self.player_2 = Player()

    def get_game_state(self):
        return {"p1": self.player_1.get_state(), "p2": self.player_2.get_state()}

    def update_game_state(self, new_state):
        self.player_1.update_state(new_state["p1"])
        self.player_2.update_state(new_state["p2"])

 
    def is_same_game_state(self, game_state):
        return (self.player_1.is_same_state(game_state["p1"]) 
        and self.player_2.is_same_state(game_state["p2"]))

    def execute_action(self, 
        action: str, 
        player: int, 
        is_opponent_visible: bool,
        no_snow_bombs: int
    ) -> ActionStatus:
        attacker, defender = (
            (self.player_1, self.player_2)
            if player == 1
            else (self.player_2, self.player_1)
        )
        while is_opponent_visible and no_snow_bombs > 0 :
            attacker.try_bomb_after_effect(defender)
            no_snow_bombs -=1
        match action:
            case Action.SHOOT.value:
                if not attacker.try_shoot(defender, is_opponent_visible):
                    return ActionStatus.FAIL_NOT_ENOUGH_BULLETS.value
                return ActionStatus.SUCCESS.value
            case Action.SHIELD.value:
                if not attacker.try_shield():
                    return ActionStatus.FAIL_NOT_ENOUGH_SHIELDS.value
                return ActionStatus.SUCCESS.value
            case Action.RELOAD.value:
                if not attacker.reload():
                    return ActionStatus.FAIL_DISALLOWED_RELOAD.value
                return ActionStatus.SUCCESS.value
            case Action.BOMB.value:
                if not attacker.try_bomb(defender, is_opponent_visible):
                    return ActionStatus.FAIL_NOT_ENOUGH_BOMBS.value
                return ActionStatus.SUCCESS.value
            case Action.FENCING.value | Action.BADMINTON.value | Action.GOLF.value | Action.BOXING.value:
                if not attacker.try_action_attack(defender, is_opponent_visible):
                    return ActionStatus.FAIL_ACTION_NOT_VISIBLE
                return ActionStatus.SUCCESS.value
            case _:
                pass
        return ActionStatus.SUCCESS.value
