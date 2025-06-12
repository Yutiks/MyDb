import socket
from messaging_protocol import sendtext, recieve
from main import multiline_command

HOST = "62.60.186.238"
PORT = 5089


def main():
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.connect((HOST, PORT))
    print("[CLIENT] Connected to DB server.")

    msg = recieve(sock)
    if not msg or msg[1] != "REQUEST_USERNAME":
        sock.close()
        return

    username = input("Enter your name: ").strip()
    sendtext(sock, username)

    msg = recieve(sock)
    if not msg:
        sock.close()
        return

    user_id = msg[1].strip()
    print(f"[CLIENT] Your user ID is {user_id}")

    while True:
        query = multiline_command().strip()
        if query == "exit":
            sendtext(sock, "exit")
            break
        sendtext(sock, query)
        msg = recieve(sock)
        if msg[0] == "TXT":
            print("Response:")
            print(msg[1])
        else:
            print("[CLIENT] Unexpected response type:", msg[0])
    sock.close()
    print("[CLIENT] Disconnected.")


main()
