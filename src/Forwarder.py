import socket
import threading

class TcpForwarder:
    def __init__(self, local_port: int, target_ip: str, target_port: int):
        self.local_port = local_port
        self.target_ip = target_ip
        self.target_port = target_port
        self.server = None

    #转发数据流
    def relay(self, src, dst):

        try:
            while True:
                data = src.recv(4096)
                if not data:
                    print("连接已关闭")
                    break  # 对端关闭连接
                dst.sendall(data)
        except Exception as e:
            print(f"转发数据时出错: {e}")
        finally:
            src.close()
            dst.close()

    #处理客户端连接并转发流量到目标地址
    def handle_client(self, client_socket):
        try:
            target = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            target.connect((self.target_ip, self.target_port))
            print(f"客户端 {client_socket.getpeername()} 已连接，正在转发到 {self.target_ip}:{self.target_port}")

            # 创建线程转发数据
            thread1 = threading.Thread(target=self.relay, args=(client_socket, target))
            thread2 = threading.Thread(target=self.relay, args=(target, client_socket))
            thread1.start()
            thread2.start()

            # 等待线程完成
            thread1.join()
            thread2.join()
        except Exception as e:
            print(f"处理客户端时出错: {e}")
        finally:
            client_socket.close()
            target.close()

    #启动端口转发服务
    def start(self):
        try:
            self.server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.server.bind(('0.0.0.0', self.local_port))  # 监听本地端口
            self.server.listen(5)
            print(f"转发服务已启动，监听本地端口:{self.local_port}，目标:{self.target_ip}:{self.target_port}")

            while True:
                client_sock, addr = self.server.accept()
                threading.Thread(target=self.handle_client, args=(client_sock,)).start()
        except Exception as e:
            print(f"启动转发服务时出错: {e}")
        finally:
            if self.server:
                self.server.close()
