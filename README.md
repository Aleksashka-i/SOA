# Mafia game 
## (Service-Oriented Architectures homework)
Implemented a gRPC web service "Mafia", a client-server chat for game users using RabbitMQ and REST web service for collecting and providing clients with opportunities to work
with the resources of the game.

## Description
This repository includes a gRPC web service **"SOA-Mafia "** (hw 2), a client-server chat service for game users using the RabbitMQ message queuing system (hw 3), and a REST web service for collecting and enabling clients to work with SOA-Mafia game resources (hw 4).

## Configuration
To start the gRPC server, the REST server, and RabbitMQ, run the following command.
```
docker-compose up
```
After all the servers have been started, you need to run **4 clients** in different terminal windows:
```
python3 client.py
```
Each client will be asked to enter a username and choose between `start session` and  `join session`. One of the clients should choose `start session`, define the number of players (by default 4, but you can enter more, but then you need more terminal windows), and enter `session_id`. All other players will have to enter this `session_id` accordingly.

<details>
  <summary><b>Remark</b></summary>
You may need to install dependencies locally for clients: <code>grpcio</code>, <code>pika</code>, <code>protobuf</code>, <code>tk</code>.
You can do this via <code>pip install -r requirements.txt</code>. <code>Tkinter</code> is needed for a minimal graphical interface in chat so that you can send messages.
</details>

## How to play?
The game will automatically start after all players are added to the session. All players are bots. The game will start, and night will begin immediately since nothing happens on the first day.

### Night
Next, all members of the Mafia (in the case of 4 players, it is one) will be asked to chat. Selecting ``YES`` will open a small window. You can type messages into it and send them using the ```send``` button. Messages will appear in the chat. As mentioned earlier, the chat is implemented with the help of the message broker ``RabbitMQ``. When the GUI is closed, the chat is terminated. 

`Detective` randomly checks the still-alive players (except for himself) and randomly decides if he wants to publish the data if he has identified a member of the Mafia. 

After the chat closes, the Mafia will make 'their choice'-a player other than themselves (if there are multiple Mafia, the victim will be chosen randomly). The Mafia and Detective then send messages to the server, indicating the end of the night for them. Once the server has received these messages from all the players, it announces that the day phase has begun.

### Day
The player killed that night is sent a message that he has become a ghost. This player will then only receive messages about who players voted for during the day and who they killed during the night (i.e., the ghost continues to follow the game). During the day, every non-ghost player will also be asked to "chat." To test this, you can select two players and see that only those currently in the chat room receive messages (there is an example picture of what the mini chat interface should look like in the ``pics`` folder).

The game continues until there are 0 mafias (**CIVILIANS WON**) or as many as there are players (**MAFIA WON**).

<details>
<summary><b>Example of mafia console + chat after 1 night </b></summary>
  <pre>
    Enter your username: W
    Enter your session id: 1
    --------> You joined session "1". Waiting for players to join.
    --------> Q joined session "1".
    --------> W joined session "1".
    --------> E joined session "1".
    --------> R joined session "1".

    -------------------------------------------------
    All players have joined session "1".

    Let's start the game. Your role: MAFIA.
    -------------------------------------------------

    ------------------------------------------------- NIGHT 1
    ☆ The city goes into the night. ☆
    ☆ You will not see in windows light. ☆

    ✝ Killers have no time for sleep. ✝
    ✝ Tell us, who's the slaughtered sheep? ✝

    Vote for the player to be killed. Your options: "Q", "E", "R"
    You voted for "R" murder.
    -------------------------------------------------  NIGHT 1

    ------------------------------------------------- DAY 1
    ☆ The city rises from its slumber. ☆
    ☆ What happened through the night, we wonder. ☆

    "R" was killed last night. They were a DETECTIVE.
    Start listening

    [W] Hi!

    [Q] How are you?

    [W] I had a weird dream...

    [Q] Hm, wanna share?

    [W] Sorry, I have to run, bye!


    Vote for the player to be eliminated. Your options: "Q", "E", or skip the vote.
    You voted for "Q" elimination.


    "Q" was voted out. They were a CIVILIAN.
    ALIVE: ['W', 'E']
    GHOSTS: ['R', 'Q']
    ------------------------------------------------- DAY 1


    -------------------------------------------------
    ☆ For now, my friends, the chaos wins. ☆
    ☆ The mafia triumphant kings! ☆
    ☆ MAFIA WON ☆
    -------------------------------------------------
  </pre>
</details>

## REST API
REST service is implemented using Flask and the SQLite database.

Information about all users of the game (current server startup).
```
curl --location --request GET 'http://127.0.0.1:57015/api/players' --header 'Content-Type:application/json'  | python3 -m json.tool
```
Information about one player by username:
```
curl --location --request GET 'http://127.0.0.1:57015/api/players/{username}' --header 'Content-Type:application/json' | python3 -m json.tool
```
Add a user to the database. You can specify ```name: str```, ```gender: str```, ```email: str```, ```avatar: str```, ```games: int```, ```wins: int```, ```time_in_game: int```:
```
curl --location --request POST 'http://127.0.0.1:57015/api/players/insert' --header 'Content-Type:application/json' --data-raw '{"name": "new_player"}' | python3 -m json.tool
```
Update user information:
```
curl --location --request PUT 'http://127.0.0.1:57015/api/players/update' --header 'Content-Type:application/json' --data-raw '{"name": "new_player", "email": "new_player@gmail.com"}' | python3 -m json.tool
```
Upload user pic (default default.jpg from rest/images):
```
curl -i -X POST -H "Content-Type: multipart/form-data" -F "file=@/Users/{name}/new_player.jpg" http://127.0.0.1:57015/api/players/images/new_player
```
Statistics is generated by asynchronous request (using rabbitMQ) on request; pdf is generated using `reportlab` (in the `pics` folder, there is an example picture of how the statistics pdf should look like):
```
curl --location --request POST 'http://127.0.0.1:57015/api/players/statistics/new_player' --header 'Content-Type:application/json'
```
Delete user:
```
curl --location --request DELETE 'http://127.0.0.1:57015/api/players/delete/new_player' --header 'Content-Type:application/json' | python3 -m json.tool
```
