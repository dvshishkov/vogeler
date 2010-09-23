import json

import vogeler.log as logger
import vogeler.exceptions as exceptions
import vogeler.conf as conf
from vogeler.messaging import amqp

log = logger.setup_logger(logLevel='DEBUG', logFile=None, name='vogeler-client')

class VogelerClient(object):
    """
    Base class for operating as a Vogeler client instance

    :param none callback_function: Callback function to use when messages are recieved

    .. attribute:: callback_function

        External callback used for processing messages

    .. attribute:: ch

        an instance of :class:`amqplib.client_0_8.channel.Channel`

    .. attribute:: queue

        an instance of :class:`amqplib.client_0_8.channel.Queue`

    :raises: :class:`vogeler.exceptions.VogelerClientConnectionException`

    """
    def __init__(self, callback_function=None, **kwargs):
        try:
            self._configure(kwargs["config"])
            if self._config.has_option('amqp', 'dsn'):
                _dsn = self._config.get('amqp', 'dsn')
        except KeyError, e:
            _dsn = kwargs["dsn"]

        try:
            self.ch, self.queue = amqp.setup_client(_dsn)
            self.callback_function = callback_function
        except Exception, e:
            log.fatal("Error connecting to %s" % _dsn)
            raise exceptions.VogelerClientConnectionException(e)

    def _configure(self, config_file=None):
        if config_file is not None:
            self._config = conf.configure(cfg=config_file)

    def callback(self, msg):
        """
        Wrapper method for handling callbacks on message reciept.
        The message body is JSON decoded and passed up to :attr:`callback_function`

        :param msg: Instance of :class:`amqplib.client_0_8.basic_message.Message`

        """
        log.info("Message recieved")
        try:
            message = json.loads(msg.body)
            log.info("Message decoded")
        except Exception, e:
            log.warn("Message not in JSON format")
            raise exceptions.VogelerClientPluginException(e)

        if(self.callback_function):
            self.callback_function(message)

    def monitor(self):
        """
        Method for watching a queue infinitely for messages

        :raises: :class:`vogeler.exceptions.VogelerClientException`
        """
        try:
            log.info("Vogeler(Client) is starting up")
            self.ch.basic_consume(self.queue, callback=self.callback, no_ack=True)
            log.info("Vogeler(Client) has started")
        except Exception, e:
            log.fatal("Error Consuming queue")
            raise exceptions.VogelerClientConnectionException(e)

        while self.ch.callbacks:
            self.ch.wait()

    def message(self, message, durable=True):
        """
        Method for sending a message via the messaging system

        :param message: The message to send.

        :param bool durable: Sets the durable flag on the message causing it to persists

        .. attribute:: msg

            instance of :class:`amqplib.client_0_8.basic_message.Message` wrapped in JSON

        :raises: :class:`vogeler.exceptions.VogelerClientException`

        """
        try:
            log.debug("Vogeler(Client) is sending a message")
            msg = amqp.amqp.Message(json.dumps(message))
            if durable == True:
                msg.properties['delivery_mode'] = 2
            self.ch.basic_publish(msg, exchange=amqp.master_exchange)
            log.debug("Vogeler(Client) finished sending message")
        except Exception, e:
            log.fatal("Error publishing message to the queue")
            raise exceptions.VogelerClientConnectionException(e)

    def close(self):
        """Close the channel with the broker"""
        log.info("Closing channel")
        self.ch.close()

# vim: set ts=4 et sw=4 sts=4 sta filetype=python :