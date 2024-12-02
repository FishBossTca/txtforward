#!/bin/bash

# 严格模式：任何错误都会导致脚本退出
set -euo pipefail

# 默认配置
DEFAULT_DOMAIN="www.example.com"
DEFAULT_LOCAL_PORT=6666

# 捕获 SIGINT 信号 (Ctrl+C)
cleanup() {
    echo "脚本已退出" >&2
    exit 0
}
trap cleanup SIGINT

# 校验 IP 地址格式
is_valid_ip() {
    local ip=$1
    if [[ $ip =~ ^([0-9]{1,3}\.){3}[0-9]{1,3}$ ]]; then
        for octet in $(echo "$ip" | tr '.' ' '); do
            if ((octet < 0 || octet > 255)); then
                return 1
            fi
        done
        return 0
    fi
    return 1
}

# 校验端口号格式
is_valid_port() {
    local port=$1
    if [[ $port =~ ^[0-9]+$ ]] && ((port >= 1 && port <= 65535)); then
        return 0
    fi
    return 1
}

# 检查依赖项
check_dependencies() {
    local dependencies=("dig" "socat")
    for cmd in "${dependencies[@]}"; do
        if ! command -v "$cmd" &> /dev/null; then
            echo "错误: 未找到依赖项 '$cmd'，请安装后重试。" >&2
            exit 1
        fi
    done
}

# 获取目标 IP 和端口
get_target_from_txt() {
    local domain=$1
    local txt_record
    local target_ip
    local target_port

    txt_record=$(dig +short TXT "$domain" | tr -d '"')

    if [[ -z "$txt_record" ]]; then
        echo "错误!无法找到 $domain 的 TXT 解析记录，请检查 TXT 域名是否正确" >&2
        exit 1
    fi

    target_ip=$(echo "$txt_record" | cut -d ':' -f 1)
    target_port=$(echo "$txt_record" | cut -d ':' -f 2)

    if ! is_valid_ip "$target_ip"; then
        echo "错误!无效的 TXT IP 格式: $target_ip" >&2
        exit 1
    fi

    if ! is_valid_port "$target_port"; then
        echo "错误!无效的 TXT 端口格式: $target_port" >&2
        exit 1
    fi

    echo "$target_ip" "$target_port"
}

# 显示帮助信息
show_help() {
    cat <<EOF
使用方法: $(basename "$0") [选项] [<端口号> <域名>]

选项说明：
  -p, --port <端口号>     指定本地监听端口，默认为 $DEFAULT_LOCAL_PORT
  -d, --domain <域名>     指定要解析的域名，默认为 $DEFAULT_DOMAIN
  -h, --help              显示此帮助信息

位置参数：
  <端口号> <域名>         直接指定端口和域名，将覆盖默认值或选项参数

示例：
  $(basename "$0")                      使用默认配置启动
  $(basename "$0") -p 8080              指定本地端口为 8080
  $(basename "$0") -d example.com       指定域名为 example.com
  $(basename "$0") 8080 example.com     通过位置参数指定本地端口和域名
EOF
}

# 主逻辑
main() {
    # 初始化参数
    LOCAL_PORT="$DEFAULT_LOCAL_PORT"
    DOMAIN="$DEFAULT_DOMAIN"

    # 如果默认域名未修改，提示用户修改配置文件并退出
    if [[ "$DEFAULT_DOMAIN" == "www.example.com" ]]; then
        show_help
        echo ""
        echo "错误: 您需要配置默认域名 (DEFAULT_DOMAIN)。请修改脚本中的默认值或通过参数指定域名。" >&2

        exit 1
    fi

    # 解析选项参数
    while [[ $# -gt 0 ]]; do
        case "$1" in
            -p|--port)
                LOCAL_PORT="$2"
                shift 2
                ;;
            -d|--domain)
                DOMAIN="$2"
                shift 2
                ;;
            -h|--help)
                show_help
                exit 0
                ;;
            -*)
                echo "未知参数: $1" >&2
                show_help
                exit 1
                ;;
            *)
                # 处理位置参数
                if [[ $# -ge 2 ]]; then
                    LOCAL_PORT="$1"
                    DOMAIN="$2"
                    shift 2
                else
                    echo "错误: 未知参数或缺少参数" >&2
                    show_help
                    exit 1
                fi
                ;;
        esac
    done

    # 校验参数
    if ! is_valid_port "$LOCAL_PORT"; then
        echo "错误!无效的本地端口格式: $LOCAL_PORT" >&2
        exit 1
    fi

    echo "正在解析 $DOMAIN 的 TXT 记录..."
    if ! read -r TARGET_IP TARGET_PORT < <(get_target_from_txt "$DOMAIN"); then
        echo "解析失败，脚本退出" >&2
        exit 1
    fi

    echo "目标地址: $TARGET_IP:$TARGET_PORT"
    echo "正在启动 socat 转发 (0.0.0.0:$LOCAL_PORT -> $TARGET_IP:$TARGET_PORT)..."

    # 使用 socat 转发数据
    if ! socat TCP-LISTEN:"$LOCAL_PORT",reuseaddr,fork TCP:"$TARGET_IP":"$TARGET_PORT"; then
        echo "错误! socat 启动失败" >&2
        exit 1
    fi
}

main "$@"
