HOST = "0.0.0.0"
PORT = "51075"

OK = 0
NAME_IS_TAKEN = 1

START_NEW_SESSION = 'Start a new session!'
JOIN_SESSION = 'Join an existing session!'
WRONG_SESSION_ID = 1
SESSION_IS_FULL = 2


MAFIA = 0
DETECTIVE = 1
CIVILIAN = 2
UNDEFINED = 3
ROLES_STR = {MAFIA:"MAFIA", DETECTIVE:"DETECTIVE", CIVILIAN:"CIVILIAN", UNDEFINED:"UNDEFINED"}

ALIVE = 0
GHOST = 1

JOIN = 0
START = 1
KILL = 2
END_GAME = 3

DAY = 0
NIGHT = 1
TIME = {DAY:"DAY", NIGHT:"NIGHT"}

NOT_OVER = 0
MAFIA_WIN = 1
CIVIL_WIN = 2

GHOST_MESSAGE = "YOU ARE A GHOST!!! ༼ つ ╹ ╹ ༽つ"

LINE = "-------------------------------------------------"
NIGHT_STR = " NIGHT {}"
DAY_STR = " DAY {}"

NIGHT_POEM = ("☆ The city goes into the night. ☆"
              "\n☆ You will not see in windows light. ☆")

DAY_POEM = ("☆ The city rises from its slumber. ☆"
            "\n☆ What happened through the night, we wonder. ☆")

MAFIA_POEM = ("\n✝ Killers have no time for sleep. ✝"
              "\n✝ Tell us, who's the slaughtered sheep? ✝")

DETECTIVE_POEM = ("\n⚄ Detective now will make their choice. ⚄"
                  "\n⚄ They'd better listen inner voice. ⚄")

MAFIA_WIN_POEM = ("\n\n-------------------------------------------------"
                  "\n☆ For now, my friends, the chaos wins. ☆"
                  "\n☆ The mafia triumphant kings! ☆"
                  "\n☆ MAFIA WON ☆"
                  "\n-------------------------------------------------")

CIVIL_WIN_POEM = ("\n\n-------------------------------------------------"
                  "\n☆ Good citizens now may exult. ☆"
                  "\n☆ They have destroyed the evil cult! ☆"
                  "\n☆ CIVILIANS WON ☆"
                  "\n-------------------------------------------------")
