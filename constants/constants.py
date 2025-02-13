DUMMY_GAME_STATE =  {
        'p1' : {
            'hp'        : 100,
            'bullets'   : 5,
            'bombs'     : 1,
            'shield_hp' : 30,
            'deaths'    : 0,
            'shields'   : 2
        },
        'p2' : {
            'hp'        : 100,
            'bullets'   : 5,
            'bombs'     : 1,
            'shield_hp' : 30,
            'deaths'    : 0,
            'shields'   : 2
        }
}

DUMMY_RELAY_NODE_DATA_P1 = {
       'player_id' : 1,
       'type' : "IMU",
       'values' : [1.0, 2.0, 3.0, 4.0, 5.0, 6.0]
}

DUMMY_RELAY_NODE_DATA_P2 = {
       'player_id' : 2,
       'type' : "IMU",
       'values' : [1.0, 2.0, 3.0, 4.0, 5.0, 6.0]
}

INITIAL_HP = 100
INITIAL_SHIELDS = 3
INITIAL_BOMBS = 2

ACTION_DAMAGE = 10
BULLET_DAMAGE = 5
BOMB_DAMAGE = 5

BULLET_PER_RELOAD = 6
SHIELD_HP = 30

# Helper.py#L62-69, num_shoot_total + num_AI_total - 1 (logout, we don't count it here)
NUMBER_OF_TWO_PLAYER_ROUNDS_BEFORE_LOGOUT = 21

