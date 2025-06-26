import socket
import threading
import os
import json
import random
from main import MyDB
from messaging_protocol import recieve, sendtext

HOST = "127.0.0.1"
PORT = 5076
USERS_FILE = "databases/users.json"

with open(USERS_FILE, 'r', encoding='utf-8') as f:
    users = json.load(f)


def save_users():
    with open(USERS_FILE, 'w', encoding='utf-8') as file:
        json.dump(users, file, ensure_ascii=False, indent=4)


def generate_unique_id():
    existing = {info["uid"] for info in users.values()}
    while True:
        uid = str(random.randint(1000, 9999))
        if uid not in existing:
            return uid


def handle_client(clt_sock, address):
    print(f"[SERVER] Connection from {address}")
    with clt_sock:
        try:
            sendtext(clt_sock, "REQUEST_USERNAME")
            msg = recieve(clt_sock)
            if msg is None or msg[0] != "TXT":
                print(f"[SERVER] Expected TXT username, got {msg!r}")
                return
            username = msg[1].strip()
            print(f"[SERVER] Received username: {username!r}")

            if username in users:
                uid = users[username]["uid"]
                db_list = users[username]["databases"]
                print(f"[SERVER] Existing user '{username}', ID={uid}")
            else:
                uid = generate_unique_id()
                users[username] = {"uid": uid, "databases": ["default"]}
                db_list = users[username]["databases"]
                save_users()
                print(f"[SERVER] New user '{username}' registered with ID={uid}")

            sendtext(clt_sock, f"Your databases: {', '.join(db_list)}\nEnter DB name (existing or new):")
            msg = recieve(clt_sock)
            if not msg or msg[0] != "TXT":
                return

            db_name = msg[1].strip()
            if db_name not in db_list:
                db_list.append(db_name)
                save_users()

            db_path = f"databases/{uid}_{db_name}.json"
            if not os.path.exists(db_path):
                with open(db_path, 'w', encoding='utf-8') as file_:
                    json.dump({}, file_, ensure_ascii=False, indent=2)
                print(f"[SERVER] Created DB file: {db_path}")

            db = MyDB(db_path)
            sendtext(clt_sock, uid)
            print(f"[SERVER] {username} ({uid}) is ready to send queries.")

            while True:
                msg = recieve(clt_sock)
                if msg is None:
                    print(f"[SERVER] {username} ({uid}) disconnected abruptly")
                    break
                if msg[0] != "TXT":
                    sendtext(clt_sock, "Error: only TXT supported")
                    continue
                query = msg[1].strip()
                print(f"[{username} ({uid})] Query: {query!r}")
                if query.lower() == "exit":
                    print(f"[SERVER] {username} ({uid}) requested exit")
                    break
                response = db.process_command(query)
                if not isinstance(response, str):
                    response = str(response)
                sendtext(clt_sock, response)
        # except Exception as e:
        #     print(f"[SERVER] Error with {address}: {e}")
        finally:
            clt_sock.close()
            print(f"[SERVER] Connection {address} closed.")


def start_server():
    server_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_sock.bind((HOST, PORT))
    server_sock.listen()
    print(f"[SERVER] working host {HOST} port: {PORT}")
    try:
        while True:
            client_sock, client_addr = server_sock.accept()
            thread = threading.Thread(target=handle_client, args=(client_sock, client_addr))
            thread.start()
    except Exception as e:
        print(f"[SERVER] Error with {HOST, PORT}: {e}")
    finally:
        server_sock.close()
        print(f"[SERVER] Server on {HOST}:{PORT} closed.")


start_server()
