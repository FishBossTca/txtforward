import configparser
import threading
import resolver#来自dnspython的库提取import dns.resolve
import argparse
import socket
import sys
import re
import os

DEFAULT_CONFIG_FILE = "txtforward.conf"  # 配置文件位置

# 命令行配置加载
class Cli_ConfigLoader:
    required_fields = ['port', 'domain', 'protocol']  # 配置文本字段检查

    # 读取配置文件并返回字典形式的参数
    def read_or_create_config(self, config_file=None, config_section='DEFAULT'):
        config = configparser.ConfigParser()
        
        # 如果传入了 config_file 参数，则使用它，否则使用默认配置文件
        if config_file is None:
            config_file = DEFAULT_CONFIG_FILE  # 使用默认配置文件路径

        # 写入配置文件
        try:
            if not os.path.exists(config_file):
                print(f"配置文件 {config_file} 不存在，正在创建默认配置...")
                config['DEFAULT'] = {
                    'port': '6666',
                    'domain': 'www.example.com',
                    'protocol': 'tcp'
                }
                try:
                    with open(config_file, 'w') as configfile:
                        config.write(configfile)
                    print(f"默认配置已写入 {config_file}，请编辑 {config_file} 或使用命令行选项覆盖参数")
                    sys.exit(1)  # 创建配置文件后退出
                except IOError as e:
                    print(f"写入配置文件 {config_file} 时发生错误: {e}")
                    sys.exit(1)  # 写入失败退出
        except Exception as e:
            print(f"检查配置文件时发生未预期的错误: {e}")
            sys.exit(1)  # 其他错误退出

        # 读取配置文件
        try:
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

    # 检查是否缺少字段
    def check_missing_fields(self, config, config_section):
        missing_fields = [key for key in self.required_fields if key not in config[config_section]]
        if missing_fields:
            print(f"配置文件 [{config_section}] 缺少以下字段: {', '.join(missing_fields)}")

    # 解析命令行参数
    def parse_arguments(self):
        parser = argparse.ArgumentParser(description="TXT解析转发")

        # TCP/UDP互斥参数组
        protocol_group = parser.add_mutually_exclusive_group()

        # 可选参数
        parser.add_argument('-p', '--port', type=int, help="本地监听端口")
        parser.add_argument('-d', '--domain', type=str, help="目标域名")
        parser.add_argument('--protocol', type=str, choices=['tcp', 'udp'], help="协议类型 (tcp/udp)")

        protocol_group.add_argument('-t', '--tcp', action='store_true', help="使用TCP协议 (默认)")
        protocol_group.add_argument('-u', '--udp', action='store_true', help=f"使用UDP协议#(暂未开发)")
        
        parser.add_argument('-f', '--file', type=str, help="指定配置文件")
        parser.add_argument('-c', '--config', type=str, default='DEFAULT', help="指定配置段名称 (默认是 'DEFAULT')")
        # 解析参数
        self.args = parser.parse_args()

    # 从命令行和配置文件加载参数，并优先使用命令行参数覆盖配置文件
    def load_parameters(self):
        self.parse_arguments()  # 获取原始 argparse.Namespace 对象

        try:
            # 如果传入了 --file 参数，优先使用该文件，否则使用默认配置文件
            config_file = self.args.file if self.args.file else None
            # 使用传入的配置段名称
            config_section = self.args.config
            self.read_or_create_config(config_file, config_section)  # 如果指定了配置文件，优先读取它
        except Exception as e:
            print(f"读取配置文件出错: {e}")
            self.config_params = {}

        # 优先级：命令行选项参数 > 配置文件参数
        port = self.args.port if self.args.port is not None else self.config_params.get('port')
        domain = self.args.domain if self.args.domain else self.config_params.get('domain')

        # 协议参数的解析逻辑
        if self.args.tcp:
            protocol = "tcp"
        elif self.args.udp:
            protocol = "udp"
        else:
            protocol = self.args.protocol or self.config_params.get('protocol')

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
        
        port = int(port)
        return port, domain, protocol


#TXT记录解析
class TXTResolve:
    def __init__(self,localport: int = 6666,domain: str = "www.example.com",protocol: str = "tcp",) -> None:
        self.localport = localport
        self.domain = domain
        self.protocol = protocol

    #解析域名的 TXT 记录，并提取其中的 IP 和端口号。返回 (ip, port)，如果解析失败，抛出异常。
    def resolve_txt_record(self):
        if self.domain=="www.example.com":
            print("请使用 -d 参数指定域名，或者修改配置文件默认域名", file=sys.stderr)
            sys.exit(1)
        IP_PORT_REGEX = re.compile(r"^(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}):(\d{1,5})$")  # ip:port的正则表达式
        try:
            answers = resolver.resolve(self.domain, 'TXT', lifetime=5)  # 设置超时时间为 5 秒
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
        except resolver.Timeout:
            print(f"域名解析失败: 查询超时，请检查网络正常", file=sys.stderr)
            sys.exit(1)
        except resolver.NXDOMAIN:
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



#TCP转发
class TCPForwarder:
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



def main():
    #命令行解析参数
    local_port, domain, protocol = Cli_ConfigLoader().load_parameters()
    print(f"当前配置:本地端口号:{local_port},域名:{domain},协议:{protocol}")

    #txt解析
    txtForward=TXTResolve(local_port,domain,protocol)
    remote_ip,remote_port=txtForward.resolve_txt_record()

    if(protocol=='tcp'):
        #tcp转发
        tcpForwarder=TCPForwarder(local_port, remote_ip, remote_port)
        tcpForwarder.start()
    else:
        print("暂不支持udp转发")

if __name__ == "__main__":
    main()