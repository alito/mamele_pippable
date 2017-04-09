import os
import logging
import socket
import tempfile

class Socket(object):
    """
    Thin wrapper around a socket connection to make dealing with them more sane
    """

    def __init__(self):
        # leftover from previous
        self._leftover_message = ''

        # mostly from https://docs.python.org/2/howto/sockets.html
        self.connection = None

        self._we_created = False

    def start_server(self):

        # make a directory where we are going to stick the socket
        directory = tempfile.mkdtemp(prefix="mamelesocket")

        # create a UNIX, STREAMing socket
        self.socket = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        # bind to a location
        self.socket_path = os.path.join(directory, 'socket')
        self.socket.bind(self.socket_path)
        self._we_created = True
        # become a server socket but listen to only one connection
        self.socket.listen(1)

        return self.socket_path

    def start_client(self, socket_path):
        self.connection = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        self.connection.connect(socket_path)


    def wait_for_connection(self):
        """
        Server-side wait for a connection
        """
        self.connection, _ = self.socket.accept()

    def receive_until_character(self, stopper):
        """
        Receive until we see the stopper character
        """

        where = self._leftover_message.find(stopper)
        if where >= 0:
            message = self._leftover_message[:where+1]
            self._leftover_message = self._leftover_message[where+1:]
            return message

        parts = [self._leftover_message]
        while True:
            try:
                next_chunk = self.connection.recv(4096)
                where = next_chunk.find(stopper)
                if where >= 0:
                    parts.append(next_chunk[:where+1])
                    self._leftover_message = next_chunk[where+1:]
                    break
                else:
                    parts.append(next_chunk)
            except Exception as error:
                logging.error("issue receiving: %s" % error)


        return ''.join(parts)

    def receive_bytes(self, count):
        received = len(self._leftover_message)
        if received >= count:
            message = self._leftover_message[:count]
            self._leftover_message = self._leftover_message[count:]
            return message


        parts = [self._leftover_message]
        left = count - received
        while True:
            try:
                next_chunk = self.connection.recv(4096)
                length = len(next_chunk)
                if length >= left:
                    self._leftover_message = next_chunk[left:]
                    parts.append(next_chunk[:left])
                    break
                else:
                    left -= length
                    parts.append(next_chunk)
            except Exception as error:
                logging.error("issue receiving: %s" % error)


        return ''.join(parts)


    def send(self, message):
        return self.connection.sendall(message)


    def destroy(self):
        self.connection.shutdown(socket.SHUT_RDWR)
        self.connection.close()

        if self._we_created:
            self.socket.shutdown(socket.SHUT_RDWR)
            self.socket.close()            
            try:
                os.remove(self.socket_path)
                os.rmdir(os.path.dirname(self.socket_path))
            except (OSError, IOError) as error:
                logging.error("Had problems removing the socket or the surrounding temporary directory: %s" % error)
