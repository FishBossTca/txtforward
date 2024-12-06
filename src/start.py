from TxtForward import TxtForward
from readConfig import Cli_ConfigLoader

def main():
    #命令行解析参数
    cli_config_loader = Cli_ConfigLoader().load_parameters()
    port, domain, protocol = cli_config_loader
    print(f"当前配置:本地端口号:{port},域名:{domain},协议:{protocol}")

    #txt直接转发
    txtForward=TxtForward(port,domain,protocol)
    txtForward.start()

if __name__ == "__main__":
    main()