import socket

def udp_server(host='0.0.0.0', port=9999):
    # 创建 UDP 套接字
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    server_socket.bind((host, port))

    print(f"UDP服务器正在监听 {host}:{port}")
    try:
        while True:
            # 接收数据
            data, addr = server_socket.recvfrom(4096)
            print(f"收到来自 {addr} 的数据: {data.decode('utf-8')}")

            # 回传响应
            server_socket.sendto(b"ACK: " + data, addr)
    except KeyboardInterrupt:
        print("\n服务器已终止")
    finally:
        server_socket.close()

if __name__ == "__main__":
    udp_server(port=8888)  # 将端口改为需要测试的端口
