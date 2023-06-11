from flask import Flask, request, jsonify, abort, send_from_directory
from helper import *
import logging
import pika
import json

HOST = "0.0.0.0"
PORT = "57015"

def create_app() -> Flask:
    """
    Create flask application
    """
    app = Flask(__name__)

    @app.route('/api/players', methods=['GET'])
    def api_get_players():
        logging.info("GET info on players")
        response = get_players()
        if response is None:
            abort(404)
        return jsonify(response)

    @app.route('/api/players/<string:username>', methods=['GET'])
    def api_get_player_by_name(username):
        logging.info("GET info on player \"{}\".".format(username))
        response = get_player_by_name(username)
        if response is None:
            abort(404)
        return jsonify(response)

    @app.route('/api/players/insert',  methods = ['POST'])
    def app_insert_player():
        player = request.get_json()
        logging.info("INSERT player: \"{}\".".format(player))
        response = insert_player(player)
        if response is None:
            abort(404)
        return jsonify(response)

    @app.route('/api/players/update',  methods = ['PUT'])
    def api_update_player():
        player = request.get_json()
        print(player)
        logging.info("UPDATE player: \"{}\".".format(player))
        response = update_player(player)
        if response is None:
            abort(404)
        return jsonify(response)

    @app.route('/api/players/delete/<string:username>',  methods = ['DELETE'])
    def api_delete_user(username):
        logging.info("DELETE player \"{}\".".format(username))
        response = delete_player(username)
        if response['is_deleted'] == False:
            abort(404)
        return jsonify(response)
    
    @app.route("/api/players/images/<string:name>", methods=["POST"])
    def upload_file(name):
        file = request.files['file']
        avatar = "default.jpg"
        if file is not None:
            file.save("./images/{}.jpg".format(name))
            avatar = "{}.jpg".format(name)
        print(file)
        try:
            update_player({"name":name, "avatar":avatar})
        except:
            abort(404)
        return "File successfully uploaded."
    
    @app.route('/api/players/statistics/<string:username>', methods=['POST'])
    def api_create_pdf(username):
        connection = pika.BlockingConnection(pika.ConnectionParameters(host="rabbitmq"))
        channel = connection.channel()
        channel.confirm_delivery()
        channel.queue_declare(queue='pdf_queue', durable=True)
        try:
            create_pdf({"name":"{}__".format(username), "id":username})
            channel.basic_publish(
                exchange='',
                routing_key='pdf_queue',
                body=json.dumps({"name":username, "id":username}),
                properties=pika.BasicProperties(
                    delivery_mode=pika.spec.PERSISTENT_DELIVERY_MODE
            ))
            print('Pdf generation was confirmed.')
            return "It will be available by the link http://127.0.0.1:{}/statistics/{}.pdf\n".format(PORT, username), 200
        except pika.exceptions.UnroutableError:
            print("Couldn't generate pdf.")
            abort(404)
    
    @app.route("/statistics/<path:name>", methods=["GET"])
    def api_publish_report(name):
        return send_from_directory("statistics_new", name)
    return app
    
app = create_app()

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    create_db_table()
    app.run(host=HOST, port=PORT) #run app