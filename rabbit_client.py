import pika, sys, os
from pika.exchange_type import ExchangeType

class RabbitMQClient:
    def __init__(self, username:str):
        self.connection = pika.BlockingConnection(pika.ConnectionParameters(host="0.0.0.0", port="5672"))
        self.channel = self.connection.channel()
        self.channel.queue_declare(queue='chat_{}'.format(username), exclusive = True)
        self.channel.queue_bind(exchange='chat', queue='chat_{}'.format(username))

    def close(self):
        self.connection.close()