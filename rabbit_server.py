import pika, sys, os
from pika.exchange_type import ExchangeType
import pkg.game_pb2 as game_pb2
import pkg.game_pb2_grpc as game_pb2_grpc
import grpc
import logging

HOST = "0.0.0.0"
PORT = "8080"

HOST_grpc = "0.0.0.0"
PORT_grpc = "51075"

class RabbitMQServer:
    def __init__(self, stub:game_pb2_grpc.MafiaServiceStub):
        self.stub = stub
        self.connection = pika.BlockingConnection(pika.ConnectionParameters(host="rabbitmq"))
        self.channel_rcv = self.connection.channel()
        self.channel_rcv.exchange_declare(exchange='receiver', exchange_type=ExchangeType.fanout)
        self.channel_rcv.queue_declare(queue='receiver', exclusive=True)
        self.channel_rcv.basic_consume(queue='receiver',
                                    auto_ack=True,
                                    on_message_callback=self.on_message_received)
        self.channel_rcv.queue_bind(exchange='receiver', queue='receiver')

        self.channel_chat = self.connection.channel()
        self.channel_chat.exchange_declare(exchange='chat', exchange_type=ExchangeType.fanout)

    def on_message_received(self, ch, method, properties, body):
        logging.info("server got message {}".format(body))
        self.channel_chat.basic_publish(exchange='chat', routing_key='', body=body)

    def close(self):
        self.connection.close()

if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    listen_addr = "{}:{}".format(HOST_grpc, PORT_grpc)
    channel = grpc.insecure_channel(listen_addr)
    stub = game_pb2_grpc.MafiaServiceStub(channel)
    try:
        rabbit_server = RabbitMQServer(stub)
        logging.info("Started rabbitMQ server.")
        rabbit_server.channel_rcv.start_consuming()
    except KeyboardInterrupt:
        print('Interrupted')
        try:
            sys.exit(0)
        except SystemExit:
            os._exit(0)