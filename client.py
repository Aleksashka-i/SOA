import asyncio
import grpc
import random
from pick import pick
import pkg.game_pb2 as game_pb2
import pkg.game_pb2_grpc as game_pb2_grpc
from pkg.globals_grpc import *
from rabbit_client import RabbitMQClient
from copy import deepcopy
import pika
import threading
import tkinter as tk

class Player:
    def __init__(self, stub, channel):
        self.stub = stub
        self.channel = channel
        self.username = None
        self.role = None
        self.session_id = None
        self.session_num = 0
        self.is_ghost = False
        self.ghosts = []
        self.rabbit_client = None
        self._is_interrupted = False

    
    async def start_session(self):
        size = max(int(input("Enter number of players: ")), 4) # default 4 players
        self.session_id = input("Enter your session id: ")
        while True:
            response = await self.stub.StartSession(
                game_pb2.StartSessionRequest(username=self.username, 
                                             session_id=self.session_id, 
                                             size=size)
            )
            if response.status == WRONG_SESSION_ID:
                self.session_id = input(
                    "Session id \"{}\" is taken, please use different session id: ".format(self.session_id)
                    )
            else:
                self.role = response.role
                print("--------> Session \"{}\" is started. Waiting for players to join.".format(self.session_id), flush=True)
                break
    
    async def join_session(self):
        self.session_id = input("Enter your session id: ")
        while True:
            response = await self.stub.JoinSession(
                game_pb2.JoinSessionRequest(username=self.username, session_id=self.session_id)
            )
            if response.status == WRONG_SESSION_ID:
                self.session_id = input(
                    "Session id \"{}\" is wrong, please use different session id: ".format(self.session_id)
                    )
            elif response.status == SESSION_IS_FULL:
                self.usession_id = input(
                    "Session \"{}\" is full, please use different session id: ".format(self.session_id)
                    )
            else:
                self.role = response.role
                print("--------> You joined session \"{}\". Waiting for players to join.".format(self.session_id), flush=True)
                break

    async def enter_session(self):
        self.username = input("Enter your username: ")
        while len(self.username) == 0:
            self.username = input("Name can't be empty. Please, enter different username: ")
        while True:
            response = await self.stub.SetUsername(
                game_pb2.SetUsernameRequest(username=self.username)
            )
            if response.status == NAME_IS_TAKEN:
                self.username = input(
                    "Username \"{}\" is taken, please choose different username: ".format(self.username)
                    )
            else:
                break
        options = [START_NEW_SESSION, JOIN_SESSION]
        option, index = pick(options, title='Please make a choice: ')
        if option == START_NEW_SESSION:
            await self.start_session()
        else:
            await self.join_session()
    
    async def day_vote(self, alives, mafia=None):
        alives.remove(self.username)
        print("\n\nVote for the player to be eliminated. Your options:", end = " ", flush=True)
        output = (', '.join('"' + player + '"' for player in alives))
        output += ", or skip the vote."
        print(output, flush=True)
        alives += ["skip the vote"]
        victim_num = random.choice(range(0, len(alives)))
        if mafia != None and mafia != self.username:
            victim_num = alives.index(mafia)
        if (victim_num + 1 == len(alives)):
            print("You chose to skip the vote.\n", flush=True)
            return
        response = await self.stub.KillPlayer(
             game_pb2.KillPlayerRequest(username=self.username, victim_username=alives[victim_num])
        )
        print("You voted for \"{}\" elimination.\n".format(alives[victim_num]), flush=True)

    async def mafia_vote(self, alives):
        alives.remove(self.username)
        print(MAFIA_POEM, flush=True)
        print("\nVote for player to be killed. Your options:", end = " ", flush=True)
        output = (', '.join('"' + player + '"' for player in alives))
        print(output, flush=True)
        victim = random.choice(alives)
        response = await self.stub.KillPlayer(
             game_pb2.KillPlayerRequest(username=self.username, victim_username=victim)
        )
        print("You voted for \"{}\" murder.".format(victim), flush=True)

    async def detective_vote(self, list):
        print(DETECTIVE_POEM, flush=True)
        print("\nVote for player to be checked. Your options:", end = " ", flush=True)
        output = (', '.join('"' + player + '"' for player in list))
        print(output, flush=True)
        victim = random.choice(list)
        response = await self.stub.DetectiveMove(
             game_pb2.DetectiveMoveRequest(username=self.username, victim_username=victim)
        )
        print("You chose to check \"{}\". They are a {}.".format(victim, ROLES_STR[response.player_role]), flush=True)
        if response.player_role == MAFIA:
            print("Do you want to share info?", end = " ", flush=True)
            if random.choice(range(0, 2)) == 0:
                print("NO", flush=True)
            else:
                response = await self.stub.DetectiveMove(
                    game_pb2.PublishDataRequest(username=self.username, mafia=victim)
                )
                print("YES", flush=True)

    
    def start_consuming(self):
        print("Start listening")
        for message in self.rabbit_client.channel.consume("chat_{}".format(self.username)):
            if self._is_interrupted:
                break
            if not message:
                continue
            method, properties, body = message
            print(body.decode())
    
    def chat(self):
        self._is_interrupted = False
        self.rabbit_client = RabbitMQClient(self.username)
        t = threading.Thread(target=self.start_consuming, daemon=True)
        t.start()
        connection = pika.BlockingConnection(pika.ConnectionParameters(host="0.0.0.0", port="5672"))
        channel = connection.channel()
        root = tk.Tk()
        root.title("{} messenger".format(self.username))
        def retrieve_input():
            inputValue=textBox.get("1.0","end-1c")
            channel.basic_publish(exchange='receiver', routing_key='', body="\n[{}] {}".format(self.username, inputValue))
        textBox = tk.Text(root, height=10, width=15)
        textBox.pack()
        buttonCommit=tk.Button(root, height=1, width=10, text="Send", 
                            command=lambda: retrieve_input())
        buttonCommit.pack()
        tk.mainloop()
        self._is_interrupted = True 
        channel.basic_publish(exchange='receiver', routing_key='', body="\n[{}] {}".format(self.username, "STOP THE CHAT"))
        t.join()
        self.rabbit_client.close()

    async def game_engine(self):
        night_num = 0
        alives = []
        checked = []
        if self.role == DETECTIVE:
            checked += [self.username]
        is_mafia = None
        while True:
            if night_num != 0:
                options = ["YES", "NO"]
                option, index = pick(options, title='Do you wanna chat?')
                if option == "YES":
                    self.chat()
                await self.day_vote(deepcopy(alives), is_mafia)
            response = await self.stub.DayNight(
                game_pb2.DayNightRequest(time=DAY, username=self.username) #switch from DAY to NIGHT
            )
            alives = [v for v in response.alives]
            ghosts = [v for v in response.ghosts]
            self.ghosts = ghosts
            if night_num != 0:
                print("\n\"{}\" was voted out. They were a {}.".format(response.victim, ROLES_STR[response.victim_role]), flush=True)
                print("ALIVE: {}".format(alives))
                print("GHOSTS: {}".format(ghosts))
                print((LINE + DAY_STR).format(night_num), flush=True)
                if response.victim == self.username:
                    self.is_ghost = True
                    print(("\n\n" + LINE + "\n" + GHOST_MESSAGE + "\n" + LINE + "\n\n"), flush=True)
                    break
                if response.is_end != NOT_OVER:
                    break
            night_num += 1
            print(("\n" + LINE + NIGHT_STR).format(night_num), flush=True)
            print(NIGHT_POEM.format(night_num), flush=True)
            if self.role == MAFIA:
                options = ["YES", "NO"]
                option, index = pick(options, title='Do you wanna chat?')
                if option == "YES":
                    self.chat()
                await self.mafia_vote(deepcopy(alives))
            elif self.role == DETECTIVE:
                list = [x for x in alives if x not in checked]
                await self.detective_vote(deepcopy(list))
            response = await self.stub.DayNight(
                game_pb2.DayNightRequest(time=NIGHT, username=self.username) #switch from NIGHT to DAY
            )
            print(LINE, NIGHT_STR.format(night_num), flush=True)
            print(("\n" + LINE + DAY_STR).format(night_num), flush=True)
            print(DAY_POEM.format(night_num), flush=True)
            alives = [v for v in response.alives]
            ghosts = [v for v in response.ghosts]
            self.ghosts = ghosts
            print("\n\"{}\" was killed last night. They were a {}.".format(response.victim, ROLES_STR[response.victim_role]), flush=True)
            if response.mafia != "":
                is_mafia = response.mafia
                print("ATTENTION! {} is a MAFIA.".format({response.mafia}), flush=True)
            else:
                is_mafia = None
            if response.is_end != NOT_OVER:
                print("ALIVE: {}".format(alives))
                print("GHOSTS: {}".format(ghosts))
                print((LINE + DAY_STR).format(night_num), flush=True)
                break
            if response.victim == self.username:
                self.is_ghost = True
                print("ALIVE: {}".format(alives))
                print("GHOSTS: {}".format(ghosts))
                print((LINE + DAY_STR).format(night_num), flush=True)
                print(("\n\n" + LINE + "\n" + GHOST_MESSAGE + "\n" + LINE + "\n\n"), flush=True)
                break

async def messanger(player):
    async for m in player.stub.Messenger(game_pb2.MessengerRequest(username=player.username)):
        if m.status == JOIN:
            print(m.message, flush=True)
        if m.status == START:
            print(m.message, flush=True)
            print("\nLet's start the game. Your role: {}.".format(ROLES_STR[player.role]), flush=True)
            print(LINE, flush=True)
            player.session_num += 1
            await player.game_engine()
        if m.status == KILL:
            if player.is_ghost and (m.victim not in player.ghosts):
                print(m.message, flush=True)
        if m.status == END_GAME:
            print(m.message, flush=True)
            await player.channel.close()
            exit(0)
        

async def run() -> None:
    listen_addr = "{}:{}".format(HOST, PORT)
    async with grpc.aio.insecure_channel(listen_addr) as channel:
        stub = game_pb2_grpc.MafiaServiceStub(channel)
        player = Player(stub, channel)
        await player.enter_session()
        await messanger(player=player)

if __name__ == '__main__':
    asyncio.run(run())
