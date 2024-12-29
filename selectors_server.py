import selectors
import socket
import types

# Создаем селектор
sel = selectors.DefaultSelector()

# Функция для обработки нового подключения
def accept_connection(sock):
    conn, addr = sock.accept()  # Принимаем новое соединение
    print(f"Connected by {addr}")
    conn.setblocking(False)  # Устанавливаем неблокирующий режим
    # Создаем объект для хранения данных клиента
    data = types.SimpleNamespace(addr=addr, inb=b"", outb=b"")
    # Регистрируем сокет клиента для чтения
    sel.register(conn, selectors.EVENT_READ, data=data)

# Функция для обработки данных клиента
def handle_client(key, mask):
    sock = key.fileobj  # Сокет клиента
    data = key.data  # Данные клиента
    if mask & selectors.EVENT_READ:  # Если сокет готов к чтению
        recv_data = sock.recv(1024)  # Читаем данные
        if recv_data:
            print(f"Received {recv_data} from {data.addr}")
            data.outb += recv_data  # Подготавливаем ответ
        else:
            print(f"Closing connection to {data.addr}")
            sel.unregister(sock)  # Убираем из селектора
            sock.close()
    if mask & selectors.EVENT_WRITE and data.outb:  # Если сокет готов к записи
        print(f"Sending {data.outb} to {data.addr}")
        sent = sock.send(data.outb)  # Отправляем данные
        data.outb = data.outb[sent:]  # Удаляем отправленные данные

# Настройка серверного сокета
host, port = '127.0.0.1', 65432
server_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
server_sock.bind((host, port))
server_sock.listen()
print(f"Server started on {host}:{port}")
server_sock.setblocking(False)  # Устанавливаем неблокирующий режим
sel.register(server_sock, selectors.EVENT_READ, data=None)  # Регистрируем серверный сокет

# Основной цикл
try:
    while True:
        events = sel.select(timeout=None)  # Ожидаем события
        for key, mask in events:
            if key.data is None:
                accept_connection(key.fileobj)  # Обрабатываем новое подключение
            else:
                handle_client(key, mask)  # Обрабатываем данные клиента
except KeyboardInterrupt:
    print("Server shutting down...")
finally:
    sel.close()
