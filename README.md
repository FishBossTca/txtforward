# txtforward
## 介绍
🚀TXT解析转发数据的工具  
🚀用来解决TXT动态ip和端口号数据转发的功能，可以固定通过stun穿透后的ip和端口号动态更新的问题，解决家庭局域网通过stun穿透获取的公网ip和都会不固定的问题

程序在启动的时候会开放本地的一个端口，将该端口的数据转发到dns的TXT记录解析的ip:port
提供解析txt的域名内容格式必须为ip:port,否则将无法正常启动

## 快速开始
[下载相应操作系统的release文件](https://github.com/FishBossTca/txtforward/releases)

### 直接启动
首次启动会创建一个默认的配置文件txtforward.conf,包含启动的必要参数，以便下次直接启动而不手动添加参数信息
- Windows   
```txtfoward-windows-amd64.exe -d 域名```
- Linux  
```txtfoward-linux-amd64 -d 域名```

### 更多参数
使用方法可以输入```./txtfoward -h```查看 
``` 
options:
  -h, --help            show this help message and exit  
  -p PORT, --port PORT  本地监听端口  
  -d DOMAIN, --domain DOMAIN  目标域名  
  --protocol {tcp,udp}  协议类型 (tcp/udp)  
  -t, --tcp             使用TCP协议 (默认)  
  -u, --udp             使用UDP协议#(暂未开发)  
  -f FILE, --file FILE  指定配置文件  
  -c CONFIG, --config CONFIG  指定配置段名称 (默认是 'DEFAULT')  
```

## 配置
程序在第一次启动的时候默认创建一个txtforward.conf的文件，默认直接启动的话会先读取里面的配置进行转发，如果传入命令行参数则会复写默认配置
``` 
[DEFAULT]
port = 6666
domain = www.example.com
protocol = tcp
```
配置文件支持使用指定配置段，默认是使用DEFAULT段，如果你有多个TXT解析记录，则使用```-c 配置段```来选取指定配置段
``` 
#这个是默认配置段，可以修改
[DEFAULT]
port = 6666
domain = www.example.com
protocol = tcp

#用户创建配置段，需要手动指定
[user]
port = 7777
domain = www.a.com
protocol = tcp
```


##  Linux-ShellSript
Linux有shellscript版本，是借助socat和dig来实现
#### 依赖项
需要安装在使用脚本之前请先确认是否可以使用socat和dig命令
- debian/ubuntu  
```sudo apt install socat dnsutils```
- openwrt  
```opkg install socat bind-dig```

在txtfoward.sh的头部头定义默认直接启动的参数
```
DEFAULT_DOMAIN="请填入你的txt域名"
DEFAULT_LOCAL_PORT=6666
```
如果设置好了可以直接使用```./txtfoward```启动
否则需要在启动的时候传入参数
```
./txtfoward.sh port doamin

./txtfoward.sh -p 6666 -d txt.example.com
```

## 编译
本程序是用python编写的，可以直接下载源码运行
```
python ./start.py -d domain
```
如果要编译二进制文件，可以使用pyinstaller来编译python源码
#### 依赖项
请确保安装了dnspython和pyinstaller的pip包
```pip install dnspython pyinstaller```
如果没有虚拟环境请先创建虚拟环境再安装pyinstaller
- Linux
```
python -m venv python-venv
source ./python-venv/bin/active
```
#### 编译命令
```
git clone https://github.com/FishBossTca/txtforward.git
cd txtforward/src
pyinstaller --onefile start.py
```
编译完成后会生成dist文件夹，里面的txtfoward就是二进制的可执行文件了
如果编译文件较大的话请单独创建一个新的虚拟环境，只安装程序启动必要的包

## 可用的玩法
这个小工具一开始的目的是为了解决lucky软件创建的stun端口号动态更新的问题，通过开放本地的一个固定端口，转发到动态更新的端口，从而固定远程的动态端口
有兴趣的话可以去我的博客发出的文章学习一下[点我打开](https://www.ytca.top/guidance/openwrt/1258/)

# 注意
当前只支持TCP连接，如果想使用UDP或者TCP/UDP双连接的话还要等后续开

# 待定
UDP的转发模式  
创建多个转发类型  
图形化  
