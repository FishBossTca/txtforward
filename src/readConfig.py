import configparser
import os
import argparse
import sys

DEFAULT_CONFIG_FILE = "src/txtforward.conf"  # 配置文件位置
required_fields = ['port', 'domain', 'protocol']  # 配置文本字段检查

#命令行配置加载
class Cli_ConfigLoader:
    def __init__(self, config_file=None):
        self.config_file = config_file or DEFAULT_CONFIG_FILE
        self.config_params = {}
        self.args = None

    #读取配置文件并返回字典形式的参数
    def read_or_create_config(self):
        config = configparser.ConfigParser()

        # 如果文件不存在，创建并写入默认值
        if not os.path.exists(self.config_file):
            print(f"配置文件 {self.config_file} 不存在，正在创建默认配置...")
            config['DEFAULT'] = {
                'port': '6666',
                'domain': 'www.example.com',
                'protocol': 'tcp'
            }
            with open(self.config_file, 'w') as configfile:
                config.write(configfile)
            print(f"默认配置已写入 {self.config_file}，请编辑{self.config_file}或者使用命令行选项覆写参数")
            sys.exit(1)

        config.read(self.config_file)
        self.check_missing_fields(config)
        self.config_params = {
            'port': config['DEFAULT'].get('port'),
            'domain': config['DEFAULT'].get('domain'),
            'protocol': config['DEFAULT'].get('protocol'),
        }

    #检查是否缺少字段
    def check_missing_fields(self, config):
        missing_fields = [key for key in required_fields if key not in config['DEFAULT']]
        if missing_fields:
            print(f"配置文件缺少以下字段: {', '.join(missing_fields)}")

    #解析命令行参数
    def parse_arguments(self):
        parser = argparse.ArgumentParser(description="TCP/UDP 转发程序")

        # TCP/UDP互斥参数组
        protocol_group = parser.add_mutually_exclusive_group()

        # 可选参数
        parser.add_argument('-p', '--port', type=int, help="本地监听端口")
        parser.add_argument('-d', '--domain', type=str, help="目标域名")
        parser.add_argument('--protocol', type=str, choices=['tcp', 'udp'], help="协议类型 (tcp/udp)")

        protocol_group.add_argument('-t', '--tcp', action='store_true', help="使用TCP协议 (默认)")
        protocol_group.add_argument('-u', '--udp', action='store_true', help="使用UDP协议")

        parser.add_argument('-f', '--file', type=str, help="指定配置文件")

        # 解析参数
        self.args = parser.parse_args()

    #从命令行和配置文件加载参数，并优先使用命令行参数覆盖配置文件
    def load_parameters(self):
        self.parse_arguments()  # 获取原始 argparse.Namespace 对象

        # 如果指定了配置文件，优先读取它
        try:
            self.read_or_create_config()
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



