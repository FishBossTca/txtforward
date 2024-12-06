from Forwarder import TcpForwarder
from TXTResolve import TXTResolve
from readConfig import Cli_ConfigLoader

def main():
    #命令行解析参数
    cli_config_loader = Cli_ConfigLoader().load_parameters()
    local_port, domain, protocol = cli_config_loader
    print(f"当前配置:本地端口号:{local_port},域名:{domain},协议:{protocol}")

    #txt解析
    txtForward=TXTResolve(local_port,domain,protocol)
    remote_ip,remote_port=txtForward.resolve_txt_record()

    #tcp转发
    tcpForwarder=TcpForwarder(local_port, remote_ip, remote_port)
    tcpForwarder.start()
    

if __name__ == "__main__":
    main()