import sqlite3
from reportlab.pdfgen.canvas import Canvas
import json
import logging

DB_PATH = './players.db' # Update this path accordingly

def connect_to_db():
    conn = sqlite3.connect(DB_PATH)
    return conn

def create_db_table():
    try:
        conn = connect_to_db()
        cur = conn.cursor()
        cur.execute('''
            CREATE TABLE IF NOT EXISTS "profile" (
                "name" TEXT PRIMARY KEY, 
                "gender" TEXT NOT NULL,
                "email" TEXT NOT NULL,
                "avatar" TEXT NULL,
                "games" INTEGER DEFAULT 0,
                "wins" INTEGER DEFAULT 0,
                "time_in_game" FLOAT DEFAULT 0
            );
        ''')
        conn.commit()
        print("Table successfully crated.", flush=True)
    except:
        print("Table creation failed.", flush=True)
    finally:
        conn.close()

# sorry
def fill_in(player, prev_player):
    if "gender" not in player:
        player["gender"] = prev_player["gender"]
    if "email" not in player:
        player["email"] = prev_player["email"]
    if "avatar" not in player:
        player["avatar"] = prev_player["avatar"]
    if "games" not in player:
        player["games"] = prev_player["games"]
    if "wins" not in player:
        player["wins"] = prev_player["wins"]
    if "time_in_game" not in player:
        player["time_in_game"] = prev_player["time_in_game"]

def insert_player(player):
    inserted_player = None
    default_player = {"gender":"none", "email":"none", "avatar":"default.jpg",
                      "games":0, "wins":0, "time_in_game":0}
    fill_in(player, default_player)
    try:
        conn = connect_to_db()
        cur = conn.cursor()
        cur.execute("INSERT INTO profile (name, gender, email, avatar, games, wins, time_in_game) "
                    "SELECT \"{}\", \"{}\", \"{}\", \"{}\", {}, {}, {} "
                    "WHERE NOT EXISTS(SELECT 1 FROM profile WHERE name = \"{}\")".format(player['name'],   
                    player['gender'], player['email'], player['avatar'],
                    player['games'], player['wins'], player['time_in_game'], player['name']))
        conn.commit()
        inserted_player = get_player_by_name(player["name"])
    except:
        conn.rollback()
        inserted_player = None
    finally:
        conn.close()
    return inserted_player

def get_players():
    players = None
    try:
        conn = connect_to_db()
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        cur.execute("SELECT * FROM profile")
        rows = cur.fetchall()
        players = []
        for row in rows:
            player = {}
            player["name"] = row["name"]
            player["gender"] = row["gender"]
            player["email"] = row["email"]
            player["avatar"] = row["avatar"]
            player["games"] = row["games"]
            player["wins"] = row["wins"]
            player["time_in_game"] = row["time_in_game"]
            players.append(player)
    except:
        players = None
    finally:
        conn.close()
    return players


def get_player_by_name(username):
    player = None
    try:
        conn = connect_to_db()
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        cur.execute("SELECT * FROM profile WHERE name = \"{}\"".format(username))
        row = cur.fetchone()

        player = {}
        player["name"] = row["name"]
        player["gender"] = row["gender"]
        player["email"] = row["email"]
        player["avatar"] = row["avatar"]
        player["games"] = row["games"]
        player["wins"] = row["wins"]
        player["time_in_game"] = row["time_in_game"]
    except:
        player = None
    finally:
        conn.close()
    return player

def update_player(player):
    updated_player = None
    cur_player = get_player_by_name(player["name"])
    if cur_player is None:
        return None
    fill_in(player, cur_player)
    try:
        conn = connect_to_db()
        cur = conn.cursor()
        cur.execute("UPDATE profile "
                    "SET name = \"{}\", gender = \"{}\", email = \"{}\", "
                    "avatar = \"{}\", games = {}, wins = {}, time_in_game = {} "
                    "WHERE name = \"{}\"".format(player["name"], player["gender"],
                    player["email"], player["avatar"], player["games"], 
                    player["wins"], player["time_in_game"], player["name"]))
        conn.commit()
        updated_player = get_player_by_name(player["name"])
    except:
        conn.rollback()
        updated_player = None
    finally:
        conn.close()
    return updated_player

def delete_player(username):
    message = {}
    try:
        conn = connect_to_db()
        print("DELETE from profile WHERE name = \"{}\"".format(username))
        conn.execute("DELETE from profile WHERE name = \"{}\"".format(username))
        conn.commit()
        message["is_deleted"] = True
    except:
        conn.rollback()
        message["is_deleted"] = False
    finally:
        conn.close()
    return message

def create_pdf(player):
    if player is None:
        logging.info("{}".format(player))
        c = Canvas("./statistics_new/{}.pdf".format(player["name"]), pagesize=(595, 210))
        c.setFont("Helvetica", 20, leading = None)
        c.drawString(10, 180, "Player doesn't exist.".format({player["name"]}))
        c.save()
    else:
        print(player)
        c = Canvas("./statistics_new/{}.pdf".format(player["name"]), pagesize=(595, 210))
        c.setFont("Helvetica", 20, leading = None)
        c.drawString(10, 180, "Username: {}".format(player["name"]))
        c.drawString(10, 146, "Gender: {}".format(player["gender"]))
        c.drawString(10, 112, "Email: {}".format(player["email"]))
        c.drawString(10, 78, "Games played: {}".format(player["games"]))
        c.drawString(10, 44, "Victories: {}".format(player["wins"]))
        c.drawString(10, 10, "Time in game: {}".format(player["time_in_game"]))
        c.drawImage("./images/{}".format(player["avatar"]), x=300, y=10, width=190, height=190)
        c.save()