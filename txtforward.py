import configparser
import dns.resolver
import threading
import argparse
import socket
import sys
import re
import os

DEFAULT_CONFIG_FILE = "txtforward.conf"  # 配置文件位置

# 命令行配置加载
class Cli_ConfigLoader:
    required_fields = ['port', 'domain', 'protocol']  # 配置文本字段检查

    def read_or_create_config(self, config_file=None, config_section='DEFAULT'):
        config = configparser.ConfigParser()

        # 如果传入了 config_file 参数，则使用它，否则使用默认配置文件
        if config_file is None:
            config_file = DEFAULT_CONFIG_FILE  # 使用默认配置文件路径

        try:
            if not os.path.exists(config_file):
                print(f"配置文件 {config_file} 不存在，正在创建默认配置...")
                config['DEFAULT'] = {
                    'port': '6666',
                    'domain': 'www.example.com',
                    'protocol': 'tcp'
                }
                with open(config_file, 'w') as configfile:
                    config.write(configfile)
                print(f"默认配置已写入 {config_file}，请编辑该文件或使用命令行选项覆盖参数")
                sys.exit(1)  # 创建配置文件后退出

            config.read(config_file)
            self.check_missing_fields(config, config_section)
            self.config_params = {
                'port': config[config_section].get('port'),
                'domain': config[config_section].get('domain'),
                'protocol': config[config_section].get('protocol'),
            }
        except configparser.Error as e:
            print(f"解析配置文件 {config_file} 时发生错误: {e}")
            sys.exit(1)  # 配置解析失败退出
        except IOError as e:
            print(f"读取配置文件 {config_file} 时发生错误: {e}")
            sys.exit(1)  # 文件读取失败退出

    def check_missing_fields(self, config, config_section):
        missing_fields = [key for key in self.required_fields if key not in config[config_section]]
        if missing_fields:
            print(f"配置文件 [{config_section}] 缺少以下字段: {', '.join(missing_fields)}")

    def parse_arguments(self):
        parser = argparse.ArgumentParser(description="TXT解析转发")

        # TCP/UDP互斥参数组
        protocol_group = parser.add_mutually_exclusive_group()

        parser.add_argument('-p', '--port', type=int, help="本地监听端口")
        parser.add_argument('-d', '--domain', type=str, help="目标域名")
        parser.add_argument('--protocol', type=str, choices=['tcp', 'udp'], help="协议类型 (tcp/udp)")
        protocol_group.add_argument('-t', '--tcp', action='store_true', help="使用TCP协议 (默认)")
        protocol_group.add_argument('-u', '--udp', action='store_true', help="使用UDP协议 (暂未开发)")
        parser.add_argument('-f', '--file', type=str, help="指定配置文件")
        parser.add_argument('-c', '--config', type=str, default='DEFAULT', help="指定配置段名称 (默认是 'DEFAULT')")

        self.args = parser.parse_args()

    def load_parameters(self):
        self.parse_arguments()  # 获取命令行参数

        try:
            config_file = self.args.file if self.args.file else None
            config_section = self.args.config
            self.read_or_create_config(config_file, config_section)  # 如果指定了配置文件，优先读取它
        except Exception as e:
            print(f"读取配置文件出错: {e}")
            self.config_params = {}

        # 优先级：命令行选项参数 > 配置文件参数
        port = self.args.port or self.config_params.get('port')
        domain = self.args.domain or self.config_params.get('domain')

        protocol = self.args.protocol or ("tcp" if self.args.tcp else "udp" if self.args.udp else self.config_params.get('protocol'))

        # 检查缺少必要参数，并输出缺少的参数
        missing_params = []
        if not port:
            missing_params.append("port")
        if not domain:
            missing_params.append("domain")
        if not protocol:
            missing_params.append("protocol")

        if missing_params:
            print(f"缺少必要参数: {', '.join(missing_params)}，请使用 --help 查看用法")
            exit(1)

        return int(port), domain, protocol


# TXT记录解析
class TXTResolve:
    def __init__(self, localport: int = 6666, domain: str = "www.example.com", protocol: str = "tcp"):
        self.localport = localport
        self.domain = domain
        self.protocol = protocol

    def resolve_txt_record(self):
        if self.domain == "www.example.com":
            print("请使用 -d 参数指定域名，或者修改配置文件默认域名", file=sys.stderr)
            sys.exit(1)

        IP_PORT_REGEX = re.compile(r"^(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}):(\d{1,5})$")
        try:
            answers = dns.resolver.resolve(self.domain, 'TXT', lifetime=5)
            for rdata in answers:
                for txt_record in rdata.strings:
                    txt_content = txt_record.decode("utf-8")
                    match = IP_PORT_REGEX.match(txt_content)
                    if match:
                        ip, port = match.groups()
                        if all(0 <= int(octet) <= 255 for octet in ip.split('.')) and 0 <= int(port) <= 65535:
                            print(f"解析成功: {ip}:{port}")
                            return ip, int(port)
                        else:
                            raise ValueError(f"IP或端口号不合法: {txt_content}")
            raise ValueError("没有找到符合格式的TXT记录")
        except dns.resolver.Timeout:
            print(f"域名解析失败: 查询超时，请检查网络正常", file=sys.stderr)
            sys.exit(1)
        except dns.resolver.NXDOMAIN:
            print(f"域名解析失败: 域名 {self.domain} 不存在，请检查拼写。", file=sys.stderr)
            sys.exit(1)
        except Exception as e:
            print(f"域名解析失败: {e}", file=sys.stderr)
            sys.exit(1)

    def get_remote_ip_port(self):
        try:
            target_ip, target_port = self.resolve_txt_record()
            return target_ip, target_port
        except Exception as e:
            print(f"获取远程 IP 和端口号失败: {e}", file=sys.stderr)
            sys.exit(1)


# TCP转发
class TCPForwarder:
    def __init__(self, local_port: int, target_ip: str, target_port: int):
        self.local_port = local_port
        self.target_ip = target_ip
        self.target_port = target_port
        self.server = None

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

    def handle_client(self, client_socket):
        try:
            target = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            target.connect((self.target_ip, self.target_port))
            print(f"客户端 {client_socket.getpeername()} 已连接，正在转发到 {self.target_ip}:{self.target_port}")

            thread1 = threading.Thread(target=self.relay, args=(client_socket, target), daemon=True)
            thread2 = threading.Thread(target=self.relay, args=(target, client_socket), daemon=True)
            thread1.start()
            thread2.start()
        except Exception as e:
            print(f"连接处理时出错: {e}")
            client_socket.close()

    def start(self):
        self.server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server.bind(('0.0.0.0', self.local_port))
        self.server.listen(5)
        print(f"监听端口 {self.local_port}...")

        try:
            while True:
                client_socket, addr = self.server.accept()
                print(f"新连接来自 {addr}")
                threading.Thread(target=self.handle_client, args=(client_socket,), daemon=True).start()
        except KeyboardInterrupt:
            print("服务器已停止")
        finally:
            self.server.close()


# 主程序入口
def main():
    loader = Cli_ConfigLoader()
    port, domain, protocol = loader.load_parameters()

    resolver = TXTResolve(localport=port, domain=domain, protocol=protocol)
    target_ip, target_port = resolver.get_remote_ip_port()

    if protocol == "tcp":
        forwarder = TCPForwarder(local_port=port, target_ip=target_ip, target_port=target_port)
        forwarder.start()

if __name__ == "__main__":
    main()
