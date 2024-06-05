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



#プロンプトを送る
print()

#サーバープロセス
process = None
server_path = os.getcwd() + "\\"
server_name = "bedrock_server.exe"

#現在のディレクトリ名を取得
now_dir = os.path.basename(os.getcwd())

#外部変数
token = None
temp_path = None 

#updateプログラムが存在しなければdropboxから./update.pyにコピーする
if not os.path.exists(server_path + "update.py"):
    from shutil import copyfile
    url='https://www.dropbox.com/scl/fi/w93o5sndwaiuie0otorm4/update.py?rlkey=gh3gqbt39iwg4afey11p99okp&st=2i9a9dzp&dl=1'
    filename='./update.py'

    urlData = requests.get(url).content

    with open(filename ,mode='wb') as f: # wb でバイト型を書き込める
        f.write(urlData)
    #os.system("curl https://www.dropbox.com/scl/fi/w93o5sndwaiuie0otorm4/update.py?rlkey=gh3gqbt39iwg4afey11p99okp&st=2i9a9dzp&dl=1 -o ./update.py")

def make_logs_file():
    #./logsが存在しなければlogsを作成する
    if not os.path.exists(server_path + "logs"):
        os.mkdir(server_path + "logs")

def make_token_file():
    global token
    #./.tokenが存在しなければ.tokenを作成する
    if not os.path.exists(server_path + ".token"):
        file = open(server_path + ".token","w")
        file.write("ここにtokenを入力")
        file.close()
        exit("トークンを./.tokenに入力してください")
    #存在するならtokenを読み込む(json形式)
    else:
        token = open(server_path + ".token","r").read()

def make_temp():
    global temp_path
    #tempファイルの作成場所
    if platform.system() == 'Windows':
        # %temp%/mcserver を作成
        temp_path = os.environ.get('TEMP') + "\\mcserver"
    else:
        # /tmp/mcserver を作成
        temp_path = "/tmp/mcserver"

    #tempファイルの作成
    if not os.path.exists(temp_path):
        os.mkdir(temp_path)

make_logs_file()
make_token_file()
make_temp()

#asyncioの制限を回避
if platform.system() == 'Windows':
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

#/cmdに関する定数
allow_cmd = set(["list","whitelist","tellraw","w","tell"])
cmd_logs = deque(maxlen=100)


#ログをdiscordにも返す可能性がある
is_back_discord = False

#help
help_str = {
    "/stop  ":"サーバーを停止します。但し起動していない場合にはエラーメッセージを返します。",
    "/start ":"サーバーを起動します。但し起動している場合にはエラーメッセージを返します。",
    "/exit  ":"botを終了します。サーバーを停止してから実行してください。終了していない場合にはエラーメッセージを返します。\nまたこのコマンドを実行した場合次にbotが起動するまですべてのコマンドが無効になります。",
    "/cmd   ":f"/cmd <mcコマンド>を用いてサーバーコンソール上でコマンドを実行できます。使用できるコマンドは{allow_cmd}です。",
    "/backup":"/backup [ワールド名] ワールドデータをバックアップします。ワールド名を省略した場合worldsをコピーします。サーバーを停止した状態で実行してください",
}
send_help = "```\n"
def make_send_help():
    global send_help
    for key in help_str:
        send_help += key + " " + help_str[key] + "\n"
    send_help += "```"
make_send_help()

async def dircp_discord(src, dst, interaction: discord.Interaction, symlinks=False):
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
                        now = "バックアップ中・・・"
                        if copyed_files == exist_files:
                            now = "バックアップが完了しました！"
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
def server_logger(proc,ret):
    global process,is_back_discord

    file = open(file = server_path + "logs\\" + datetime.now().strftime("%Y-%m-%d_%H_%M_%S") + ".log",mode = "w")
    while True:
        logs = proc.stdout.readline()
        #ログに\nが含まれない = プロセスが終了している
        if "\n" not in logs:
            break
        #ログが\nのみであれば不要
        if logs == "\n":
            continue
        minecraft_logs(logs)
        file.write(logs)
        if is_back_discord:
            cmd_logs.append(logs)
            is_back_discord = False
    ret.append("server closed")
    process = None
    file.close()

def minecraft_logs(message):
    msg_type = message.split(" ")
    if len(msg_type) >= 3:
        msg_type = msg_type[2][:-1]
    msg_color = Color.RESET
    if msg_type == "INFO":
        msg_color = Color.CYAN
    elif msg_type == "ERROR":
        msg_color = Color.RED
    decoration = Color.BOLD + Color.GREEN
    print(Color.BOLD + Color.BLACK + datetime.now().strftime('%Y-%m-%d %H:%M:%S'),end = " " + Color.RESET)
    print(decoration + "MC",end= "       " + Color.RESET)
    print(msg_color + message,end = "" + Color.RESET)

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
        padded_levelname = original_levelname.ljust(8)
        original_name = record.name
        padded_name = original_name.ljust(10)
        
        # Apply color to the level name only
        color = self.COLORS.get(original_levelname, self.RESET)
        colored_levelname = f"{color}{padded_levelname}{self.RESET}"
        
        # Get the formatted message
        message = record.getMessage()
        
        # Create the final formatted message
        formatted_message = f"{bold_black_asctime} {colored_levelname} {padded_name}: {message}"
        
        return formatted_message

#logger
dt_fmt = '%Y-%m-%d %H:%M:%S'
formatter = ColoredFormatter(f'{Color.BOLD + Color.BG_BLACK}%(asctime)s %(levelname)s %(name)s: %(message)s', dt_fmt)
def create_logger(name):

    logger = logging.getLogger(name)
    logger.setLevel(logging.DEBUG)
    ch = logging.StreamHandler()
    ch.setLevel(logging.DEBUG)
    ch.setFormatter(formatter)
    logger.addHandler(ch)
    return logger

stop_logger = create_logger("stop")
start_logger = create_logger("start")
exit_logger = create_logger("exit")
ready_logger = create_logger("ready")
cmd_logger = create_logger("cmd")
help_logger = create_logger("help")
backup_logger = create_logger("backup")
replace_logger = create_logger("replace")
ip_logger = create_logger("ip")



async def put_logs(mean,message):
    decoration = Color.RESET
    if mean == 'INFO':
        decoration = Color.BOLD + Color.BLUE
        space = "     "
    elif mean == 'ERROR':
        decoration = Color.BOLD + Color.RED
        space = "    "
    print(Color.BOLD + Color.BLACK + datetime.now().strftime('%Y-%m-%d %H:%M:%S'),end = " " + Color.RESET)
    print(decoration + mean,end= space + Color.RESET)
    print(message)

@client.event
async def on_ready():
    global process
    ready_logger.info('discord bot logging on')
    #サーバーの起動
    await client.change_presence(activity=discord.Game('さーばーきどう'))
    #server を実行する
    process = subprocess.Popen([server_path + server_name],shell=True,stdin=subprocess.PIPE,stdout=subprocess.PIPE,encoding="utf-8")
    threading.Thread(target=server_logger,args=(process,deque())).start()
    ready_logger.info('server starting')
    # アクティビティを設定 
    new_activity = f"さーばーじっこう" 
    await client.change_presence(activity=discord.Game(new_activity)) 
    # スラッシュコマンドを同期 
    await tree.sync()

#start
@tree.command(name="start",description="サーバーを起動します")
async def start(interaction: discord.Interaction):
    global process
    if process is not None:
        start_logger.error('server is already running')
        await interaction.response.send_message("サーバーはすでに起動しています")
        return
    start_logger.info('server starting')
    await interaction.response.send_message("サーバーを起動します")
    process = subprocess.Popen([server_path + server_name],shell=True,stdin=subprocess.PIPE,stdout=subprocess.PIPE,encoding="utf-8")
    threading.Thread(target=server_logger,args=(process,deque())).start()
    new_activity = f"さーばーじっこう"
    await client.change_presence(activity=discord.Game(new_activity))

#/stop
@tree.command(name="stop",description="サーバーを停止します")
async def stop(interaction: discord.Interaction):
    global process
    if process is None:
        stop_logger.error('server is not running')
        await interaction.response.send_message("サーバーは起動していません")
        return
    stop_logger.info('server stopping')
    await interaction.response.send_message("サーバーを停止します")
    process.stdin.write("stop\n")
    process.stdin.flush()
    new_activity = f"さーばーとじてる"
    await client.change_presence(activity=discord.Game(new_activity)) 

#/command <mc command>
@tree.command(name="cmd",description="サーバーにマインクラフトコマンドを送信します")
async def cmd(interaction: discord.Interaction,command:str):
    global is_back_discord,cmd_logs
    if process is None:
        cmd_logger.error('server is not running')
        await interaction.response.send_message("サーバーは起動していません")
        return
    if command.split()[0] not in allow_cmd:
        cmd_logger.error('unknown command : ' + command)
        await interaction.response.send_message("コマンドが存在しない、または許可されないコマンドです")
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
@tree.command(name="backup",description="ワールドデータをバックアップします")
async def backup(interaction: discord.Interaction,world_name:str = "worlds"):
    global exist_files, copyed_files
    if process is not None:
        backup_logger.error('server is still running')
        await interaction.response.send_message("サーバーが起動しているためバックアップできません")
        return
    backup_logger.info('backup started')
    await interaction.response.send_message("progress...\n")
    # discordにcopyed_files / exist_filesをプログレスバーで
    await dircp_discord(server_path + world_name,server_path + "..\\backup\\" + now_dir + "\\",interaction)
    backup_logger.info('backup done')

#/replace <py file>
@tree.command(name="replace",description="このbotのコードを<py file>に置き換えます\nこのコマンドはbotを破壊する可能性があります")
async def replace(interaction: discord.Interaction,py_file:discord.Attachment):
    if process is not None:
        replace_logger.error('server is still running')
        await interaction.response.send_message("サーバーが起動しているため置き換えできません")
        return
    #実行者に管理者権限がなければreturn
    if not interaction.user.guild_permissions.administrator:
        replace_logger.error('permission denied')
        await interaction.response.send_message("このコマンドを実行するには管理者権限が必要です")
        return
    replace_logger.info('replace started')
    # ファイルをすべて読み込む
    with open(temp_path + "\\new_source.py","w",encoding="utf-8") as f:
        f.write((await py_file.read()).decode("utf-8").replace("\r\n","\n"))
    # discordにコードを置き換える
    replace_logger.info('replace done')
    await interaction.response.send_message("更新プログラムの適応中・・・")
    response = await interaction.original_response()
    #interaction id を保存
    msg_id = str(response.id)
    channel_id = str(interaction.channel_id)
    replace_logger.info("call update.py")
    replace_logger.info('replace args : ' + msg_id + " " + channel_id)
    os.execv(sys.executable,["python3",server_path + "update.py",temp_path + "\\new_source.py",msg_id,channel_id])

#/ip
@tree.command(name="ip",description="サーバーのIPアドレスを表示します")
async def ip(interaction: discord.Interaction):
    # ipをget
    try:
        addr = requests.get("https://api.ipify.org")
    except:
        ip_logger.error('get ip failed')
        await interaction.response.send_message("IPアドレスを取得できません")
        return
    ip_logger.info('get ip : ' + addr.text)
    await interaction.response.send_message("サーバーip : " + addr.text)


#/help
@tree.command(name="help",description="botのコマンド一覧を表示します")
async def help(interaction: discord.Interaction):
    await interaction.response.send_message(send_help)
    help_logger.info('help sent')

#/exit
@tree.command(name="exit",description="botを終了します\nサーバーを停止してから実行してください")
async def exit(interaction: discord.Interaction):
    if process is not None:
        exit_logger.error('server is still running')
        await interaction.response.send_message("サーバーが起動しているため終了できません")
        return
    await interaction.response.send_message("botを終了します...")
    exit_logger.info('exit')
    await client.close()


client.run(token, log_formatter=formatter)

