![Windrecorder](https://github.com/yuka-friends/Windrecorder/blob/main/__assets__/product-header-cn.jpg)
<h1 align="center"> 🦝 Windrecorder | 捕風記錄儀</h1>
<p align="center"> Windows 上での <a href="https://www.rewind.ai/">Rewind</a> の代替ツールで、メモリクーを取り戻すのに役立ちます。</p>

<p align="center"> <a href="https://github.com/yuka-friends/Windrecorder/blob/main/__assets__/README-en.md">English</a>  | <a href="https://github.com/yuka-friends/Windrecorder/blob/main/README.md">简体中文</a> | <a href="https://github.com/yuka-friends/Windrecorder/blob/main/__assets__/README-ja.md">日本語</a> </p>

---

画面を継続的に記録し、キーワード検索などでいつでも思い出を呼び出すことができるツールです。

**そのすべての機能 (記録、認識処理、ストレージ トレースバックなど) は完全にローカルで実行され、インターネット接続やデータのアップロードは必要なく、実行すべきことのみを実行します。 **

![Windrecorder](https://github.com/yuka-friends/Windrecorder/blob/main/__assets__/product-preview-cn.jpg)

> [!WARNING]
> 🤯 このプロジェクトはまだ開発の初期段階にあり、経験や使用においていくつかの小さな問題が発生する可能性があります。 この問題に遭遇した場合は、問題のフィードバックを送信し、更新情報をフォローし、ディスカッション フォーラムでディスカッションを開始してください。

> [!IMPORTANT]
> プロジェクトでは機能の追加やアーキテクチャの変更が行われており、以前のバージョンのユーザーが正常にアップグレードおよびアップデートできないなどの問題が発生する可能性があります。
> 心配しないでください。 独自の「videos」、「db」、「config\config_user.json」、その他のディレクトリとファイルを持ち込んでいつでも最新バージョンに移行できます。

## 🦝🎉 0.1.0 新しいトレーラー (近日公開)

![Windrecorder](https://github.com/yuka-friends/Windrecorder/blob/main/__assets__/product-update-0.1.0.jpg)

- このツールをシステム トレイに統合し、すぐに実行できる統合パッケージをリリースする予定であるため、Wind Recorder はこれまでよりも直感的で使いやすくなります。 `start_record.bat` と `start_webui.bat` の複雑な手動インストールに別れを告げましょう。 👋
- タイムマーク機能の追加: 重要な会議、緊急事態、生放送、ゲームや映画鑑賞のハイライトなどにマークを付けて、将来のレビューを容易にしたい場合は、トレイを通して現在の瞬間にマークを付けるか、重要な記録を追加することができます。レビュー時のイベント。
- 圧縮ビデオのフォーマットとパラメータのサポートを追加しました。
- 多数のコード構造をリファクタリングし、いくつかのバグを修正し、パフォーマンスを向上させました。
- その他のアップグレードと変更については、[更新ログ](https://github.com/yuka-friends/Windrecorder/blob/main/CHANGELOG.md)をご確認ください。


以前にウィンドロガーを使用したことがある場合は、ありがとうございます。 次の方法で最新バージョンに更新できます。

- 方法 A: [リリース](https://github.com/yuka-friends/Windrecorder/releases) から統合パッケージをダウンロードして解凍し、次の手順を実行します。
     - ツール ディレクトリに新しい `userdata` フォルダーを作成し、元の `videos`、`db`、`result_lightbox`、`result_timeline`、`result_wordcloud` フォルダーを `userdata` に移動します。
     - 元の `config\config_user.json` ファイルを `userdata` フォルダーに移動します。
     - `windrecorder.exe`を開いて使用します 🎉
- 方法 B: ディレクトリで `git pull` を実行し、`install_update_setting.bat` を開いてアップグレードします。


# 🦝 初めてのインストール

## 自動インストール (ほぼ準備完了)

[リリース](https://github.com/yuka-friends/Windrecorder/releases) から統合パッケージをダウンロードし、データを保存するディレクトリに解凍し、「windrecorder.exe」を開いて使用を開始します。


## 手動インストール

- [ffmpeg](https://www.gyan.dev/ffmpeg/builds/ffmpeg-release-essentials.zip) をダウンロードし、bin ディレクトリ内の ffmpeg.exe、ffprobe.exe を `C:\Windows\System32` (または他のディレクトリ) に解凍します。 PATH にあります)

- [Git](https://git-scm.com/downloads)、[Python](https://www.python.org/ftp/python/3.10.11/python-3.10.11-amd64.exe)をインストール) (インストール中に python.exe を PATH に追加するをチェックします)、[Pip](https://pip.pypa.io/en/stable/installation/);
     - **知らせ！ 現在、Python 3.12** はサポートされていないため、上記のリンクで示されているバージョンである Python 3.10 を使用することをお勧めします。

- このツールをインストールするディレクトリに移動し (十分なスペースのあるパーティションに配置することをお勧めします)、ターミナル コマンド `git clone https://github.com/yuka-friends/ を使用してツールをダウンロードします。ウィンドレコーダー`;

     - インストールするフォルダーを開き、パスバーに「cmd」と入力して Enter キーを押し、現在のディレクトリターミナルに入り、上記のコマンドを貼り付けて Enter キーを押して実行します。

- ディレクトリ内の「install_update.bat」を開いて、ツールをインストールして設定し、問題がなければ使用を開始できます。

     - ネットワーク上の理由によりエラーが報告された場合は、プロキシ `set https_proxy=http://127.0.0.1:xxxx` を追加するか、メインランド [ミラー ソース] (https://mirrors.tuna.tsinghua.edu.cn) を追加できます。 /help/pypi/);


#🦝使い方

現在、ツールを使用するには、ディレクトリ内のバッチ スクリプトを開く必要があります。

- ディレクトリ内の「start_app.bat」を開いて画面の記録を開始します。

> 注: 記録するには、ターミナル ウィンドウを最小化したままにし、バックグラウンドで実行する必要があります。 同様に、録音を一時停止する必要がある場合は、ターミナル ウィンドウを閉じるだけです。

> ベストプラクティス: Webui で自動開始を設定して、手間をかけずにすべてを記録します。 映像に変化がない場合、または画面がスリープモードの場合、録画は自動的に一時停止されます。 コンピュータがアイドル状態で誰も使用していないとき、このツールは自動的にデータベースを維持し、期限切れのビデオを圧縮し、クリーンアップします。設定するだけで、あとは忘れてください。
Genzai, tsūru o shiyō suru ni wa, direkutori-nai no batchi sukuriput

---
### ロードマップ:
- [x] より小さいファイルサイズで画面を安定して継続的に録画します
- [x] 変更された画像のみを識別し、データベースにインデックスを保存します
- [x] 完全なグラフィカル インターフェイス (webui)
- [x] ワードクラウド、タイムライン、ライトボックス、散布図のデータ概要
- [x] 録画後にクリップを自動的に識別し、空いた時間にビデオを自動的にメンテナンス、クリーンアップ、圧縮します。
- [x] 多言語サポート: インターフェイスおよび OCR 認識の i18n サポートが完了しました
- [ ] コードをリファクタリングして、より標準化され、開発が容易になり、パフォーマンスが向上します。
- [-] ツールをパッケージ化し、より便利な使用モードを提供してユーザーフレンドリーにする
- [ ] 画面モダリティの認識を追加して、画面コンテンツの説明の検索を可能にします
- [ ] データベース暗号化機能を追加
- [ ] フォアグラウンドプロセス名を記録し、OCR ワードの対応する位置を記録して、検索時の手がかりとして表示します。
- [ ] 単語埋め込みインデックス、ローカル/API LLM クエリを追加
- [-] マルチスクリーン録画サポートを追加 (pyautogui の将来の機能に応じて)
- [ ] 🤔


# 🦝 Q&A | よくある質問
Q: webui を開いたときに最近のデータがありません。

- A: ツールがデータのインデックスを作成しているとき、webui は最新の一時データベース ファイルを作成しません。
解決策: しばらく待つか、ツールのインデックスが完了するのを待つか、WebUI インターフェイスを更新するか、db ディレクトリ内のサフィックス _TEMP_READ.db を持つデータベース ファイルを削除して更新してみてください (データベース ファイルの破損を求めるプロンプトが表示される場合)心配しないでください。ツールがまだインデックスに残っている可能性があります。しばらくしてから更新/削除してください)。 この戦略は将来的に修正され、リファクタリングされる予定です。 [#26](https://github.com/yuka-friends/Windrecorder/issues/26)

Q: WebUI を開くと、「FileNotFoundError: [WinError 2] 指定されたファイルが見つかりません: './db\\user_2023-10_wind.db-journal'」というプロンプトが表示されます。

- A: 通常、ツールがまだデータのインデックスを作成しているときに、初めて WebUI にアクセスしたときに発生します。
解決策: ツールのバックグラウンド インデックス作成が完了したら、db フォルダー内のサフィックス _TEMP_READ.db を持つ対応するデータベース ファイルを削除し、更新します。

Q: 記録中にマウスが点滅します

- A: Windows の歴史に残っている問題については、[この投稿](https://stackoverflow.com/questions/34023630/how-to-avoid-mouse-pointer-flicker-when-capture-a-window) を試してください。 -by-ffmpeg ) を解決するメソッド🤔。 (本当は慣れて気にならなくても大丈夫です(逃げ)

Q: Windows.Media.Ocr.Cli OCR が利用できない/認識率が低すぎる

- A1: ターゲット言語の言語パック/入力メソッドがシステムに追加されているかどうかを確認します: https://learn.microsoft.com/en-us/uwp/api/windows.media.ocr

- A2: 以前のバージョンのデフォルト ポリシーでは、高さが 1500 を超える画面解像度は「高 DPI/高解像度画面」として扱われ、録画されるビデオ解像度は元の 4 分の 1 に低下します。 たとえば、3840x2160 の 4k モニターでは、録画されるビデオの解像度は 1920x1080 となり、OCR 認識精度の低下につながる可能性があります。 高解像度の画面で小さいフォントやスケーリングを使用する場合は、[録画とビデオの保存] でこのオプションをオフにし、元のビデオをより小さい値に圧縮する前に保存する日数を設定することで、ビデオを圧縮できます。ビデオ OCR インデックスからしばらく後のビデオ ボリューム。

- A3: Windows.Media.Ocr.Cli は、小さなテキストの認識率が低い場合があります。設定で「類似グリフ検索」オプションをオンにすると、検索時の再現ヒット率が向上します。

#🧡
以下のプロジェクトにヘルプが導入されました。

- https://github.com/DayBreak-u/chineseocr_lite

- https://github.com/zh-h/Windows.Media.Ocr.Cli


---

🧡 このツールは気に入りましたか? [YUKA NAGASE](https://www.youtube.com/channel/UCf-PcSHzYAtfcoiBr5C9DZA) の優しい音楽を聴く YouTube とストリーミング音楽プラットフォームへようこそ、ありがとう!

> "Your tools suck, check out my girl Yuka Nagase, she's amazing, I code 10 times faster when listening to her." -- @jpswing