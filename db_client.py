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
    if not msg or msg[0] != "TXT" or msg[1] != "REQUEST_USERNAME":
        print("[CLIENT] Invalid response from server.")
        sock.close()
        return

    username = input("Enter your name: ").strip()
    sendtext(sock, username)

    msg = recieve(sock)
    if not msg or msg[0] != "TXT":
        print("[CLIENT] Failed to receive DB list and prompt.")
        sock.close()
        return
    print(msg[1])
    db_name = input("DB name: ").strip()
    sendtext(sock, db_name)

    msg = recieve(sock)
    if not msg or msg[0] != "TXT":
        print("[CLIENT] Failed to receive UID.")
        sock.close()
        return
    user_id = msg[1].strip()
    print(f"[CLIENT] Your user ID is {user_id}")

    try:
        while True:
            query = multiline_command().strip()
            if query == "exit":
                sendtext(sock, "exit")
                break
            sendtext(sock, query)
            msg = recieve(sock)
            if msg and msg[0] == "TXT":
                print("Response:")
                print(msg[1])
            else:
                print("[CLIENT] Unexpected response or no response from server.")
    except Exception as e:
        print(f"[CLIENT] Error with {HOST}:{PORT}: {e}")
    finally:
        sock.close()
        print("[CLIENT] Disconnected.")


main()
