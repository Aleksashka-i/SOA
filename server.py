import asyncio
import logging
import grpc
import random
from random import randrange
from collections import defaultdict
import json 
import os

import pkg.game_pb2 as game_pb2
import pkg.game_pb2_grpc as game_pb2_grpc
from pkg.globals_grpc import *
import requests
import time

class Session:
    def __init__(self, session_id, size):
        self.session_id = session_id
        self.session_started = False
        self.size = size
        
        self.roles = dict() # {username, role}
        self.player_status = dict() # {username, ALIVE/GHOST}
        self.alives = []
        self.ghosts = []
        self.last_victim = ""
        self.last_victim_role = UNDEFINED
        self.guessed_mafia = ""
        self.message_queue = []
        self.game_over = NOT_OVER
        self.available_roles = []
        self.switch = 0

        self.day_num = 0
        self.time = DAY
        self.votes = defaultdict(int)
        self.mafia_cnt = 0
        self.civil_cnt = 0

        self.lock = asyncio.Lock()
        self.condition = asyncio.Condition()
        
    
    async def generate_roles(self):
        mafia_sz = (self.size - 1) // 3
        civil_sz = self.size - mafia_sz - DETECTIVE
        self.available_roles += mafia_sz * [MAFIA]
        self.available_roles += [DETECTIVE]
        self.available_roles += civil_sz * [CIVILLIAN]
        self.mafia_cnt = mafia_sz
        self.civil_cnt = civil_sz + 1


class MafiaServiceServicer(game_pb2_grpc.MafiaServiceServicer):
    def __init__(self, rest_server:str):
        self.users = dict() # {username, session_id}
        self.users_time = dict()
        self.sessions = dict() # {session_id, Session}
        self.sessions_size = dict() # {session_id, active_cnt}
        self.lock = asyncio.Lock()
        self.rest_server = rest_server

    
    async def Update_DB(self, username, is_winner:bool, time_start):
        response = requests.get((self.rest_server + "/api/players/{}").format(username))
        if response is None:
            return
        else:
            dict_params = response.json()
            dict_params["games"] += 1
            dict_params["wins"] += is_winner
            dict_params["time_in_game"] += time.time() - time_start
            dict_params["time_in_game"] = float("{:.2f}".format(dict_params["time_in_game"]))
            _ = requests.put((self.rest_server + "/api/players/update"), json=dict_params)

    async def SetUsername(self, request, context):
        async with self.lock:
            if request.username in self.users:
                return game_pb2.SetUsernameResponse(status=NAME_IS_TAKEN)
            else:
                self.users[request.username] = 0
                requests.post(self.rest_server + "/api/players/insert", json={"name":request.username})
                return game_pb2.SetUsernameResponse(status=OK)
        
    async def StartSession(self, request, context):
        async with self.lock:
            if request.session_id in self.sessions:
                return game_pb2.StartSessionResponse(status=WRONG_SESSION_ID)
        new_session = Session(session_id=request.session_id,
                                size=request.size)
        await new_session.generate_roles()
        role = new_session.available_roles.pop(randrange(len(new_session.available_roles)))
        new_session.roles[request.username] = role
        new_session.alives += [request.username]
        new_session.message_queue.append(game_pb2.MessengerResponse(status=JOIN, message="--------> {} joined session \"{}\".".format(request.username, request.session_id)))
        async with self.lock:
            self.sessions[request.session_id] = new_session
            self.users[request.username] = request.session_id
            self.users_time[request.username] = time.time()
            self.sessions_size[request.session_id] = request.size
        return game_pb2.StartSessionResponse(status=OK, role=role)
    
    async def JoinSession(self, request, context):
        async with self.lock:
            if request.session_id not in self.sessions:
                return game_pb2.JoinSessionResponse(status=WRONG_SESSION_ID)
            elif self.sessions[request.session_id].session_started == True:
                return game_pb2.JoinSessionResponse(status=SESSION_IS_FULL)
            cur_session = self.sessions[request.session_id]
            self.users[request.username] = request.session_id
            self.users_time[request.username] = time.time()
        async with cur_session.lock:
            cur_session.message_queue.append(game_pb2.MessengerResponse(status=JOIN, message="--------> {} joined session \"{}\".".format(request.username, request.session_id)))
            role = cur_session.available_roles.pop(randrange(len(cur_session.available_roles)))
            cur_session.roles[request.username] = role
            cur_session.alives += [request.username]
            if not cur_session.available_roles:
                cur_session.message_queue.append(game_pb2.MessengerResponse(status=START, message=
                                                                            "\n-------------------------------------------------"
                                                                            "\nAll players has joined session \"{}\".".format(request.session_id)))
        return game_pb2.JoinSessionResponse(status=OK, role=role)
    
    async def Messenger(self, request, context):
        iter = 0
        async with self.lock:
            session = self.sessions[self.users[request.username]]
        while True:
            while len(session.message_queue) <= iter:
                await asyncio.sleep(0)
            async with session.lock:
                cur_message = session.message_queue[iter]
            iter += 1
            if cur_message.status == END_GAME:
                is_winner = False
                if session.game_over == MAFIA_WIN and session.roles[request.username] == MAFIA:
                    is_winner = True
                if session.game_over == CIVIL_WIN and session.roles[request.username] != MAFIA:
                    is_winner = True
                async with self.lock:
                    await self.Update_DB(request.username, is_winner, self.users_time[request.username])
                    _ = self.users.pop(request.username)
                    self.sessions_size[session.session_id] -= 1
                    if (self.sessions_size[session.session_id] == 0):
                        _ = self.sessions.pop(session.session_id)

            yield cur_message
    
    async def DayNight(self, request, context):
        logging.info("{} requested switch of time from {} to {}.".format(request.username,
                                                                         TIME[request.time],
                                                                         TIME[(request.time + 1)%2]))
        async with self.lock:
            session = self.sessions[self.users[request.username]]
        async with session.condition:
            session.switch += 1
            if session.switch == len(session.alives):
                session.switch = 0
                if session.day_num != 0:
                    max_vote = max(session.votes.values())
                    victims = [k for k,v in session.votes.items() if v == max_vote]
                    session.last_victim = random.choice(victims)
                    session.last_victim_role = session.roles[session.last_victim]
                    session.alives.remove(session.last_victim)
                    session.ghosts += [session.last_victim]
                    async with session.lock:
                        if request.time == DAY:
                            kill_message = "--------> \"{}\" was voted out. They were a {}.".format(session.last_victim,
                                                                                                    ROLES_STR[session.last_victim_role])
                        else:
                            kill_message = "--------> \"{}\" was killed. They were a {}.".format(session.last_victim,
                                                                                                    ROLES_STR[session.last_victim_role])
                        session.message_queue.append(game_pb2.MessengerResponse(status=KILL, message=kill_message, victim=session.last_victim))
                    session.votes = defaultdict(int)
                    if session.last_victim_role == MAFIA:
                        session.mafia_cnt -= 1
                    else:
                        session.civil_cnt -= 1
                    if session.mafia_cnt == 0:
                        session.game_over = CIVIL_WIN
                        session.message_queue.append(game_pb2.MessengerResponse(status=END_GAME, message=CIVIL_WIN_POEM))
                    elif session.mafia_cnt == session.civil_cnt:
                        session.game_over = MAFIA_WIN
                        session.message_queue.append(game_pb2.MessengerResponse(status=END_GAME, message=MAFIA_WIN_POEM))
                session.day_num = 1
                session.condition.notify_all()
            else:
                await session.condition.wait()
        response = game_pb2.DayNightResponse()
        response.victim = session.last_victim
        response.victim_role = session.last_victim_role
        response.mafia = session.guessed_mafia
        response.is_end = session.game_over
        response.alives.extend(session.alives)
        response.ghosts.extend(session.ghosts)
        return response

    
    async def KillPlayer(self, request, context):
        async with self.lock:
            session = self.sessions[self.users[request.username]]
        async with session.lock:
            session.votes[request.victim_username] += 1
        return game_pb2.KillPlayerResponse()

    async def DetectiveMove(self, request, context):
        async with self.lock:
            session = self.sessions[self.users[request.username]]
        async with session.lock:
            player_role = session.roles[request.victim_username]
        if player_role != MAFIA:
            session.guessed_mafia = ""
        return game_pb2.DetectiveMoveResponse(player_role=player_role)

    async def PublishData(self, request, context):
        async with self.lock:
            session = self.sessions[self.users[request.username]]
        async with session.lock:
            session.guessed_mafia = request.mafia
            role = session.roles[self.victim_username]
        return game_pb2.PublishData()


async def serve() -> None:
    rest_server = os.environ.get("RESTSERVER_PORT")
    if rest_server is not None:
        rest_server = "http://" + rest_server
    server = grpc.aio.server()
    game_pb2_grpc.add_MafiaServiceServicer_to_server(MafiaServiceServicer(rest_server), server)
    listen_addr = "{}:{}".format(HOST, PORT)
    server.add_insecure_port(listen_addr)
    logging.info("Starting server on %s", listen_addr)
    await server.start()
    await server.wait_for_termination()


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    asyncio.run(serve())
