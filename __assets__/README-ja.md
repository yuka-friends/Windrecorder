![Windrecorder](https://github.com/Antonoko/Windrecorder/blob/main/__assets__/product-header-en.jpg)
<h1 align="center"> 🦝 Windrecorder</h1>
<p align="center">Windowsでのメモリーの手がかりを取得するためのオープンソースのRewindの代替ツールです。</p>

<p align="center"> <a href="https://github.com/Antonoko/Windrecorder/blob/main/__assets__/README-en.md">English</a>  | <a href="https://github.com/Antonoko/Windrecorder/blob/main/README.md">简体中文</a> | 日本語 </p>

---
> Rewindアプリとは？: https://www.rewind.ai/

**⚠️ツールに含まれているWindows.Media.Ocr.Cliは現在、中国語のみにコンパイルされており、純粋な日本語システムではOCR認識が利用できなくなります。このブロッキングの問題は、修正のためのアップデートを待っています。**

これは、画面を継続的に記録し、キーワード検索などの方法で関連するメモリーをすぐに取得できるツールです。

**すべての機能（録画、認識処理、バックトラックの保存など）は完全にローカルで実行され、インターネットに接続する必要はありません。データはアップロードされません。ツールは必要なことだけを行います。**

![Windrecorder](https://github.com/Antonoko/Windrecorder/blob/main/__assets__/product-preview-cn.jpg)


# 🦝 インストール

- [ffmpeg](https://www.gyan.dev/ffmpeg/builds/ffmpeg-release-essentials.zip)をダウンロードし、binディレクトリ内のffmpeg.exeを`C:\Windows\System32`（または他のPATHでアクセス可能なディレクトリ）に解凍します。

- [Git](https://git-scm.com/downloads)、[Python](https://www.python.org/ftp/python/3.11.6/python-3.11.6-amd64.exe)（インストール時にAdd python.exe to PATHを選択）、[Pip](https://pip.pypa.io/en/stable/installation/)がインストールされていることを確認します。

- インストールするディレクトリに移動し、ターミナルコマンド`git clone https://github.com/Antonoko/Windrecorder`を使用してツールをダウンロードします。

    - インストールしたいフォルダを開き、パスバーに`cmd`と入力しEnterキーを押して、現在のディレクトリのターミナルに上記のコマンドを貼り付け、Enterキーを押します。

- ディレクトリ内の`install_update_setting.bat`を開いて、ツールのインストールと設定を行います。うまくいけば、使用を開始できます！


- ディレクトリ内の`start_record.bat`を実行して画面を記録し、`start_webui.bat`を使用してトラックバック、クエリ、および設定を行います。

---
### ロードマップ：
- [x] 小さなファイルサイズで画面を安定して記録する
- [x] 変更された画像のみを識別し、データベースにインデックスを保存する
- [x] リッチなグラフィカルユーザーインターフェース（WebUI）
- [x] キーワードクラウド、タイムライン、ライトボックス、散布図のデータの視覚化
- [ ] メモリーの手がかりを取得するための検索機能の改善
- [ ] 他のオペレーティングシステム（macOS、Linux）のサポート
- [ ] インターフェースの改善とユーザビリティの向上
- [ ] ドキュメンテーションとチュートリアルの追加
- [ ] プロジェクトの安定性とパフォーマンスの向上


# 🧡
Help from these projects has been enlisted:

- [https://github.com/DayBreak-u/chineseocr_lite](https://github.com/DayBreak-u/chineseocr_lite)

- [https://github.com/zh-h/Windows.Media.Ocr.Cli](https://github.com/zh-h/Windows.Media.Ocr.Cli)


---

Like this tool? Feel free to enjoy the soothing music of [YUKA NAGASE](https://www.youtube.com/channel/UCf-PcSHzYAtfcoiBr5C9DZA) on YouTube and streaming music platforms. Thank you!

> "Your tools suck, check out my girl Yuka Nagase, she's amazing, I code 10 times faster when listening to her." -- @jpswing