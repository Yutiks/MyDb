""" header = (size<5;type=3;filename=10) """

HEADERSIZE = 21
TYPES = ["TXT", "AUD", "IMG"]


def check_recieve(sock, size: int):
    received = b""
    while len(received) != size:
        recv = sock.recv(size)
        if recv:
            received += recv
        else:
            raise ConnectionError("received is less than expected")
    return received


def check_header(header: str) -> list:
    parts = header[1:-1].split(";")
    if len(parts) != 3:
        raise ConnectionError("Header does not have 3 parts")
    size, type, filename = parts
    if size.isdigit() and type in TYPES:
        return [size, type, filename]
    else:
        raise ConnectionError("Header is incorrect")


def recieve(sock):
    header = check_recieve(sock, HEADERSIZE)
    size, type, filename = check_header(header.decode())
    size = int(size)
    recv = check_recieve(sock, size)
    if type in ["AUD", "IMG"]:
        with open(f"received/{filename}", "wb") as f:
            f.write(recv)
        return [type, filename]
    elif type == "TXT":
        return [type, recv.decode()]


def sendfile(sock, filename, type):
    filename = filename[:10]
    gaps = "#" * (10 - len(filename))
    with open(filename, "rb") as f:
        filedata = f.read()

    _send(sock, type, f"{gaps}{filename}", filedata)


def sendtext(sock, message: str):
    _send(sock, "TXT", "#"*10, message.encode())


def _send(sock, type, filename="", message=b""):
    size = len(str(len(message)))
    gaps = "0" * (4 - size)
    size_str = f"{gaps}{len(message)}"
    header = f"({size_str};{type};{filename})"
    sock.sendall(header.encode())
    sock.sendall(message)
