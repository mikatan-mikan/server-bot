# server-bot

## 最初に

以前のバージョンを利用中で新たなバージョンに更新する方は最下部に存在する"更新履歴"の"最後の破壊的変更"を確認してください。また、更新時には/replaceを用いて最新のserver.pyファイルに置き換えてください。

確認や/replaceでの更新が面倒な場合はこれまでの.configや.token、update.pyを削除してから新たなバージョンを起動してください。

## 対応言語

This bot supports English and Japanese.(このbotは英語と日本語をサポートしています。)

For the Readme, writing an English version is currently under consideration.(Readmeについては英語版を記述することを現在検討中です。)

## 目的

このbotはサーバーを管理するためのdiscord botです。

discordを用いて特定のサーバーを管理できます。

ここでの管理とは起動/停止/ログ取得/入出力などを行うことを指します。

## コマンド一覧

プログラムに含まれるコマンドは以下の通りです。

|コマンド|実行結果|必要権限|
|----|----|----|
|help|discord上にhelpを表示します。 |-|
|ip|このbot(サーバー)を実行しているipアドレスを返します。|-(configにより有効にする必要あり)|
|start|サーバーを開始します。但し、server.py起動時には自動的に開始されます。|bot管理者/discord管理者|
|stop|サーバーを停止します。但しserver.pyは実行状態から遷移しないため他のコマンドを使用できます。|bot管理者/discord管理者|
|exit|server.pyを終了します(このコマンドを利用すると次回サーバー管理者がserver.pyを起動するまでbotを利用できません)。サーバー停止中にのみ使用できます。|bot管理者/discord管理者|
|backup|サーバーデータをバックアップします。引数が与えられない場合`./worlds`をバックアップします。|bot管理者/discord管理者|
|cmd|サーバーに対してコマンドを送信します。|bot管理者/discord管理者|
|replace|server.pyを与えられた引数に置換します。|discord管理者|
|logs|サーバーログを表示します。引数が与えられる場合には該当のファイルを、与えられない場合には現在のサーバーログを10件表示します。|bot管理者/discord管理者|
|lang|サーバーの言語を変更します。|bot管理者/discord管理者|
|admin|サーバー内の管理者権限を操作します。admin forceを用いてbot管理者を設定できます。|discord管理者|
|permission|プレイヤーの権限を表示します。|-|

これらコマンドの設定等は後述の使用方法を参照してください。

## 動作確認

|確認バージョン|日時|確認時のOS|
|----|----|----|
|Java vanilla 1.9.4|2024/06/26|Windows 11|
|Java vanilla 1.19|2024/06/26|Windows 11|
|Java vanilla 1.19.4|2024/07/31|Windows 11|
|Java fabric 1.20.1|2024/06/26|Windows 11|
|Bedrock dedicated server 1.21|2024/07/30|Windows 11 & Ubuntu(wsl2)|

java版serverをWindowsで起動する際一般に利用されるような以下の内容のbatをconfigのserver_nameに設定しています。noguiオプションが無い場合現在/stop等が利用できません。(fabric : start.bat , forge : run.bat)

> [!WARNING]
> -Dfile.encoding=UTF-8が存在しない場合一部環境で特殊文字等が正常に表示されません。またpauseのようなコマンドを記載しないでください。(このプログラムはサーバーを制御するプログラムです。それ以外のコマンドを実行しないでください。)

`java -Xmx4048M -Xms1024M -Dfile.encoding=UTF-8 -jar server.jar nogui`

### 確認済み環境

windows 11 version 23H2  / python3.12.2&3.10.2

ubuntu(wsl2) / python3.8.10 (古いバージョンのPythonを利用する場合は、configの初期設定が相対パスになります。絶対パスに直してから実行してください)

## 必要なもの

現在使用していないdiscord bot

ライブラリ：requirements.txtを参照

## 使用方法

(読みたくない方へ：ドライブ直下でない場所にserver.pyを配置して実行して進めれば何とかなるかも・・・？)

server.pyを任意の場所に配置します。(推奨ディレクトリは実行するserver.[exe/jar]が存在する階層です。)

ただしserver.exeやserver.jar本体が存在する階層はrootでない必要があります。(何かのディレクトリの中に入れてください)これは初期状態では、`../backup/`内にbackupが生成されるためです。

後にserver.pyを起動するとserver.pyと同じ階層に`.token`と`.config`が生成されます。

.tokenにbotのtokenを記述してください。

.configについては後述します。

このとき同時に`update.py`が生成されますが、これは`/repalce`を実行するために必要なファイルです。

tokenを記述し、configのserver_pathにserver.[exe/bat(jarを実行するファイル)]へのパスを記述後に再度server.pyを起動すると正常に起動するはずです。このプログラムはserver.pyがサーバー本体を呼び出すためserver.[exe/jar/bat]を自身で起動する必要はありません。

> [!WARNING]
> server.jar(java edition)を起動する場合基本的には`java -Xmx4048M -Xms1024M -Dfile.encoding=UTF-8 -jar server.jar nogui`と記述されたbatファイル(Windowsの場合)を作成しserver_pathに記載してください。

### .config

./configは初期生成では以下のような内容で構成されています。

```json
{
    "allow": {
        "ip": true
    },
    "server_path": str(path of server.py),
    "allow_mccmd": [
        "list",
        "whitelist",
        "tellraw",
        "w",
        "tell"
    ],
    "server_name": "bedrock_server.exe",
    "log": {
        "server": true,
        "all": false
    },
    "backup_path": str(path of backup),
    "mc": true,
    "lang": "en"
}
```

|項目|説明|
|---|---|
|allow|各コマンドの実行を許可するかどうか。(現在は/ipにのみ実装されています)|
|server_path|minecraft server本体のパス(例えば`D:\\a\\server.jar`に配置されていれば`D:\\a\\`または`D:/a/`)|
|allow_mccmd|/cmdで標準入力を許可するコマンド名のリスト|
|server_name|minecraft server本体の名前 java版の場合サーバ起動に利用される`server.bat`等を入力してください(GUI起動させないでください)|
|log|各種ログを保存するか否か serverをtrueにするとmcサーバーの実行ログをmcserverと同じディレクトリに保存し、allをtrueにするとすべてのログをserver.pyと同じディレクトリに保存します|
|backup_path|ワールドデータのバックアップパス(例えば`D:\\server\\backup`に保存したければ`D:\\server\\backup\\`または`D:/server/backup/`)|
|mc|サーバーがmcサーバーかどうかを記述します。現在trueに設定されている場合、/ip時にserver.propertiesからserver-portを読み出します|
|lang|discordに送信するメッセージの言語を選択します。(en : 英語, ja : 日本語)|

server.pyはサーバ本体と同じ改装に配置することを推奨します。

### 動作状態

以下の動画はダウンロード後のserver.pyを起動し、コマンドを実行する動画です。

![server.mp4](https://github.com/mikatan-mikan/server-bot/assets/78290592/32df51eb-7166-40a8-b817-e1057d2aabd0)

## 注意

生成されるupdate.pyの名前は変更しないでください。`/replace`が動作しなくなるはずです。

### /cmd

このコマンドで利用できるコマンドは`allow_cmd`により定義されています。他に使いたいコマンドが存在する場合はlistを追加してください。

コマンド使用例としてwhitelistへの追加は/cmd `command:whitelist add <mcid>`のようにして実行できます。

## 免責事項

本プログラムのインストール/実行/その他本プログラムが影響する挙動全てにおいて、生じた損害や不具合には作者は一切の責任を負わないものとします。

## 更新履歴

https://github.com/mikatan-mikan/server-bot/blob/main/PATCH.md

### 最後の破壊的変更

破壊的変更とは既存のupdate.py等を変更する必要がある変更を指します。

2024/06/10 更新前にupdate.pyの削除が必要です。6/10以前のserver.pyを利用している場合はupdate.pyを削除してください。

今後の更新ではupdate.pyを自動更新するように変更しています。
