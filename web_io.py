import os
import socket
import sys
import ssl
import eventlet
from eventlet import wsgi
import logging
from flask import Flask
from flask_socketio import SocketIO
from flask_uploads import UploadSet, configure_uploads
from pydispatch import dispatcher

# Patch system modules to be greenthread-friendly
eventlet.monkey_patch()

# Another monkey patch to avoid annoying (and useless?) socket pipe warnings when users disconnect
import socketserver
from wsgiref import handlers
socketserver.BaseServer.handle_error = lambda *args, **kwargs: None
handlers.BaseHandler.log_exception = lambda *args, **kwargs: None

# Turn off more annoying log messages that aren't helpful.
log = logging.getLogger('werkzeug')
log.setLevel(logging.ERROR)

app = Flask(__name__, static_folder='webpage')
app.config['SECRET_KEY'] = 'Big Whoop is an amusement park... or is it?!'
app.config['UPLOADED_JSON_DEST'] = '/tmp/'

socketio = SocketIO(app, async_mode='eventlet', ping_timeout=30, logger=False, engineio_logger=False)

# Configure server to accept uploads of JSON files
docs = UploadSet('json', ('json'))
configure_uploads(app, docs)

class WebServer:
    @app.route("/")
    def index():
        return app.send_static_file('index.html')

    def broadcast(self, id, data):
        with app.app_context():
            try:
                socketio.emit(id, data, broadcast=True)
            except Exception as e:
                print(f"Broadcast error: {e}")

    @app.route('/<path:path>')
    def static_proxy(path):
        return app.send_static_file(path)

    @socketio.on('onConnect')
    def connectEvent(msg):
        dispatcher.send(signal='connectEvent')

    @socketio.on('onKeyPress')
    def webKeyEvent(data):
        dispatcher.send(signal="keyEvent", key=data["keyVal"], val=int(data["val"]))
        return data["keyVal"]

    def __init__(self):
        self.server = eventlet.spawn(self.run_server)

    def run_server(self):
        try:
            # Start HTTP server on port 80 in a new green thread
            print("Starting HTTP server on port 80...")
            eventlet.spawn_n(socketio.run, app, host='0.0.0.0', port=80)

            # HTTPS setup
            print("Starting HTTPS server on port 443...")
            
            # Create an SSL context
            ssl_context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
            ssl_context.load_cert_chain(certfile='server.crt', keyfile='server.key')

            # Create a new SSL socket for HTTPS
            https_socket = eventlet.wrap_ssl(eventlet.listen(('0.0.0.0', 443)),
                                             certfile='server.crt',
                                             keyfile='server.key',
                                             server_side=True)

            # Start HTTPS server using the SSL socket
            eventlet.spawn_n(wsgi.server, https_socket, app)

            # Keep the main thread alive to ensure the servers keep running
            eventlet.sleep(10**6)

        except Exception as e:
            print(f"Error running server: {e}")

    def shutdown(self):
        print("Shutting down server...")
        socketio.stop()
        # Note: You might need to stop any running threads/processes here as well.
