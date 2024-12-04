import re
import sys
import dns.resolver
from .Forwarder import TcpForwarder
class TxtForward:
    def __init__(self,localport: int = 6666,domain: str = "www.example.com",protocol: str = "tcp",) -> None:
        self.localport = localport
        self.domain = domain
        self.protocol = protocol

    #解析域名的 TXT 记录，并提取其中的 IP 和端口号。返回 (ip, port)，如果解析失败，抛出异常。
    def resolve_txt_record(self):
        IP_PORT_REGEX = re.compile(r"^(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}):(\d{1,5})$")  # ip:port的正则表达式
        try:
            answers = dns.resolver.resolve(self.domain, 'TXT', lifetime=5)  # 设置超时时间为 5 秒
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

    #直接转发
    def start(self):
        try:
            target_ip, target_port = self.resolve_txt_record()
            if self.protocol == "tcp":
                TcpForwarder(self.localport, target_ip, target_port).start()
            elif self.protocol == "udp":
                print("UDP暂不支持")
                sys.exit(1)
        except KeyboardInterrupt:
            print("\n程序已终止")