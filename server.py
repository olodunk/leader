from waitress import serve
from app import app
import socket

# 获取本机IP，方便局域网访问
def get_host_ip():
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(('8.8.8.8', 80))
        ip = s.getsockname()[0]
    except:
        ip = '127.0.0.1'
    finally:
        s.close()
    return ip

if __name__ == '__main__':
    host_ip = get_host_ip()
    port = 1111
    
    print(f"-------------------------------------------------------")
    print(f" 中层干部测评系统已启动 (Waitress Server)")
    print(f" 访问地址: http://{host_ip}:{port}")
    print(f" 本地地址: http://127.0.0.1:{port}")
    print(f"-------------------------------------------------------")
    
    # threads=4 表示并发线程数，根据实际情况调整
    serve(app, host='0.0.0.0', port=port, threads=30)