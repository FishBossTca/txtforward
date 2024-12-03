import socket
import threading
import dns.resolver

#解析域名的 TXT 记录，并提取其中的 IP 和端口号。返回 (ip, port)，如果解析失败，抛出异常。
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

#转发数据流
def relay(src, dst):
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

#处理客户端连接并转发流量到目标地址。
def handle_client(client_socket, target_ip, target_port):
    try:
        target = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        target.connect((target_ip, target_port))
        print(f"客户端 {client_socket.getpeername()} 已连接，正在转发到 {target_ip}:{target_port}")
        
        # 创建线程转发数据
        thread1 = threading.Thread(target=relay, args=(client_socket, target))
        thread2 = threading.Thread(target=relay, args=(target, client_socket))
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

#启动端口转发服务。
def forward_traffic(local_port, target_ip, target_port):
    try:
        server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server.bind(('0.0.0.0', local_port))#如果要修改监听地址就改这里
        server.listen(5)
        print(f"转发服务已启动，监听本地端口 {local_port}，目标 {target_ip}:{target_port}")

        while True:
            client_sock, addr = server.accept()
            threading.Thread(target=handle_client, args=(client_sock, target_ip, target_port)).start()
    except Exception as e:
        print(f"启动转发服务时出错: {e}")

def main():
    import sys
    if len(sys.argv) != 3:
        print(f"用法: {sys.argv[0]} <本地端口> <域名>")
        return
    
    local_port = int(sys.argv[1])
    domain = sys.argv[2]
    
    try:
        target_ip, target_port = resolve_txt_record(domain)
        print(f"解析成功: {target_ip}:{target_port}")
        forward_traffic(local_port, target_ip, target_port)
    except KeyboardInterrupt:
        print("\n程序已终止")

if __name__ == "__main__":
    main()


