from enum import Enum
import random

class Action(Enum):
    SHOOT       = "gun"
    BOMB        = "bomb"
    NONE        = "none"
    SHIELD      = "shield"
    RELOAD      = "reload"
    BADMINTON   = "badminton"
    GOLF        = "golf"
    FENCING     = "fencing"
    BOXING      = "boxing"
    LOGOUT      = "logout"

    @staticmethod
    def random_action():
        return random.choice([action for action in Action if action != Action.NONE]).value

class ActionStatus(Enum):
    SUCCESS = "success"  # does not necessarily mean the opponent was hit. only to display AR visualisation
    FAIL_NOT_ENOUGH_BULLETS = "fail_not_enough_bullets"
    FAIL_NOT_ENOUGH_SHIELDS = "fail_not_enough_shields"
    FAIL_NOT_ENOUGH_BOMBS = "fail_not_enough_bombs"
    FAIL_DISALLOWED_RELOAD = "fail_disallowed_reload"  # when player tries to reload when they still have bullets left
    FAIL_DISALLOWED_LOGOUT = "fail_disallowed_logout"