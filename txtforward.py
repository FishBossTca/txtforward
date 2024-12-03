import socket
import threading
import dns.resolver

# 解析域名的 TXT 记录
def resolve_txt_record(domain):
    try:
        answers = dns.resolver.resolve(domain, 'TXT')
        for rdata in answers:
            for txt_record in rdata.strings:
                txt_content = txt_record.decode("utf-8")
                if ':' in txt_content:
                    ip, port = txt_content.split(':', 1)
                    if ip.count('.') == 3 and port.isdigit():
                        return ip, int(port)
                    else:
                        raise ValueError(f"TXT 记录格式不正确: {txt_content}")
        raise ValueError("没有找到符合格式的 TXT 记录")
    except Exception as e:
        raise ValueError(f"域名解析失败: {e}")

# TCP 转发逻辑
def tcp_relay(src, dst):
    try:
        while True:
            data = src.recv(4096)
            if not data:
                break
            dst.sendall(data)
    except Exception as e:
        print(f"TCP 转发时出错: {e}")
    finally:
        src.close()
        dst.close()

def handle_tcp_client(client_socket, target_ip, target_port):
    try:
        target = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        target.connect((target_ip, target_port))
        print(f"TCP 客户端 {client_socket.getpeername()} 已连接，转发到 {target_ip}:{target_port}")
        
        thread1 = threading.Thread(target=tcp_relay, args=(client_socket, target))
        thread2 = threading.Thread(target=tcp_relay, args=(target, client_socket))
        thread1.start()
        thread2.start()
        thread1.join()
        thread2.join()
    except Exception as e:
        print(f"处理 TCP 客户端时出错: {e}")
    finally:
        client_socket.close()

def start_tcp_forward(local_port, target_ip, target_port):
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.bind(('0.0.0.0', local_port))
    server.listen(5)
    print(f"TCP 转发服务已启动，监听 {local_port}，目标 {target_ip}:{target_port}")
    try:
        while True:
            client_socket, addr = server.accept()
            threading.Thread(target=handle_tcp_client, args=(client_socket, target_ip, target_port)).start()
    except Exception as e:
        print(f"TCP 服务启动失败: {e}")
    finally:
        server.close()

# UDP 转发逻辑
def start_udp_forward(local_port, target_ip, target_port):
    server = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    server.bind(('0.0.0.0', local_port))
    print(f"UDP 转发服务已启动，监听 {local_port}，目标 {target_ip}:{target_port}")
    try:
        while True:
            data, addr = server.recvfrom(4096)
            print(f"收到来自 {addr} 的数据")
            server.sendto(data, (target_ip, target_port))
    except Exception as e:
        print(f"UDP 服务启动失败: {e}")
    finally:
        server.close()

# 主函数
def main():
    import sys
    if len(sys.argv) != 4:
        print(f"用法: {sys.argv[0]} <本地端口> <域名> <协议(tcp/udp/both)>")
        return

    local_port = int(sys.argv[1])
    domain = sys.argv[2]
    protocol = sys.argv[3].lower()

    try:
        target_ip, target_port = resolve_txt_record(domain)
        print(f"解析成功: {target_ip}:{target_port}")

        if protocol in ['tcp', 'both']:
            threading.Thread(target=start_tcp_forward, args=(local_port, target_ip, target_port)).start()
        if protocol in ['udp', 'both']:
            threading.Thread(target=start_udp_forward, args=(local_port, target_ip, target_port)).start()
    except KeyboardInterrupt:
        print("\n程序已终止")   
    except Exception as e:
        print(f"程序出错: {e}")

if __name__ == "__main__":
    main()
