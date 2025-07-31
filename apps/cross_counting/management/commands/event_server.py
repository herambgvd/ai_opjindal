import socket
import select
import json
from urllib.parse import urlparse, parse_qs
import time
import paho.mqtt.client as mqtt
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Start a TCP server to handle HTTP requests and publish to MQTT"

    def add_arguments(self, parser):
        try:
            default_host = socket.gethostbyname(socket.gethostname())
        except socket.gaierror:
            default_host = "127.0.0.1"

        parser.add_argument(
            '--host',
            type=str,
            default=default_host,
            help="Host IP address for the TCP server (default: system IP or 127.0.0.1 if resolution fails)."
        )
        parser.add_argument(
            '--port',
            type=int,
            default=4000,
            help="Port number for the TCP server (default: 4000)."
        )

    def handle(self, *args, **options):
        host = options['host']
        port = options['port']

        # MQTT_BROKER = "mqtt.geniusvision.in"
        MQTT_BROKER = "0.0.0.0"
        MQTT_PORT = 1883
        MQTT_TOPIC = "alert"

        clients = {}
        mqtt_client = None  # Ensure it's accessible in `finally`

        MAX_RETRIES = 3

        def safe_publish(mqtt_client, topic, payload):
            for attempt in range(1, MAX_RETRIES + 1):
                if not mqtt_client.is_connected():
                    self.stdout.write("Reconnecting to MQTT broker...")
                    try:
                        mqtt_client.reconnect()
                    except Exception as e:
                        self.stderr.write(f"Failed to reconnect to MQTT broker: {e}")
                        time.sleep(1)
                        continue

                result = mqtt_client.publish(topic, payload)
                if result.rc == 0:
                    self.stdout.write("Payload published to MQTT successfully.")
                    return True
                self.stderr.write(f"Publish failed (Attempt {attempt}/{MAX_RETRIES}), Result code: {result.rc}")
                time.sleep(1)
            self.stderr.write("Exceeded maximum retries for publishing to MQTT.")
            return False

        def parse_http_message(message):
            try:
                lines = message.split("\r\n")
                request_line = lines[0]
                method, path, http_version = request_line.split()
                headers = {}
                body = ""

                for i in range(1, len(lines)):
                    if lines[i] == "":
                        body = "\r\n".join(lines[i + 1:])
                        break
                    key, value = lines[i].split(":", 1)
                    headers[key.strip()] = value.strip()

                return method, path, headers, body
            except ValueError:
                self.stderr.write("Error parsing HTTP message.")
                return None, None, None, None

        def handle_request(method, path, headers, body, addr, mqtt_client):
            self.stdout.write(f"Received {method} request from {addr}")

            if method == "POST":
                self.stdout.write(f"Body: {body}")
                if not body:
                    self.stderr.write("Empty body received, skipping publish.")
                    return

                try:
                    if not safe_publish(mqtt_client, MQTT_TOPIC, body):
                        self.stderr.write("Failed to publish payload to MQTT after retries.")
                except Exception as e:
                    self.stderr.write(f"Error publishing to MQTT: {e}")

        def start_server():
            nonlocal mqtt_client  # allow access to outer scope
            mqtt_client = mqtt.Client(protocol=mqtt.MQTTv311)
            mqtt_client.enable_logger()

            try:
                mqtt_client.connect(MQTT_BROKER, MQTT_PORT)
                mqtt_client.loop_start()
                self.stdout.write(f"Connected to MQTT broker at {MQTT_BROKER}:{MQTT_PORT}")
            except Exception as e:
                self.stderr.write(f"Failed to connect to MQTT broker: {e}")
                return

            server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            server_socket.bind((host, port))
            server_socket.listen(5)

            self.stdout.write(f"Server started on {host}:{port}")

            sockets_list = [server_socket]

            while True:
                read_sockets, _, exception_sockets = select.select(sockets_list, [], sockets_list)

                for notified_socket in read_sockets:
                    if notified_socket == server_socket:
                        conn, addr = server_socket.accept()
                        self.stdout.write(f"Accepted new connection from {addr}")
                        sockets_list.append(conn)
                        clients[conn] = addr
                    else:
                        try:
                            buffer = []
                            while True:
                                chunk = notified_socket.recv(4096)
                                if not chunk:
                                    break
                                buffer.append(chunk)

                            if not buffer:
                                self.stdout.write(f"Client {clients.get(notified_socket)} disconnected.")
                                sockets_list.remove(notified_socket)
                                del clients[notified_socket]
                                continue

                            full_message = b"".join(buffer).decode()
                            method, path, headers, body = parse_http_message(full_message)

                            if method and path:
                                handle_request(method, path, headers, body, clients[notified_socket], mqtt_client)
                            else:
                                self.stderr.write("Malformed HTTP message received.")

                            notified_socket.sendall(b"HTTP/1.1 200 OK\r\nContent-Length: 12\r\n\r\nAcknowledged")

                        except ConnectionResetError as e:
                            self.stderr.write(f"Client {clients.get(notified_socket)} disconnected unexpectedly: {e}")
                            sockets_list.remove(notified_socket)
                            if notified_socket in clients:
                                del clients[notified_socket]

                        except Exception as e:
                            self.stderr.write(f"Error handling client data: {e}")
                            if notified_socket in sockets_list:
                                sockets_list.remove(notified_socket)
                            if notified_socket in clients:
                                del clients[notified_socket]

                for notified_socket in exception_sockets:
                    sockets_list.remove(notified_socket)
                    if notified_socket in clients:
                        del clients[notified_socket]

        try:
            start_server()
        except KeyboardInterrupt:
            self.stdout.write("\nServer shutting down gracefully.")
        except Exception as e:
            self.stderr.write(f"Server encountered an error: {e}")
        finally:
            for client in clients:
                client.close()
            if mqtt_client:
                mqtt_client.disconnect()
