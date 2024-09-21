import discord 
from discord import app_commands 
intents = discord.Intents.default() 
client = discord.Client(intents=intents) 
tree = app_commands.CommandTree(client)

from enum import Enum
from datetime import datetime
from collections import deque
import subprocess
import threading
import asyncio
import platform
import os
from shutil import copystat,Error,copy2
import sys
import logging
import requests
import json

#プロンプトを送る
print()

#サーバープロセス
process = None

#起動した時刻
time = datetime.now().strftime("%Y-%m-%d_%H_%M_%S")

#外部変数
token = None
temp_path = None 

#現在のディレクトリ
now_path = "/".join(__file__.replace("\\","/").split("/")[:-1])
# 相対パス
if now_path == "": now_path = "."
#現在のファイル(server.py)
now_file = __file__.replace("\\","/").split("/")[-1]

def wait_for_keypress():
    print("please press any key to continue...")
    if platform.system() == "Windows":
        import msvcrt
        while True:
            if msvcrt.kbhit():
                msvcrt.getch()
                break
        exit()
    else:
        import sys
        import termios
        import tty
        fd = sys.stdin.fileno()
        old_settings = termios.tcgetattr(fd)
        try:
            tty.setraw(sys.stdin.fileno())
            sys.stdin.read(1)
        finally:
            termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)
            exit()

config_file_place = now_path + "/" + ".config"

def make_config():
    if not os.path.exists(config_file_place):
        file = open(config_file_place,"w")
        server_path = now_path
        default_backup_path = server_path + "/../backup/" + server_path.split("/")[-1]
        if not os.path.exists(default_backup_path):
            os.makedirs(default_backup_path)
        default_backup_path = os.path.realpath(default_backup_path) + "/"
        print("default backup path: " + default_backup_path)
        config_dict = {"allow":{"ip":True},"server_path":now_path + "/","allow_mccmd":["list","whitelist","tellraw","w","tell"],"server_name":"bedrock_server.exe","log":{"server":True,"all":False},"backup_path": default_backup_path,"mc":True,"lang":"en","force_admin":[]}
        json.dump(config_dict,file,indent=4)
        config_changed = True
    else:
        try:
            config_dict = json.load(open(now_path + "/"  + ".config","r"))
        except json.decoder.JSONDecodeError:
            print("config file is broken. please delete .config and try again.")
            wait_for_keypress()
        #要素がそろっているかのチェック
        def check(cfg):
            if "allow" not in cfg:
                cfg["allow"] = {"ip":True}
            elif "ip" not in cfg["allow"]:
                cfg["allow"]["ip"] = True
            if "server_path" not in cfg:
                cfg["server_path"] = now_path + "/"
            if "allow_mccmd" not in cfg:
                cfg["allow_mccmd"] = ["list","whitelist","tellraw","w","tell"]
            if "server_name" not in cfg:
                cfg["server_name"] = "bedrock_server.exe"
            if "log" not in cfg:
                cfg["log"] = {"server":True,"all":False}
            else:
                if "server" not in cfg["log"]:
                    cfg["log"]["server"] = True
                if "all" not in cfg["log"]:
                    cfg["log"]["all"] = False
            if "backup_path" not in cfg:
                try:
                    server_name = cfg["server_path"].split("/")[-2]
                except IndexError:
                    print(f"server_path is broken. please check config file and try again.\ninput : {cfg['server_path']}")
                    wait_for_keypress()
                if server_name == "":
                    print("server_path is broken. please check config file and try again.")
                    wait_for_keypress()
                cfg["backup_path"] = cfg["server_path"] + "../backup/" + server_name
                cfg["backup_path"] = os.path.realpath(cfg["backup_path"]) + "/"
                if not os.path.exists(cfg["backup_path"]):
                    os.makedirs(cfg["backup_path"])
            if "mc" not in cfg:
                cfg["mc"] = True
            if "lang" not in cfg:
                cfg["lang"] = "en"
            if "force_admin" not in cfg:
                cfg["force_admin"] = []
            return cfg
        if config_dict != check(config_dict.copy()):
            check(config_dict)
            file = open(now_path + "/"  + ".config","w")
            #ログ
            config_changed = True
            json.dump(config_dict,file,indent=4)
            file.close()
        else: config_changed = False
    return config_dict,config_changed
def to_config_safe(config):
    #"force_admin"に重複があれば削除する
    save = False
    if len(config["force_admin"]) > len(set(config["force_admin"])):
        config["force_admin"] = list(set(config["force_admin"]))
        save = True
    if save:
        file = open(config_file_place,"w")
        json.dump(config,file,indent=4)
        file.close()

config,config_changed = make_config()
#整合性チェック
to_config_safe(config)
#ロガー作成前なので最小限の読み込み
try:
    log = config["log"]
    server_path = config["server_path"]
    if not os.path.exists(server_path):
        print("not exist server_path dir")
        wait_for_keypress()
    #ログファイルの作成
    def make_logs_file():
        #./logsが存在しなければlogsを作成する
        if not os.path.exists(now_path + "/" + "logs"):
            os.makedirs(now_path + "/" + "logs")
        if not os.path.exists(server_path + "logs"):
            os.makedirs(server_path + "logs")
    make_logs_file()
except KeyError:
    print("(log or server_path) in config file is broken. please input true or false and try again.")
    wait_for_keypress()

#--------------------------------------------------------------------------------------------ログ関連
class Color(Enum):
    BLACK          = '\033[30m'#(文字)黒
    RED            = '\033[31m'#(文字)赤
    GREEN          = '\033[32m'#(文字)緑
    YELLOW         = '\033[33m'#(文字)黄
    BLUE           = '\033[34m'#(文字)青
    MAGENTA        = '\033[35m'#(文字)マゼンタ
    CYAN           = '\033[36m'#(文字)シアン
    WHITE          = '\033[37m'#(文字)白
    COLOR_DEFAULT  = '\033[39m'#文字色をデフォルトに戻す
    BOLD           = '\033[1m'#太字
    UNDERLINE      = '\033[4m'#下線
    INVISIBLE      = '\033[08m'#不可視
    REVERCE        = '\033[07m'#文字色と背景色を反転
    BG_BLACK       = '\033[40m'#(背景)黒
    BG_RED         = '\033[41m'#(背景)赤
    BG_GREEN       = '\033[42m'#(背景)緑
    BG_YELLOW      = '\033[43m'#(背景)黄
    BG_BLUE        = '\033[44m'#(背景)青
    BG_MAGENTA     = '\033[45m'#(背景)マゼンタ
    BG_CYAN        = '\033[46m'#(背景)シアン
    BG_WHITE       = '\033[47m'#(背景)白
    BG_DEFAULT     = '\033[49m'#背景色をデフォルトに戻す
    RESET          = '\033[0m'#全てリセット
    def __add__(self, other):
        if isinstance(other, Color):
            return self.value + other.value
        elif isinstance(other, str):
            return self.value + other
        else:
            raise NotImplementedError
    def __radd__(self, other):
        if isinstance(other, Color):
            return other.value + self.value
        elif isinstance(other, str):
            return other + self.value
        else:
            raise NotImplementedError

class Formatter():
    levelname_size = 8
    name_size = 10
    class ColoredFormatter(logging.Formatter):
        # ANSI escape codes for colors
        COLORS = {
            'DEBUG': Color.BOLD + Color.WHITE,   # White
            'INFO': Color.BOLD + Color.BLUE,    # Blue
            'WARNING': Color.BOLD + Color.YELLOW, # Yellow
            'ERROR': Color.BOLD + Color.RED,   # Red
            'CRITICAL': Color.BOLD + Color.MAGENTA # Red background
        }
        RESET = '\033[0m'  # Reset color
        BOLD_BLACK = Color.BOLD + Color.BLACK  # Bold Black

        def format(self, record):
            # Format the asctime
            record.asctime = self.formatTime(record, self.datefmt)
            bold_black_asctime = f"{self.BOLD_BLACK}{record.asctime}{self.RESET}"
            
            # Adjust level name to be 8 characters long
            original_levelname = record.levelname
            padded_levelname = original_levelname.ljust(Formatter.levelname_size)
            original_name = record.name
            padded_name = original_name.ljust(Formatter.name_size)
            
            # Apply color to the level name only
            color = self.COLORS.get(original_levelname, self.RESET)
            colored_levelname = f"{color}{padded_levelname}{self.RESET}"
            
            # Get the formatted message
            message = record.getMessage()
            
            # Create the final formatted message
            formatted_message = f"{bold_black_asctime} {colored_levelname} {padded_name}: {message}"
            
            return formatted_message

    class MinecraftFormatter(logging.Formatter):
        
        # ANSI escape codes for colors
        COLORS = {
            'MC': Color.BOLD + Color.GREEN,   # Green
        }
        RESET = '\033[0m'  # Reset color
        BOLD_BLACK = Color.BOLD + Color.BLACK  # Bold Black

        def format(self, record):
            # Format the asctime
            record.asctime = self.formatTime(record, self.datefmt)
            bold_black_asctime = f"{self.BOLD_BLACK}{record.asctime}{self.RESET}"
            
            # Apply color to the level name only
            color = self.COLORS["MC"]
            colored_levelname = f"{color}MC      {self.RESET}"
            
            # Get the formatted message
            message = record.getMessage()
            # msg_type = message.split()
            # if len(msg_type) > 2:
            #     msg_type = msg_type[2][:-1]
            # if msg_type == "INFO":
            #     msg_color = Color.CYAN
            # elif msg_type == "ERROR":
            #     msg_color = Color.RED
            # else:
            #     msg_color = Color.RESET
            what_type = message.upper()
            if "INFO" in what_type:
                msg_color = Color.CYAN
            elif "ERROR" in what_type:
                msg_color = Color.RED
            elif "WARN" in what_type:
                msg_color = Color.YELLOW
            else:
                msg_color = Color.RESET

            message = msg_color + message + Color.RESET
            
            # Create the final formatted message
            formatted_message = f"{bold_black_asctime} {colored_levelname} {message}"
            
            return formatted_message

    class DefaultConsoleFormatter(logging.Formatter):
        def format(self, record):
            # Format the asctime
            record.asctime = self.formatTime(record, self.datefmt)
            
            # Adjust level name to be 8 characters long
            original_levelname = record.levelname
            padded_levelname = original_levelname.ljust(Formatter.levelname_size)
            original_name = record.name
            padded_name = original_name.ljust(Formatter.name_size)
            
            
            # Get the formatted message
            message = record.getMessage()
            
            # Create the final formatted message
            formatted_message = f"{record.asctime} {padded_levelname} {padded_name}: {message}"
            
            return formatted_message
        
    class MinecraftConsoleFormatter(logging.Formatter):
        def format(self, record):
            # Format the asctime
            record.asctime = self.formatTime(record, self.datefmt)
            
            padded_levelname = "MC".ljust(Formatter.levelname_size)
            
            
            # Get the formatted message
            message = record.getMessage()
            
            # Create the final formatted message
            formatted_message = f"{record.asctime} {padded_levelname} {message}"
            
            return formatted_message


#logger
dt_fmt = '%Y-%m-%d %H:%M:%S'
console_formatter = Formatter.ColoredFormatter(f'{Color.BOLD + Color.BG_BLACK}%(asctime)s %(levelname)s %(name)s: %(message)s', dt_fmt)
file_formatter = Formatter.DefaultConsoleFormatter('%(asctime)s %(levelname)s %(name)s: %(message)s', dt_fmt)
#/log用のログ保管場所
log_msg = deque(maxlen=10)
def create_logger(name,console_formatter=console_formatter,file_formatter=file_formatter):
    class DequeHandler(logging.Handler):
        def __init__(self, deque):
            super().__init__()
            self.deque = deque

        def emit(self, record):
            log_entry = self.format(record)
            self.deque.append(log_entry)
    logger = logging.getLogger(name)
    logger.setLevel(logging.DEBUG)
    console = logging.StreamHandler()
    console.setLevel(logging.DEBUG)
    console.setFormatter(console_formatter)
    logger.addHandler(console)
    if log["all"]:
        f = time + ".log"
        file = logging.FileHandler(now_path + "/logs/all " + f,encoding="utf-8")
        file.setLevel(logging.DEBUG)
        file.setFormatter(file_formatter)
        logger.addHandler(file)
    deque_handler = DequeHandler(log_msg)
    deque_handler.setLevel(logging.DEBUG)
    deque_handler.setFormatter(console_formatter)  # フォーマットは任意で設定
    logger.addHandler(deque_handler)
    return logger

#ロガーの作成
logger_name = ["stop", "start", "exit", "ready", "cmd", "help", "backup", "replace", "ip", "sys"]

stop_logger = create_logger("stop")
start_logger = create_logger("start")
exit_logger = create_logger("exit")
ready_logger = create_logger("ready")
cmd_logger = create_logger("cmd")
help_logger = create_logger("help")
backup_logger = create_logger("backup")
replace_logger = create_logger("replace")
ip_logger = create_logger("ip")
sys_logger = create_logger("sys")
log_logger = create_logger("log")
permission_logger = create_logger("permission")
admin_logger = create_logger("admin")
lang_logger = create_logger("lang")
minecraft_logger = create_logger("minecraft",Formatter.MinecraftFormatter(f'{Color.BOLD + Color.BG_BLACK}%(asctime)s %(levelname)s %(name)s: %(message)s', dt_fmt),Formatter.MinecraftConsoleFormatter('%(asctime)s %(levelname)s %(name)s: %(message)s', dt_fmt))
#--------------------------------------------------------------------------------------------


#configの読み込み
try:
    allow_cmd = set(config["allow_mccmd"])
    server_name = config["server_name"]
    if not os.path.exists(server_path + server_name):
        sys_logger.error("not exist " + server_path + server_name + " file. please check your config.")
        wait_for_keypress()
    allow = {"ip":config["allow"]["ip"]}
    log = config["log"]
    now_dir = server_path.replace("\\","/").split("/")[-2]
    backup_path = config["backup_path"]
    lang = config["lang"]
    bot_admin = set(config["force_admin"])
except KeyError:
    sys_logger.error("config file is broken. please delete .config and try again.")
    wait_for_keypress()



args = sys.argv[1:]
do_init = False

#引数を処理する。
for i in args:
    arg = i.split("=")
    if arg[0] == "-init":
        do_init = True
        # pass

#updateプログラムが存在しなければdropboxから./update.pyにコピーする
if not os.path.exists(now_path + "/" + "update.py") or do_init:
    url='https://www.dropbox.com/scl/fi/w93o5sndwaiuie0otorm4/update.py?rlkey=gh3gqbt39iwg4afey11p99okp&st=2i9a9dzp&dl=1'
    filename= now_path + '/' + 'update.py'

    urlData = requests.get(url).content

    with open(filename ,mode='wb') as f: # wb でバイト型を書き込める
        f.write(urlData)
    #os.system("curl https://www.dropbox.com/scl/fi/w93o5sndwaiuie0otorm4/update.py?rlkey=gh3gqbt39iwg4afey11p99okp&st=2i9a9dzp&dl=1 -o ./update.py")



def make_token_file():
    global token
    #./.tokenが存在しなければ.tokenを作成する
    if not os.path.exists(now_path + "/" + ".token"):
        file = open(now_path + "/" + ".token","w",encoding="utf-8")
        file.write("ここにtokenを入力")
        file.close()
        sys_logger.error("please write token in" + now_path + "/" +".token")
        #ブロッキングする
        wait_for_keypress()
    #存在するならtokenを読み込む(json形式)
    else:
        token = open(now_path + "/" + ".token","r",encoding="utf-8").read()

def make_temp():
    global temp_path
    #tempファイルの作成場所
    if platform.system() == 'Windows':
        # %temp%/mcserver を作成
        temp_path = os.environ.get('TEMP') + "/mcserver"
    else:
        # /tmp/mcserver を作成
        temp_path = "/tmp/mcserver"

    #tempファイルの作成
    if not os.path.exists(temp_path):
        os.mkdir(temp_path)


make_token_file()
make_temp()

#asyncioの制限を回避
if platform.system() == 'Windows':
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

#/cmdに関する定数
cmd_logs = deque(maxlen=100)


#ログをdiscordにも返す可能性がある
is_back_discord = False

#java properties の読み込み
def properties_to_dict(filename):
    properties = {}
    try:
        with open(filename) as file:
            for line in file:
                line = line.strip()
                if line and not line.startswith('#'):
                    if line.startswith(' ') or line.startswith('\t'):
                        line = line[1:]
                    key, value = line.split('=', 1)
                    properties[key] = value
        return properties
    except Exception as e:#ファイルが存在しなければ存在しないことを出力して終了
        sys_logger.error(e)
        sys_logger.info("not exist server.properties file in " + server_path + ". if you are not using a minecraft server, please set mc to false in .config .if not, restart it and server.properties should be generated in the server hierarchy.")
        return {}

#minecraftサーバーであればpropertiesを読み込む
if config["mc"]:
    properties = properties_to_dict(server_path + "server.properties")
    sys_logger.info("read properties file -> " + server_path + "server.properties")

# 権限データ
COMMAND_PERMISSION = {
    "/stop       ":1,
    "/start      ":1,
    "/exit       ":1,
    "/cmd        ":1,
    "/help       ":0,
    "/backup     ":1,
    "/replace    ":2,
    "/ip         ":0,
    "/logs       ":1,
    "/force_admin":2,
    "/permission ":0,
    "/lang       ":2,
}

async def get_text_dat():
    global HELP_MSG, COMMAND_DESCRIPTION, send_help, RESPONSE_MSG, ACTIVITY_NAME 
# テキストデータ領域-----------------------------------------------------------------------------------------------------------------------------------------------------------------------------

#help
    HELP_MSG = {
        "ja":{
            "/stop       ":"サーバーを停止します。但し起動していない場合にはエラーメッセージを返します。",
            "/start      ":"サーバーを起動します。但し起動している場合にはエラーメッセージを返します。",
            "/exit       ":"botを終了します。サーバーを停止してから実行してください。終了していない場合にはエラーメッセージを返します。\nまたこのコマンドを実行した場合次にbotが起動するまですべてのコマンドが無効になります。",
            "/cmd        ":f"/cmd <mcコマンド> を用いてサーバーコンソール上でコマンドを実行できます。使用できるコマンドは{allow_cmd}です。",
            "/backup     ":"/backup [ワールド名] でワールドデータをバックアップします。ワールド名を省略した場合worldsをコピーします。サーバーを停止した状態で実行してください",
            "/replace    ":"/replace <py file> によってbotのコードを置き換えます。",
            "/ip         ":"サーバーのIPアドレスを表示します。",
            "/logs       ":"サーバーのログを表示します。引数を与えた場合にはそのファイルを、与えられなければ動作中に得られたログから最新の10件を返します。",
            "/force_admin":"/force_admin <add/remove> <user> で、userのbot操作権利を付与/剥奪することができます。",
            "/permission ":"/permission <user> で、userのbot操作権利を表示します。",
            "/lang       ":"/lang <lang> で、botの言語を変更します。"
        },
        "en":{
            "/stop       ":"Stop the server. If the server is not running, an error message will be returned.",
            "/start      ":"Start the server. If the server is running, an error message will be returned.",
            "/exit       ":"Exit the bot. Stop the server first and then run the command. If the server is not running, an error message will be returned.\n",
            "/cmd        ":f"/cmd <mc command> can be used to execute commands in the server console. The available commands are {allow_cmd}.",
            "/backup     ":"/backup [world name] copies the world data. If no world name is given, the worlds will be copied.",
            "/replace    ":"/replace <py file> replaces the bot's code.",
            "/ip         ":"The server's IP address will be displayed to discord.",
            "/logs       ":"Display the server's logs. If an argument is given, that file will be returned. If no argument is given, the latest 10 logs will be returned.",
            "/force_admin":"/force_admin <add/remove> <user> gives or removes user's bot operation rights.",
            "/permission ":"/permission <user> displays the user's bot operation rights.",
            "/lang       ":"/lang <lang> changes the bot's language.",
        },
    }
        

    COMMAND_DESCRIPTION = {
        "ja":{
            "stop":"サーバーを停止します。",
            "start":"サーバーを起動します。",
            "exit":"botを終了します。",
            "cmd":"サーバーにマインクラフトコマンドを送信します。",
            "backup":"ワールドデータをバックアップします。引数にはワールドファイルの名前を指定します。入力しない場合worldsが選択されます。",
            "replace":"このbotのコードを<py file>に置き換えます。このコマンドはbotを破壊する可能性があります。",
            "ip":"サーバーのIPアドレスを表示します。",
            "logs":"サーバーのログを表示します。引数にはファイル名を指定します。入力しない場合は最新の10件のログを返します。",
            "help":"このbotのコマンド一覧を表示します。",
            "admin":{
                "force":"選択したユーザに対してbotをdiscord管理者と同等の権限で操作できるようにします。",
            },
            "permission":"選択したユーザに対してbot操作権限を表示します。",
            "lang":"botの言語を変更します。引数には言語コードを指定します。",
        },
        "en":{
            "stop":"Stop the server.",
            "start":"Start the server.",
            "exit":"Exit the bot.",
            "cmd":"Send a Minecraft command to the server.",
            "backup":"Copy the world data. If no argument is given, the worlds will be copied.",
            "replace":"Replace the bot's code with <py file>.",
            "ip":"The server's IP address will be displayed to discord.",
            "logs":"Display server logs. With an argument, return that file. Without, return the latest 10 logs.",
            "help":"Display this bot's command list.",
            "admin":{
                "force":"Force the selected user to have the same permissions as the bot, as discord administrator.",
            },
            "permission":"Display the bot operation rights of the selected user.",
            "lang":"Change the bot's language. With an argument, specify the language code.",
        },
    }

    #今後も大きくなることが予想されるので、ここで条件分岐する
    if lang == "ja":
        send_help = "詳細なHelpはこちらを参照してください\n<https://github.com/mikatan-mikan/server-bot/blob/main/README.md#%E3%82%B3%E3%83%9E%E3%83%B3%E3%83%89%E4%B8%80%E8%A6%A7>\n"
        RESPONSE_MSG = {
            "other":{
                "no_permission":"管理者権限を持っていないため実行できません",
                "is_running":"サーバーが起動しているため実行できません",
                "is_not_running":"サーバーが起動していないため実行できません",
            },
            "stop":{
                "success":"サーバーを停止します",
            },
            "start":{
                "success":"サーバーを起動します",
            },
            "cmd":{
                "skipped_cmd":"コマンドが存在しない、または許可されないコマンドです",
            },
            "backup":{
                "now_backup":"バックアップ中・・・",
                "data_not_found":"データが見つかりません",
                "success":"バックアップが完了しました！",
            },
            "replace":{
                "progress":"更新プログラムの適応中・・・",
            },
            "ip":{
                "not_allow":"このコマンドはconfigにより実行を拒否されました",
                "get_ip_failed":"IPアドレスを取得できません",
                "msg_startwith":"サーバーIP : "
            },
            "logs":{
                "cant_access_other_dir":"他のディレクトリにアクセスすることはできません。この操作はログに記録されます。",
                "not_found":"指定されたファイルが見つかりません。この操作はログに記録されます。",
            },
            "exit":{
                "success":"botを終了します...",
            },
            "error":{
                "error_base":"エラーが発生しました。\n",
            },
            "admin":{
                "force":{
                    "already_added":"このユーザーはすでにbotの管理者権限を持っています",
                    "add_success":"{}にbotの管理者権限を与えました",
                    "remove_success":"{}からbotの管理者権限を剥奪しました",
                    "already_removed":"このユーザーはbotの管理者権限を持っていません",
                },
            },
            "permission":{
                "success":"{} の権限 : \ndiscord管理者権限 : {}\nbot管理者権限 : {}",
            },
            "lang":{
                "success":"言語を{}に変更しました",
            },
        }
        ACTIVITY_NAME = {
            "starting":"さーばーきどう",
            "running":"さーばーじっこう",
            "ending":"さーばーおしまい",
            "ended":"さーばーとじてる",
        }
    elif lang == "en":
        send_help = "Details on the help can be found here\n<https://github.com/mikatan-mikan/server-bot/blob/main/README.md#%E3%82%B3%E3%83%9E%E3%83%B3%E3%83%89%E4%B8%80%E8%A6%A7>\n"
        RESPONSE_MSG = {
            "other":{
                "no_permission":"Permission denied",
                "is_running":"Server is still running",
                "is_not_running":"Server is not running",
            },
            "stop":{
                "success":"The server has been stopped",
            },
            "start":{
                "success":"The server has been started",
            },
            "cmd":{
                "skipped_cmd":"The command is not found or not allowed",
            },
            "backup":{
                "now_backup":"Backup in progress",
                "data_not_found":"Data not found",
                "success":"Backup complete!",
            },
            "replace":{
                "progress":"Applying update program",
            },
            "ip":{
                "not_allow":"This command is denied by config",
                "get_ip_failed":"Failed to get IP address",
                "msg_startwith":"Server IP : "
            },
            "logs":{
                "cant_access_other_dir":"Cannot access other directory. This operation will be logged.",
                "not_found":"The specified file was not found. This operation will be logged.",
            },
            "exit":{
                "success":"The bot is exiting...",
            },
            "error":{
                "error_base":"An error has occurred.\n",
            },
            "admin":{
                "force":{
                    "already_added":"The user has already been added as an administrator",
                    "add_success":"Added as an administrator to {}",
                    "already_removed":"The user has already been removed as an administrator",
                    "remove_success":"Removed as an administrator from {}",
                },
            },
            "permission":{
                "success":"{}'s permission : \ndiscord administrator permission : {}\nbot administrator permission : {}",
            },
            "lang":{
                "success":"Language changed to {}",
            },
        }
        ACTIVITY_NAME = {
            "starting":"Server go!",
            "running":"Server whoosh!",
            "ending":"Server stopping!",
            "ended":"Server stop!",
        }
    def make_send_help():
        global send_help
        send_help += "```"
        for key in HELP_MSG[lang]:
            send_help += key + " " + HELP_MSG[lang][key] + "\n"
        send_help += "```"
    make_send_help()


get_text = asyncio.run(get_text_dat())
sys_logger.info('create text data')
# ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------


async def not_enough_permission(interaction: discord.Interaction,logger: logging.Logger) -> bool:
    logger.error('permission denied')
    await interaction.response.send_message(RESPONSE_MSG["other"]["no_permission"],ephemeral = True)


async def is_administrator(user: discord.User) -> bool:
    if not user.guild_permissions.administrator:
        return False
    return True

async def is_force_administrator(user: discord.User) -> bool:
    #user idがforce_adminに含まれないなら
    if user.id not in config["force_admin"]:
        return False
    return True

#既にサーバが起動しているか
async def is_running_server(interaction: discord.Interaction,logger: logging.Logger) -> bool:
    global process
    if process is not None:
        logger.error('server is still running')
        await interaction.response.send_message(RESPONSE_MSG["other"]["is_running"],ephemeral = True)
        return True
    return False

#サーバーが閉まっている状態か
async def is_stopped_server(interaction: discord.Interaction,logger: logging.Logger) -> bool:
    global process
    if process is None:
        logger.error('server is not running')
        await interaction.response.send_message(RESPONSE_MSG["other"]["is_not_running"],ephemeral = True)
        return True
    return False

async def reload_config():
    import json
    with open(config_file_place, 'r') as f:
        global config
        config = json.load(f)
        #TODO
    

async def rewrite_config(config: dict) -> bool:
    try:
        with open(config_file_place, 'w') as f:
            import json
            json.dump(config, f,indent=4)
        return True
    except:
        return False


async def dircp_discord(src, dst, interaction: discord.Interaction, symlinks=False) -> None:
    global exist_files, copyed_files
    """
    src : コピー元dir
    dst : コピー先dir
    symlinks : リンクをコピーするか
    """
    #表示サイズ
    bar_width = 30
    #送信制限
    max_send = 20
    dst += datetime.now().strftime('%Y-%m-%d_%H_%M_%S')
    exist_files = 0
    for root, dirs, files in os.walk(top=src, topdown=False):
        exist_files += len(files)
    #何ファイルおきにdiscordへ送信するか(最大100回送信するようにする)
    send_sens = int(exist_files / max_send) if exist_files > max_send else 1
    copyed_files = 0
    async def copytree(src, dst, symlinks=False):
        global copyed_files
        names = os.listdir(src)
        os.makedirs(dst)
        errors = []
        for name in names:
            srcname = os.path.join(src, name)
            dstname = os.path.join(dst, name)
            try:
                if symlinks and os.path.islink(srcname):
                    linkto = os.readlink(srcname)
                    os.symlink(linkto, dstname)
                elif os.path.isdir(srcname):
                    await copytree(srcname, dstname, symlinks)
                else:
                    copy2(srcname, dstname)
                    copyed_files += 1
                    if copyed_files % send_sens == 0 or copyed_files == exist_files:
                        now = RESPONSE_MSG["backup"]["now_backup"]
                        if copyed_files == exist_files:
                            now = RESPONSE_MSG["backup"]["success"]
                        await interaction.edit_original_response(content=f"{now}\n```{int((copyed_files / exist_files * bar_width) - 1) * '='}☆{((bar_width) - int(copyed_files / exist_files * bar_width)) * '-'}  ({'{: 5}'.format(copyed_files)} / {'{: 5}'.format(exist_files)}) {'{: 3.3f}'.format(copyed_files / exist_files * 100)}%```")
            except OSError as why:
                errors.append((srcname, dstname, str(why)))
            # catch the Error from the recursive copytree so that we can
            # continue with other files
            except Error as err:
                errors.extend(err.args[0])
        try:
            copystat(src, dst)
        except OSError as why:
            # can't copy file access times on Windows
            if why.winerror is None:
                errors.extend((src, dst, str(why)))
        if errors:
            raise Error(errors)
    await copytree(src, dst, symlinks)

#logger thread
def server_logger(proc:subprocess.Popen,ret):
    global process,is_back_discord 
    if log["server"]:
        file = open(file = server_path + "logs/server " + datetime.now().strftime("%Y-%m-%d_%H_%M_%S") + ".log",mode = "w")
    while True:
        try:
            logs = proc.stdout.readline()
        except Exception as e:
            sys_logger.error(e)
            continue
        # プロセスが終了している
        if logs == '': 
            if proc.poll() is not None:
                break
            continue
        #ログが\nのみであれば不要
        if logs == "\n":
            continue
        #後ろが\nなら削除
        logs = logs.rstrip("\n")
        minecraft_logger.info(logs)
        if log["server"]:
            file.write(logs + "\n")
            file.flush()
        if is_back_discord:
            cmd_logs.append(logs)
            is_back_discord = False
    #プロセスを終了させる
    process = None

async def print_user(logger: logging.Logger,user: discord.user):
    logger.info('command used by ' + str(user))

#ローカルファイルの読み込み結果出力
sys_logger.info("read token file -> " + now_path + "/" +".token")
sys_logger.info("read config file -> " + now_path + "/" +".config")
sys_logger.info("config -> " + str(config))
if config_changed: sys_logger.info("added config because necessary elements were missing")

class ServerBootException(Exception):pass

@client.event
async def on_ready():
    global process
    ready_logger.info('discord bot logging on')
    try:
        #サーバーの起動
        await client.change_presence(activity=discord.Game(ACTIVITY_NAME["starting"]))
        if process is  None:
            #server を実行する
            process = subprocess.Popen([server_path + server_name],cwd=server_path,shell=True,stdin=subprocess.PIPE,stdout=subprocess.PIPE,encoding="utf-8")
            threading.Thread(target=server_logger,args=(process,deque())).start()
            ready_logger.info('server starting')
        else:
            ready_logger.info('skip server starting because server already running')
        # アクティビティを設定 
        await client.change_presence(activity=discord.Game(ACTIVITY_NAME["running"])) 
        # スラッシュコマンドを同期 
        await tree.sync()
    except Exception as e:
        sys_logger.error("error on ready -> ",e)

#start
@tree.command(name="start",description=COMMAND_DESCRIPTION[lang]["start"])
async def start(interaction: discord.Interaction):
    await print_user(start_logger,interaction.user)
    global process
    if await is_running_server(interaction,start_logger): return
    start_logger.info('server starting')
    process = subprocess.Popen([server_path + server_name],cwd=server_path,shell=True,stdin=subprocess.PIPE,stdout=subprocess.PIPE,encoding="utf-8")
    await interaction.response.send_message(RESPONSE_MSG["start"]["success"])
    threading.Thread(target=server_logger,args=(process,deque())).start()
    await client.change_presence(activity=discord.Game(ACTIVITY_NAME["running"]))

#/stop
@tree.command(name="stop",description=COMMAND_DESCRIPTION[lang]["stop"])
async def stop(interaction: discord.Interaction):
    await print_user(stop_logger,interaction.user)
    global process
    #管理者権限を要求
    if not await is_administrator(interaction.user) and not await is_force_administrator(interaction.user): 
        #両方not(権限がないなら)
        await not_enough_permission(interaction,stop_logger)
        return
    #サーバー起動確認
    if await is_stopped_server(interaction,stop_logger): return
    stop_logger.info('server stopping')
    await interaction.response.send_message(RESPONSE_MSG["stop"]["success"])
    process.stdin.write("stop\n")
    process.stdin.flush()
    await client.change_presence(activity=discord.Game(ACTIVITY_NAME["ending"])) 
    while True:
        #終了するまで待つ
        if process is None:
            await client.change_presence(activity=discord.Game(ACTIVITY_NAME["ended"])) 
            break
        await asyncio.sleep(1)

#/admin force <add/remove>
@tree.command(name="admin",description=COMMAND_DESCRIPTION[lang]["admin"]["force"])
@app_commands.choices(
    mode = [
        app_commands.Choice(name="add",value="add"),
        app_commands.Choice(name="remove",value="remove"),
    ],
    perm = [
        app_commands.Choice(name="force",value="force"),
    ]
)
async def admin(interaction: discord.Interaction,perm: str,mode:str,user:discord.User):
    await print_user(admin_logger,interaction.user)
    async def force():
        async def read_force_admin():
            global bot_admin
            bot_admin = set(config["force_admin"])
        if mode == "add":
            if user.id in config["force_admin"]:
                await interaction.response.send_message(RESPONSE_MSG["admin"]["force"]["already_added"])
                return
            config["force_admin"].append(user.id)
            #configファイルを変更する
            await rewrite_config(config)
            await read_force_admin()
            await interaction.response.send_message(RESPONSE_MSG["admin"]["force"]["add_success"].format(user))
        elif mode == "remove":
            if user.id not in config["force_admin"]:
                await interaction.response.send_message(RESPONSE_MSG["admin"]["force"]["already_removed"])
                return
            config["force_admin"].remove(user.id)
            #configファイルを変更する
            await rewrite_config(config)
            await read_force_admin()
            await interaction.response.send_message(RESPONSE_MSG["admin"]["force"]["remove_success"].format(user))
        admin_logger.info(f"exec force admin {mode} {user}")
    if perm == "force": await force()

#/permission <user>
@tree.command(name="permission",description=COMMAND_DESCRIPTION[lang]["permission"])
async def permission(interaction: discord.Interaction,user:discord.User,detail:bool):
    await print_user(permission_logger,interaction.user)
    value = {"admin":"☐","force_admin":"☐"}
    if await is_administrator(user): value["admin"] = "☑"
    if await is_force_administrator(user): value["force_admin"] = "☑"
    if detail:
        my_perm_level = 0 if value["admin"] == "☐" and value["force_admin"] == "☐" else 1 if value["admin"] == "☐" else 2
        can_use_cmd = {f"{key}":"☑" if COMMAND_PERMISSION[key] <= my_perm_level else "☐" for key in COMMAND_PERMISSION}
        await interaction.response.send_message(RESPONSE_MSG["permission"]["success"].format(user,value["admin"],value["force_admin"]) + "\n```\n"+"\n".join([f"{key} : {value}" for key,value in can_use_cmd.items()]) + "\n```")
    else:
        await interaction.response.send_message(RESPONSE_MSG["permission"]["success"].format(user,value["admin"],value["force_admin"]))
    permission_logger.info("send permission info : " + str(user.id) + f"({user})")

#/lang <lang>
@tree.command(name="lang",description=COMMAND_DESCRIPTION[lang]["lang"])
@app_commands.choices(
    language = [
        app_commands.Choice(name="en",value="en"),
        app_commands.Choice(name="ja",value="ja"),
    ]
)
async def language(interaction: discord.Interaction,language:str):
    """
    config の lang を変更する
    permission : discord 管理者 (2)
    lang : str "en"/"ja"
    """
    await print_user(lang_logger,interaction.user)
    global lang
    #管理者権限を要求
    if not await is_administrator(interaction.user):
        await not_enough_permission(interaction,lang_logger)
        return
    #データの書き換え
    config["lang"] = language
    lang = config["lang"]
    #configファイルを変更する
    await rewrite_config(config)
    #textデータを再構築
    await get_text_dat()
    await interaction.response.send_message(RESPONSE_MSG["lang"]["success"].format(language))
    lang_logger.info("change lang to " + lang)

#/command <mc command>
@tree.command(name="cmd",description=COMMAND_DESCRIPTION[lang]["cmd"])
async def cmd(interaction: discord.Interaction,command:str):
    await print_user(cmd_logger,interaction.user)
    global is_back_discord,cmd_logs
    #管理者権限を要求
    if not await is_administrator(interaction.user) and not await is_force_administrator(interaction.user): 
        await not_enough_permission(interaction,cmd_logger)
        return
    #サーバー起動確認
    if await is_stopped_server(interaction,cmd_logger): return
    #コマンドの利用許可確認
    if command.split()[0] not in allow_cmd:
        cmd_logger.error('unknown command : ' + command)
        await interaction.response.send_message(RESPONSE_MSG["cmd"]["skipped_cmd"])
        return
    cmd_logger.info("run command : " + command)
    process.stdin.write(command + "\n")
    process.stdin.flush()
    #結果の返却を要求する
    is_back_discord = True
    #結果を送信できるまで待機
    while True:
        #何もなければ次を待つ
        if len(cmd_logs) == 0:
            await asyncio.sleep(0.1)
            continue
        await interaction.response.send_message(cmd_logs.popleft())
        break

#/backup()
@tree.command(name="backup",description=COMMAND_DESCRIPTION[lang]["backup"])
async def backup(interaction: discord.Interaction,world_name:str = "worlds"):
    await print_user(backup_logger,interaction.user)
    global exist_files, copyed_files
    #管理者権限を要求
    if not await is_administrator(interaction.user) and not await is_force_administrator(interaction.user):
        await not_enough_permission(interaction,backup_logger) 
        return
    #サーバー起動確認
    if await is_running_server(interaction,backup_logger): return
    backup_logger.info('backup started')
    #server_path + world_namの存在確認
    if os.path.exists(server_path + world_name):
        await interaction.response.send_message("progress...\n")
        # discordにcopyed_files / exist_filesをプログレスバーで
        await dircp_discord(server_path + world_name,backup_path + "/",interaction)
        backup_logger.info('backup done')
    else:
        backup_logger.error('data not found : ' + server_path + world_name)
        await interaction.response.send_message(RESPONSE_MSG["backup"]["data_not_found"] + ":" + server_path + world_name)

#/replace <py file>
@tree.command(name="replace",description=COMMAND_DESCRIPTION[lang]["replace"])
async def replace(interaction: discord.Interaction,py_file:discord.Attachment):
    await print_user(replace_logger,interaction.user)
    #管理者権限を要求
    if not await is_administrator(interaction.user):
        await not_enough_permission(interaction,replace_logger)
        return
    #サーバー起動確認
    if await is_running_server(interaction,replace_logger): return
    replace_logger.info('replace started')
    # ファイルをすべて読み込む
    with open(temp_path + "/new_source.py","w",encoding="utf-8") as f:
        f.write((await py_file.read()).decode("utf-8").replace("\r\n","\n"))
    # discordにコードを置き換える
    replace_logger.info('replace done')
    await interaction.response.send_message(RESPONSE_MSG["replace"]["progress"])
    response = await interaction.original_response()
    #interaction id を保存
    msg_id = str(response.id)
    channel_id = str(interaction.channel_id)
    replace_logger.info("call update.py")
    replace_logger.info('replace args : ' + msg_id + " " + channel_id)
    os.execv(sys.executable,["python3",now_path + "/" + "update.py",temp_path + "/new_source.py",msg_id,channel_id,now_file])

#/ip
@tree.command(name="ip",description=COMMAND_DESCRIPTION[lang]["ip"])
async def ip(interaction: discord.Interaction):
    await print_user(ip_logger,interaction.user)
    if not allow["ip"]:
        await interaction.response.send_message(RESPONSE_MSG["ip"]["not_allow"])
        ip_logger.error('ip is not allowed')
        return
    # ipをget
    try:
        addr = requests.get("https://api.ipify.org")
    except:
        ip_logger.error('get ip failed')
        await interaction.response.send_message(RESPONSE_MSG["ip"]["get_ip_failed"])
        return
    if config["mc"]:
        ip_logger.info('get ip : ' + addr.text + ":" + properties["server-port"])
        await interaction.response.send_message(RESPONSE_MSG["ip"]["msg_startwith"] + addr.text + ":" + properties["server-port"] + "\n" + f"(ip:{addr.text} port(ポート):{properties['server-port']})")
    else:
        ip_logger.info('get ip : ' + addr.text)
        await interaction.response.send_message(RESPONSE_MSG["ip"]["msg_startwith"] + addr.text)


async def get_log_files_choice_format(interaction: discord.Interaction, current: str):
    current = current.translate(str.maketrans("/\\:","--_"))
    #全てのファイルを取得
    s_logfiles = os.listdir(server_path + "logs/")
    a_logfiles = os.listdir(now_path + "/logs/")
    logfiles = (s_logfiles + a_logfiles)
    # current と一致するものを返す & logファイル & 25個制限を実装
    logfiles = [i for i in logfiles if current in i and i.endswith(".log")][-25:]
    # open("./tmp.txt","w").write("\n".join(logfiles))
    return [
        app_commands.Choice(name = i,value = i) for i in logfiles
    ]

#/log <filename>
# filename : ログファイル名
# filename == None -> 最新のログ10件
# filename != None -> server_path + "logs/" または now_path + "logs/"の中を候補表示する
@tree.command(name="logs",description=COMMAND_DESCRIPTION[lang]["logs"])
@app_commands.autocomplete(filename = get_log_files_choice_format)
async def logs(interaction: discord.Interaction,filename:str = None):
    await print_user(log_logger,interaction.user)
    #管理者権限を要求
    if not await is_administrator(interaction.user) and not await is_force_administrator(interaction.user): 
        await not_enough_permission(interaction,log_logger)
        return
    # discordにログを送信
    if filename is None:
        await interaction.response.send_message("```ansi\n" + "\n".join(log_msg) + "\n```")
    else:
        if "/" in filename or "\\" in filename or "%" in filename:
            log_logger.error('invalid filename : ' + filename + "\n" + f"interaction user / id：{interaction.user} {interaction.user.id}")
            await interaction.response.send_message(RESPONSE_MSG["logs"]["cant_access_other_dir"])
            return
        elif not filename.endswith(".log"):
            log_logger.error('invalid filename : ' + filename + "\n" + f"interaction user / id：{interaction.user} {interaction.user.id}")
            await interaction.response.send_message(RESPONSE_MSG["logs"]["not_found"])
            return
        elif filename.startswith("server"):
            filename = server_path + "logs/" + filename
        elif filename.startswith("all"):
            filename = now_path + "/logs/" + filename
        else:
            filename = server_path + "logs/" + filename
            if not os.path.exists(filename):
                if os.path.exists(now_path + "/logs/" + filename):
                    filename = now_path + "/logs/" + filename
                else:
                    log_logger.error('invalid filename : ' + filename + "\n" + f"interaction user / id：{interaction.user} {interaction.user.id}")
                    await interaction.response.send_message(RESPONSE_MSG["logs"]["not_found"])
                    return
        #ファイルを返却
        await interaction.response.send_message(file=discord.File(filename))
    log_ = "Server logs" if filename is None else filename
    log_logger.info(f"sended logs -> {log_}")

#/help
@tree.command(name="help",description=COMMAND_DESCRIPTION[lang]["help"])
async def help(interaction: discord.Interaction):
    await print_user(help_logger,interaction.user)
    await interaction.response.send_message(send_help)
    help_logger.info('help sent')

#/exit
@tree.command(name="exit",description=COMMAND_DESCRIPTION[lang]["exit"])
async def exit(interaction: discord.Interaction):
    await print_user(exit_logger,interaction.user)
    #管理者権限を要求
    if not await is_administrator(interaction.user) and not await is_force_administrator(interaction.user): 
        await not_enough_permission(interaction,exit_logger)
        return
    #サーバが動いているなら終了
    if await is_running_server(interaction,exit_logger): return
    await interaction.response.send_message(RESPONSE_MSG["exit"]["success"])
    exit_logger.info('exit')
    await client.close()

#コマンドがエラーの場合
@tree.error
async def on_error(interaction: discord.Interaction, error: Exception):
    sys_logger.error(error)
    await interaction.response.send_message(RESPONSE_MSG["error"]["error_base"] + str(error))

# discord.py用のロガーを取得して設定
discord_logger = logging.getLogger('discord')
if log["all"]:
    file_handler = logging.FileHandler(now_path + "/logs/all " + time + ".log")
    file_handler.setFormatter(file_formatter)
    discord_logger.addHandler(file_handler)

client.run(token, log_formatter=console_formatter)

