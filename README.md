# ShazamAPI
### Shazam-based Music Recognition API

このプロジェクトは、[ShazamIO](https://github.com/devscanline/shazamio) を用いて音楽の認識や楽曲情報の取得を行う FastAPI アプリケーションです。  
`FFmpeg` を使用し、未対応フォーマットのファイルでも OGG へ変換した上で音楽認識を試みます。

## 主な機能

- **音楽認識**: `/music/recognize` に音声ファイルを POST することで、該当曲の情報を取得  
- **アーティスト情報の取得**: アーティスト情報や楽曲トップリストの取得  
- **トラック情報の取得**: トラック固有情報や関連トラックの取得  
- **検索機能**: アーティスト・トラック名での検索  
- **チャート情報**: 世界・国別ランキングやジャンル別ランキングの取得

## 必要環境

- Python 3.8 以上
- FFmpeg (音声ファイルの変換で使用)
- 主要ライブラリ
  - fastapi
  - uvicorn
  - shazamio

## インストール手順

1. リポジトリをクローン、またはソースコードをダウンロード
2. 仮想環境を作成（推奨）
3. 必要ライブラリをインストール
   ```bash
   pip install fastapi uvicorn shazamio
   ```
4. システムに FFmpeg がインストールされていることを確認

## 実行方法

```bash
uvicorn main:app --host 0.0.0.0 --port 8000
```

## 使用例

音声ファイルを POST して楽曲を認識したい場合は、`/music/recognize` エンドポイントに以下のようにリクエストします:

```bash
curl -X POST "http://localhost:8000/music/recognize" \
     -F "file=@/path/to/music_file.mp3"
```

## デモ環境

デモ用として、以下にデプロイ済みの環境を用意しています:
- **https://shazamapi.sprink.cloud/docs**  

各種エンドポイントに対して同様にリクエストを送ることで、機能をお試しできます。

## 主なエンドポイント

### 音楽認識
- `POST /music/recognize`
  - `file` パラメータに音声ファイルを送信すると、認識結果を返す

### アーティスト
- `GET /music/artist/about/{artist_id}`
  - アーティストの詳細情報を取得
- `GET /music/artist/top_songs/{artist_id}`
  - アーティストのトップソングリストを取得

### トラック
- `GET /music/track/about/{track_id}`
  - トラックの詳細情報を取得
- `GET /music/track/listening_count/{track_id}`
  - トラックの再生回数（Shazam 上のリスナー数）を取得
- `GET /music/track/related/{track_id}`
  - 関連トラックを取得

### 検索
- `GET /music/search/artist`
  - アーティスト名をキーワードに検索
- `GET /music/search/track`
  - 楽曲名をキーワードに検索

### チャート
- `GET /music/charts/city`
  - 指定都市のトップトラックを取得
- `GET /music/charts/country`
  - 指定国のトップトラックを取得
- `GET /music/charts/country/genre`
  - 指定国 & ジャンルのトップトラックを取得
- `GET /music/charts/world/genre`
  - 世界 & ジャンルのトップトラックを取得
- `GET /music/charts/world`
  - 世界のトップトラックを取得

## 備考

- 変換前にファイル形式が ShazamIO に対応していない場合、OGG に変換して再試行します  
- ShazamIO は内部的に FFmpeg を利用するため、コード内の `convert_to_supported_format` 関数による変換を経由しなくても動作する場合がありますが、ここでは念のため外部での変換を行っています  
- API ドキュメントは `http://localhost:8000/docs` から確認できます
