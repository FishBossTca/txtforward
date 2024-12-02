# txtforward
## 介绍
🚀TXT解析转发数据的工具  
🚀用来解决TXT动态ip和端口号数据转发的功能，可以固定通过stun穿透后的ip和端口号动态更新的问题，解决家庭局域网通过stun穿透获取的公网ip和都会不固定的问题

程序在启动的时候会开放本地的一个端口，将该端口的数据转发到dns的TXT记录解析的ip:port
提供解析txt的域名内容格式必须为ip:port,否则将无法正常启动

## 快速开始
[下载相应操作系统的release文件](https://alist.ytca.top)

###   直接启动
```./txtforward 本地端口 txt域名```

###  Linux
Linux有shellscript版本，是借助socat和dig来实现
#### 依赖项
需要安装在使用脚本之前请先确认是否可以使用socat和dig命令
- debian/ubuntu
```sudo apt install socat dnsutils```
- openwrt
```opkg install socat bind-dig```

使用方法可以输入./txtfoward -h 查看
  -p, --port <端口号>     指定本地监听端口，默认为文件头部定义的
  -d, --domain <域名>     指定要解析的域名，默认为 $DEFAULT_DOMAIN
  -h, --help              显示此帮助信息

在txtfoward.sh的头部头定义默认直接启动的参数
```
DEFAULT_DOMAIN="请填入你的txt域名"
DEFAULT_LOCAL_PORT=6666
```
如果设置好了可以直接使用./txtfoward启动
否则需要在启动的时候传入参数
```
./txtfoward.sh port doamin

./txtfoward.sh -p 6666 -d txt.example.com
```

## 编译
本程序是用python编写的，可以直接下载源码运行
```
python ./txtfoward.py port donmain
```
如果要编译二进制文件，可以使用pyinstaller来编译python源码
#### 依赖项

请确保安装了dnspython和pyinstaller的pip包
```

pip install dnspython pyinstaller
```
如果没有虚拟环境请先创建虚拟环境再安装pyinstaller
- Linux
```
python -m venv python-venv
source ./python-venv/bin/active
```
#### 编译命令
```
git clone https://
cd txtforward
pyinstaller --onefile txtfoward.py
```
编译完成后会生成dist文件夹，里面的txtfoward就是二进制的可执行文件了

