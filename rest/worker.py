import pika, sys, os
import json
from helper import create_pdf
import logging

def main():
    connection = pika.BlockingConnection(pika.ConnectionParameters(host="rabbitmq"))
    channel = connection.channel()
    channel.queue_declare(queue='pdf_queue', durable=True)
    logging.info(' [*] Waiting for messages. To exit press CTRL+C')

    def callback(ch, method, properties, body):
        data = json.loads(body)
        logging.info(" [x] Received %r" % data)
        create_pdf(data)
        ch.basic_ack(delivery_tag=method.delivery_tag)

    channel.basic_qos(prefetch_count=1) #not to give more than one message to a worker at a time
    channel.basic_consume(queue='pdf_queue', on_message_callback=callback)
    channel.start_consuming()

if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    try:
        main()
    except KeyboardInterrupt:
        print('Interrupted')
        try:
            sys.exit(0)
        except SystemExit:
            os._exit(0)