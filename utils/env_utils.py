import socket


def is_oracle_instance() -> bool:
    hostname = socket.gethostname()
    return "instance" in hostname
