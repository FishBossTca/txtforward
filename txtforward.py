import configparser
import dns.resolver
import threading
import argparse
import socket
import logging
import sys
import re
import os

# 配置日志记录格式和级别
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

DEFAULT_CONFIG_FILE = "txtforward.conf"
BUFFER_SIZE = 8192  # 设置缓冲区大小以提高数据传输性能

class ConfigError(Exception):
    """配置相关错误的自定义异常"""
    pass

class CliConfigLoader:
    def __init__(self):
        self.required_fields = ['port', 'domain', 'protocol']  # 必须在配置文件中定义的字段
        self.config_params = {}

    def load_config(self, config_file=None, config_section='DEFAULT'):
        """读取或创建配置文件"""
        config = configparser.ConfigParser()
        config_file = config_file or DEFAULT_CONFIG_FILE

        if not os.path.exists(config_file):
            self._create_default_config(config_file)
            return

        try:
            config.read(config_file)
            self._check_missing_fields(config, config_section)
            self.config_params = {field: config[config_section].get(field) for field in self.required_fields}
        except (configparser.Error, IOError) as e:
            raise ConfigError(f"配置文件错误: {e}")

    def _create_default_config(self, config_file):
        """创建默认配置文件"""
        config = configparser.ConfigParser()
        config['DEFAULT'] = {
            'port': '6666',
            'domain': 'www.example.com',
            'protocol': 'tcp'
        }
        with open(config_file, 'w') as configfile:
            config.write(configfile)
        logger.info(f"已创建默认配置文件: {config_file}")
        sys.exit(1)

    def _check_missing_fields(self, config, config_section):
        """检查配置文件中是否缺少必要字段"""
        missing_fields = [key for key in self.required_fields if key not in config[config_section]]
        if missing_fields:
            raise ConfigError(f"配置文件 [{config_section}] 缺少以下字段: {', '.join(missing_fields)}")

    def parse_arguments(self):
        """解析命令行参数"""
        parser = argparse.ArgumentParser(description="TXT解析转发")
        protocol_group = parser.add_mutually_exclusive_group()

        # 添加命令行参数
        parser.add_argument('-p', '--port', type=int, help="本地监听端口")
        parser.add_argument('-d', '--domain', type=str, help="目标域名")
        parser.add_argument('--protocol', type=str, choices=['tcp', 'udp'], help="协议类型 (tcp/udp)")
        protocol_group.add_argument('-t', '--tcp', action='store_true', help="使用TCP协议 (默认)")
        protocol_group.add_argument('-u', '--udp', action='store_true', help="使用UDP协议")
        parser.add_argument('-f', '--file', type=str, help="指定配置文件")
        parser.add_argument('-c', '--config', type=str, default='DEFAULT', help="指定配置段名称 (默认是 'DEFAULT')")

        self.args = parser.parse_args()

    def load_parameters(self):
        """加载参数，优先使用命令行参数，其次是配置文件"""
        self.parse_arguments()

        config_file = self.args.file if self.args.file else None
        config_section = self.args.config
        self.load_config(config_file, config_section)

        # 获取参数，命令行参数优先
        port = self.args.port or self.config_params.get('port')
        domain = self.args.domain or self.config_params.get('domain')
        protocol = self.args.protocol or ("tcp" if self.args.tcp else "udp" if self.args.udp else self.config_params.get('protocol'))

        # 检查是否缺少必要参数
        missing_params = []
        if not port:
            missing_params.append("port")
        if not domain:
            missing_params.append("domain")
        if not protocol:
            missing_params.append("protocol")

        if missing_params:
            logger.error(f"缺少必要参数: {', '.join(missing_params)}，请使用 --help 查看用法")
            sys.exit(1)

        return int(port), domain, protocol

class TXTResolver:
    def __init__(self, domain: str):
        self.domain = domain
        self._ip_port_pattern = re.compile(r"^(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}):(\d{1,5})$")

    def resolve(self):
        """解析域名的TXT记录以获取IP和端口"""
        if self.domain == "www.example.com":
            logger.error("请使用 -d 参数指定域名，或者修改配置文件默认域名")
            sys.exit(1)

        try:
            answers = dns.resolver.resolve(self.domain, 'TXT', lifetime=5)
            for rdata in answers:
                for txt_record in rdata.strings:
                    txt_content = txt_record.decode("utf-8")
                    match = self._ip_port_pattern.match(txt_content)
                    if match:
                        ip, port = match.groups()
                        if self._validate_ip_port(ip, port):
                            logger.info(f"解析成功: {ip}:{port}")
                            return ip, int(port)
            raise ValueError("没有找到符合格式的TXT记录")
        except (dns.resolver.Timeout, dns.resolver.NXDOMAIN, Exception) as e:
            logger.error(f"域名解析失败: {e}")
            sys.exit(1)

    def _validate_ip_port(self, ip: str, port: str) -> bool:
        """验证IP和端口的合法性"""
        try:
            if not all(0 <= int(octet) <= 255 for octet in ip.split('.')):
                return False
            port_num = int(port)
            return 0 <= port_num <= 65535
        except ValueError:
            return False

class Forwarder:
    def __init__(self, local_port: int, target_ip: str, target_port: int, protocol: str):
        self.local_port = local_port
        self.target_ip = target_ip
        self.target_port = target_port
        self.protocol = protocol
        self.server = None

    def start(self):
        """启动转发服务器"""
        if self.protocol == 'tcp':
            self._start_tcp()
        elif self.protocol == 'udp':
            self._start_udp()

    def _start_tcp(self):
        """启动TCP转发服务器"""
        self.server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server.bind(('0.0.0.0', self.local_port))
        self.server.listen(5)
        logger.info(f"TCP: 监听端口 {self.local_port}...")

        try:
            while True:
                client_socket, addr = self.server.accept()
                logger.info(f"新连接来自 {addr}")
                threading.Thread(target=self._handle_tcp_client, args=(client_socket,), daemon=True).start()
        except KeyboardInterrupt:
            logger.info("TCP服务器已停止")
        finally:
            self.server.close()

    def _handle_tcp_client(self, client_socket):
        """处理TCP客户端连接"""
        try:
            target = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            target.connect((self.target_ip, self.target_port))
            logger.info(f"客户端 {client_socket.getpeername()} 已连接，正在转发到 {self.target_ip}:{self.target_port}")

            threading.Thread(target=self._relay, args=(client_socket, target), daemon=True).start()
            threading.Thread(target=self._relay, args=(target, client_socket), daemon=True).start()
        except Exception as e:
            logger.error(f"TCP连接处理时出错: {e}")
            client_socket.close()

    def _relay(self, src, dst):
        """在两个socket之间转发数据"""
        try:
            while True:
                data = src.recv(BUFFER_SIZE)
                if not data:
                    logger.info("连接已关闭")
                    break
                dst.sendall(data)
        except Exception as e:
            logger.error(f"转发数据时出错: {e}")
        finally:
            src.close()
            dst.close()

    def _start_udp(self):
        """启动UDP转发服务器"""
        self.server = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.server.bind(('0.0.0.0', self.local_port))
        logger.info(f"UDP: 监听端口 {self.local_port}...")

        client_to_server = {}

        try:
            while True:
                data, client_addr = self.server.recvfrom(BUFFER_SIZE)
                if not data:
                    continue

                if client_addr not in client_to_server:
                    forward_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                    client_to_server[client_addr] = forward_socket
                    threading.Thread(
                        target=self._handle_udp_response,
                        args=(forward_socket, client_addr, client_to_server),
                        daemon=True
                    ).start()

                forward_socket = client_to_server[client_addr]
                try:
                    forward_socket.sendto(data, (self.target_ip, self.target_port))
                except Exception as e:
                    logger.error(f"UDP: 转发数据时出错: {e}")
                    del client_to_server[client_addr]
                    forward_socket.close()

        except KeyboardInterrupt:
            logger.info("UDP服务器已停止")
        finally:
            self._cleanup(client_to_server)

    def _handle_udp_response(self, forward_socket, client_addr, client_to_server):
        """处理从目标服务器返回的UDP响应"""
        try:
            while True:
                data, _ = forward_socket.recvfrom(BUFFER_SIZE)
                if not data:
                    break
                self.server.sendto(data, client_addr)
        except Exception as e:
            logger.error(f"UDP: 处理响应时出错: {e}")
        finally:
            if client_addr in client_to_server:
                del client_to_server[client_addr]
            forward_socket.close()

    def _cleanup(self, client_to_server):
        """清理所有打开的socket"""
        for socket in client_to_server.values():
            socket.close()
        if self.server:
            self.server.close()
        client_to_server.clear()

def main():
    loader = CliConfigLoader()
    port, domain, protocol = loader.load_parameters()

    resolver = TXTResolver(domain=domain)
    target_ip, target_port = resolver.resolve()

    forwarder = Forwarder(local_port=port, target_ip=target_ip, target_port=target_port, protocol=protocol)
    forwarder.start()

if __name__ == "__main__":
    main()
