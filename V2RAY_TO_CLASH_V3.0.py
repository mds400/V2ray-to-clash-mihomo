import json
import base64
import urllib.parse
import sys
import subprocess
import os
import re

# ألوان واجهة الطرفية
RESET = "\033[0m"
BOLD = "\033[1m"
CYAN = "\033[96m"
BLUE = "\033[94m"
GREEN = "\033[92m"
YELLOW = "\033[93m"
RED = "\033[91m"
MAGENTA = "\033[95m"

def color(text, code):
    if os.environ.get("NO_COLOR"):
        return str(text)
    return f"{code}{text}{RESET}"

def show_banner():
    print()
    print(color("╔══════════════════════════════════════════════════════════════╗", CYAN))
    print(color("║              V2RAY  TO  CLASH   V3.0                        ║", BLUE + BOLD))
    print(color("║                 محوّل التكوينات                              ║", CYAN + BOLD))
    print(color("╠══════════════════════════════════════════════════════════════╣", CYAN))
    print(color("║ الحقوق: محمد 🇮🇶 سلوم  |  @SELOOM1                         ║", YELLOW + BOLD))
    print(color("║ انضم إلى قناة التلكرام:                                     ║", GREEN))
    print(color("║ https://t.me/freevpsiraq                                    ║", MAGENTA))
    print(color("╚══════════════════════════════════════════════════════════════╝", CYAN))
    print()

def info(message):
    print(color(f"  • {message}", CYAN))

def success(message):
    print(color(f"  ✓ {message}", GREEN + BOLD))

def error(message):
    print(color(f"  ✗ {message}", RED + BOLD))

# --- دالة ذكية تدعم العربي والانكليزي والسمايلات والأعلام بالكامل ---
def get_clean_proxy_name(link, server_address, default_type):
    decoded_link = urllib.parse.unquote(link)
    name_part = ""
    
    if "#" in decoded_link:
        name_part = decoded_link.split("#")[-1].strip()
            
    if not name_part and server_address:
        name_part = server_address
        
    if not name_part:
        name_part = f"{default_type}_Server"
        
    if "?" in name_part:
        name_part = name_part.split("?")[0].strip()
        
    name_part = re.sub(r'\s+', '_', name_part)
    cleaned = re.sub(r'[^a-zA-Z0-9._\-\u0600-\u06FF\U00010000-\U0010ffff]', '', name_part)
    cleaned = re.sub(r'_+', '_', cleaned)
    cleaned = cleaned.strip('_')
    
    return cleaned if cleaned else f"{default_type}_Server"

def parse_vmess(link):
    decoded_link = urllib.parse.unquote(link)
    body = decoded_link.split("vmess://")[1].split("#")[0].strip()
    missing_padding = len(body) % 4
    if missing_padding:
        body += '=' * (4 - missing_padding)
    
    data = json.loads(base64.b64decode(body).decode('utf-8'))
    
    server_host = data.get("add", "")
    proxy_name = get_clean_proxy_name(link, server_host, "VMess")
    
    if "ps" in data and "#" not in decoded_link:
        ps_name = urllib.parse.unquote(data.get("ps")).strip()
        if ps_name:
            proxy_name = get_clean_proxy_name(f"#{ps_name}", server_host, "VMess")
    
    proxy = {
        "name": proxy_name,
        "type": "vmess",
        "server": server_host,
        "port": int(data.get("port", 443)),
        "uuid": data.get("id"),
        "alterId": 0,
        "cipher": "auto",
        "network": data.get("net", "tcp"),
        "udp": True
    }
    
    if data.get("tls") == "tls":
        proxy["tls"] = True
        proxy["skip-cert-verify"] = True
        if data.get("sni"):
            proxy["servername"] = data.get("sni")
    else:
        proxy["tls"] = False
        
    if data.get("net") == "ws":
        ws_opts = {}
        if data.get("path"):
            ws_opts["path"] = data.get("path")
        if data.get("host"):
            ws_opts["headers"] = {"Host": data.get("host")}
        if ws_opts:
            proxy["ws-opts"] = ws_opts
            
    return proxy

def parse_vless(link):
    decoded_link = urllib.parse.unquote(link)
    main_part = decoded_link.split("#")[0]
    
    parsed = urllib.parse.urlparse(main_part)
    netloc_parts = parsed.netloc.split("@")
    
    uuid = netloc_parts[0]
    server_port = netloc_parts[1].split(":")
    server = server_port[0]
    port = int(server_port[1])
    
    proxy_name = get_clean_proxy_name(link, server, "VLESS")
    query = urllib.parse.parse_qs(parsed.query)
    
    network = query.get("type", ["tcp"])[0]
    security = query.get("security", ["none"])[0]
    sni = query.get("sni", [""])[0]
    path = query.get("path", [""])[0]
    host = query.get("host", [""])[0]
    
    proxy = {
        "name": proxy_name,
        "type": "vless",
        "server": server,
        "port": port,
        "uuid": uuid,
        "cipher": "auto",
        "network": network,
        "udp": True
    }
    
    if network == "tcp":
        proxy["xudp"] = True
        proxy["flow"] = query.get("flow", ["none"])[0]
        
    if security == "tls":
        proxy["tls"] = True
        proxy["skip-cert-verify"] = True
        if sni:
            proxy["servername"] = sni
    else:
        proxy["tls"] = False
        
    if network == "ws":
        proxy["xudp"] = True
        ws_opts = {}
        if path:
            ws_opts["path"] = path
        if host:
            ws_opts["headers"] = {"Host": host}
        if ws_opts:
            proxy["ws-opts"] = ws_opts
            
    return proxy

def parse_trojan(link):
    decoded_link = urllib.parse.unquote(link)
    main_part = decoded_link.split("#")[0]
    
    parsed = urllib.parse.urlparse(main_part)
    netloc_parts = parsed.netloc.split("@")
    
    password = netloc_parts[0]
    server_port = netloc_parts[1].split(":")
    server = server_port[0]
    port = int(server_port[1])
    
    proxy_name = get_clean_proxy_name(link, server, "Trojan")
    query = urllib.parse.parse_qs(parsed.query)
    
    network = query.get("type", ["tcp"])[0]
    sni = query.get("sni", [""])[0]
    path = query.get("path", [""])[0]
    host = query.get("host", [""])[0]
    
    proxy = {
        "name": proxy_name,
        "type": "trojan",
        "server": server,
        "port": port,
        "password": password,
        "skip-cert-verify": True,
        "network": network,
        "udp": True
    }
    
    if sni:
        proxy["sni"] = sni
    else:
        proxy["sni"] = ""
        
    if network == "ws":
        ws_opts = {}
        if path:
            ws_opts["path"] = path
        if host:
            ws_opts["headers"] = {"Host": host}
        if ws_opts:
            proxy["ws-opts"] = ws_opts
            
    return proxy

def parse_wireguard(link):
    """قراءة رابط WireGuard بصيغة wireguard:// وتحويله لبيانات Mihomo."""
    raw_link = link.strip()
    main_part = raw_link.split("#")[0]
    parsed = urllib.parse.urlparse(main_part)

    if not parsed.hostname or not parsed.port:
        raise ValueError("رابط WireGuard يجب أن يحتوي على server و port")

    query = urllib.parse.parse_qs(parsed.query)

    def get_required(name):
        value = query.get(name, [""])[0].strip()
        if not value:
            raise ValueError(f"رابط WireGuard لا يحتوي على {name}")
        return value

    private_key = urllib.parse.unquote(parsed.username or "").strip()
    if not private_key:
        private_key = get_required("privatekey")

    addresses = [x.strip() for x in get_required("address").split(",") if x.strip()]
    ipv4 = ""
    ipv6 = ""
    for address in addresses:
        clean_address = address.split("/")[0]
        if ":" in clean_address and not ipv6:
            ipv6 = clean_address
        elif ":" not in clean_address and not ipv4:
            ipv4 = clean_address

    if not ipv4:
        raise ValueError("يجب أن يحتوي address على عنوان IPv4 مثل 172.16.0.2/32")

    return {
        "name": get_clean_proxy_name(link, parsed.hostname, "WireGuard"),
        "type": "wireguard",
        "server": parsed.hostname,
        "port": parsed.port,
        "ip": ipv4,
        "ipv6": ipv6,
        "private-key": private_key,
        "public-key": get_required("publickey"),
    }

def generate_wireguard_config(proxy_data):
    """قالب WireGuard المطابق للتكوين العامل، بدون قسم DNS العام."""
    ipv6_line = f'    ipv6: "{proxy_data["ipv6"]}"\n' if proxy_data.get("ipv6") else ""
    return f'''redir-port: 9797
tproxy-port: 9898

mode: rule
allow-lan: true
bind-address: "*"
log-level: error

unified-delay: true
geodata-mode: true
geodata-loader: memconservative
ipv6: false

keep-alive-interval: 15
tcp-concurrent: false


proxies:
  - name: "{proxy_data["name"]}"
    type: wireguard
    server: {proxy_data["server"]}
    port: {proxy_data["port"]}

    ip: {proxy_data["ip"]}
{ipv6_line}
    private-key: "{proxy_data["private-key"]}"
    public-key: "{proxy_data["public-key"]}"

    udp: true
    mtu: 1280
    remote-dns-resolve: true
    dns:
      - 1.1.1.1
      - 1.0.0.1
proxy-groups:
  - name: box
    type: select
    proxies:
      - "{proxy_data["name"]}"

rules:
  - MATCH,box

external-controller: 0.0.0.0:9090
external-ui: ./dashboard
'''

def generate_full_config(proxy_data):
    if proxy_data.get("type") == "wireguard":
        return generate_wireguard_config(proxy_data)

    config_template = f"""redir-port: 9797
tproxy-port: 9898

mode: rule
allow-lan: true
bind-address: '*'
log-level: error

unified-delay: true
geodata-mode: true
geodata-loader: memconservative
ipv6: false

keep-alive-interval: 15
tcp-concurrent: false

dns:
  enable: true
  listen: 0.0.0.0:1053
  ipv6: false
  enhanced-mode: fake-ip
  fake-ip-range: 198.18.0.1/16

  default-nameserver:
    - 1.1.1.1
    - 8.8.8.8

  nameserver:
    - https://dns.google/dns-query#box

proxies:
"""
    proxy_yaml = f"  - name: \"{proxy_data['name']}\"\n"
    proxy_yaml += f"    type: {proxy_data['type']}\n"
    proxy_yaml += f"    server: {proxy_data['server']}\n"
    proxy_yaml += f"    port: {proxy_data['port']}\n"
    
    if proxy_data['type'] in ['vmess', 'vless']:
        proxy_yaml += f"    uuid: {proxy_data['uuid']}\n"
    elif proxy_data['type'] == 'trojan':
        proxy_yaml += f"    password: {proxy_data['password']}\n"
    
    if proxy_data['type'] == 'vmess':
        proxy_yaml += f"    alterId: {proxy_data['alterId']}\n"
        
    if proxy_data['type'] != 'trojan':
        proxy_yaml += f"    cipher: {proxy_data['cipher']}\n"
    
    if "flow" in proxy_data and proxy_data["flow"] != "none":
        proxy_yaml += f"    flow: {proxy_data['flow']}\n"
        
    proxy_yaml += f"    network: {proxy_data['network']}\n"
    proxy_yaml += f"    udp: {proxy_data['udp']}\n"
    
    if "xudp" in proxy_data:
        proxy_yaml += f"    xudp: {proxy_data['xudp']}\n"
        
    if "packet-encoding" in proxy_data:
        proxy_yaml += f"    packet-encoding: {proxy_data['packet-encoding']}\n"
        
    if proxy_data['type'] == 'trojan':
        proxy_yaml += f"    skip-cert-verify: {str(proxy_data['skip-cert-verify']).lower()}\n"
        proxy_yaml += f"    sni: '{proxy_data['sni']}'\n"
    else:
        proxy_yaml += f"    tls: {str(proxy_data['tls']).lower()}\n"
        if proxy_data.get("tls"):
            proxy_yaml += f"    skip-cert-verify: {str(proxy_data['skip-cert-verify']).lower()}\n"
            if "servername" in proxy_data:
                proxy_yaml += f"    servername: {proxy_data['servername']}\n"
            
    if "ws-opts" in proxy_data:
        proxy_yaml += "    ws-opts:\n"
        if "path" in proxy_data["ws-opts"]:
            proxy_yaml += f"      path: {proxy_data['ws-opts']['path']}\n"
        if "headers" in proxy_data["ws-opts"] and "Host" in proxy_data["ws-opts"]["headers"]:
            proxy_yaml += f"      headers:\n"
            proxy_yaml += f"        Host: {proxy_data['ws-opts']['headers']['Host']}\n"

    footer = f"""
proxy-groups:
  - name: box
    type: select
    proxies:
      - "{proxy_data['name']}"

rules:
  - MATCH,box

external-controller: 0.0.0.0:9090
external-ui: ./dashboard
"""
    return config_template + proxy_yaml + footer

def copy_to_box_root(filename):
    """نقل الملف مع كسر حماية Mount Namespace الخاصة بالأندرويد"""
    
    target_dir = "/data/data/com.boxproxy.box/files/box/mihomo"
    source_path = os.path.abspath(filename)
    
    try:
        if not os.path.exists(source_path):
            print(f"❌ خطأ: الملف لم يتم إنشاؤه في المسار: {source_path}")
            return

        # المحاولة الأولى: استخدام su -mm (Mount Master) للهروب من العزل الوهمي (يفضل لـ Magisk)
        cmd_magisk = f"su -mm -c 'mkdir -p \"{target_dir}\" && cat > \"{target_dir}/{filename}\" && chmod 777 \"{target_dir}/{filename}\"'"
        
        with open(source_path, 'rb') as f:
            result = subprocess.run(cmd_magisk, shell=True, stdin=f, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            
        # المحاولة الثانية: إذا فشل الأمر الأول، نستخدم nsenter (الحل النهائي لـ KernelSU/APatch)
        if result.returncode != 0:
            cmd_kernelsu = f"su -c 'nsenter -t 1 -m -- sh -c \"mkdir -p \\\"{target_dir}\\\" && cat > \\\"{target_dir}/{filename}\\\" && chmod 777 \\\"{target_dir}/{filename}\\\"\"'"
            with open(source_path, 'rb') as f:
                result = subprocess.run(cmd_kernelsu, shell=True, stdin=f, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

        if result.returncode == 0:
            print(f"🚀 تم النقل بنجاح! تم كسر حماية الأندرويد ووضع التكوين في:\n{target_dir}/{filename}")
            os.remove(source_path)
        else:
            error_msg = result.stderr.decode('utf-8', errors='ignore')
            print(f"⚠️ فشلت عملية النقل نهائياً، المشكلة من الروت:\n{error_msg}")
            
    except Exception as e:
        print(f"❌ حدث خطأ غير متوقع أثناء عملية النقل: {e}")

if __name__ == "__main__":
    show_banner()
    print(color("الصيغ المدعومة: VLESS  •  VMess  •  Trojan  •  WireGuard", YELLOW + BOLD))
    print()
    link = input(color("أدخل رابط التكوين: ", YELLOW + BOLD)).strip()
    try:
        if not link:
            error("لم يتم إدخال أي رابط")
            sys.exit(1)

        if link.startswith("vmess://"):
            info("جاري تحليل رابط VMess ...")
            proxy_data = parse_vmess(link)
        elif link.startswith("vless://"):
            info("جاري تحليل رابط VLESS ...")
            proxy_data = parse_vless(link)
        elif link.startswith("trojan://"):
            info("جاري تحليل رابط Trojan ...")
            proxy_data = parse_trojan(link)
        elif link.startswith("wireguard://"):
            info("جاري تحليل رابط WireGuard ...")
            proxy_data = parse_wireguard(link)
        else:
            error("رابط غير مدعوم")
            sys.exit(1)

        success(f"تم التعرف على الخادم: {proxy_data['name']}")
        full_config = generate_full_config(proxy_data)
        
        custom_filename = f"{proxy_data['name']}.yaml"
        
        with open(custom_filename, "w", encoding="utf-8") as f:
            f.write(full_config)

        success(f"تم إنشاء التكوين: {custom_filename}")
        print(color("  الحقوق: محمد 🇮🇶 سلوم | @SELOOM1", YELLOW + BOLD))
        print(color("  انضم إلى قناة التلكرام: https://t.me/freevpsiraq", MAGENTA))
        info("جاري نقل التكوين إلى Box4Magisk ...")
        copy_to_box_root(custom_filename)
        
    except Exception as e:
        error(f"حدث خطأ أثناء التحويل: {e}")
