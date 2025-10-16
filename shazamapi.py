#!/usr/bin/env python3.10
import uvicorn
import asyncio
import os
import traceback
import uuid
import subprocess
import json
from typing import Optional
from fastapi import FastAPI, HTTPException, UploadFile, File, APIRouter
from shazamio import Shazam, Serialize, GenreMusic
from shazamio.schemas.artists import ArtistView, ArtistQuery

def error_response(e: Exception):
    return {
        "error": str(e)
        #"traceback": traceback.format_exc()
    }

def convert_to_supported_format(input_path: str, output_path: str) -> bool:
    # ffmpegでの変換処理を実行
    # 成功すればTrue, 失敗すればFalse
    try:
        # ffmpegでのコマンド呼び出し
        # 強制的にOGGに変換する例
        cmd = ["ffmpeg", "-y", "-i", input_path, "-vn", "-acodec", "libvorbis", output_path]
        subprocess.run(cmd, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        return True
    except Exception:
        return False

app = FastAPI()

@app.on_event("startup")
async def startup_event():
    app.state.shazam = Shazam()

# === Recognition Router ===
recognition_router = APIRouter(prefix="/music/recognize", tags=["Recognition"])

@recognition_router.post("/")
async def recognize_track(file: UploadFile = File(...)):
    # 一時ファイルを作成
    temp_input = f"/tmp/{uuid.uuid4()}_{file.filename}"
    with open(temp_input, "wb") as f:
        f.write(await file.read())

    # Shazamが対応するフォーマットかを簡易的にチェックするために、まずはそのまま試す
    # エラーが出た場合はフォーマット変換を試みる
    # ShazamIOは内部でffmpegを用いているが、念のため外部で変換
    try:
        result = await app.state.shazam.recognize(temp_input)
        # 認識成功すればファイル削除
        os.remove(temp_input)
        return result
    except Exception:
        # 変換を試みる
        # 変換先ファイル名
        temp_output = f"/tmp/{uuid.uuid4()}.ogg"
        success = convert_to_supported_format(temp_input, temp_output)
        if not success:
            # 変換できなければエラーを返す
            os.remove(temp_input)
            raise HTTPException(status_code=400, detail="対応していないファイル形式です。変換不可のため認識できません。")
        # 元ファイル削除
        os.remove(temp_input)

        # 変換後ファイルで再度認識を試行
        try:
            result = await app.state.shazam.recognize(temp_output)
            os.remove(temp_output)
            return result
        except Exception:
            os.remove(temp_output)
            raise HTTPException(status_code=400, detail="対応していないファイル形式か、認識できません。")

# === Artist Router ===
artist_router = APIRouter(prefix="/music/artist", tags=["Artist"])

@artist_router.get("/about/{artist_id}")
async def about_artist(artist_id: int):
    try:
        about = await app.state.shazam.artist_about(artist_id)
        #serialized = Serialize.artist(about)
        return {
            "raw": about,
            "serialized": about
        }
    except Exception as e:
        return error_response(e)

@artist_router.get("/top_songs/{artist_id}")
async def top_artist_tracks(artist_id: int):
    try:
        about_artist = await app.state.shazam.artist_about(
            artist_id,
            query=ArtistQuery(
                views=[ArtistView.TOP_SONGS],
            ),
        )
        serialized = Serialize.artist_v2(about_artist)
        result = []
        if serialized.data and serialized.data[0].views and serialized.data[0].views.top_songs and serialized.data[0].views.top_songs.data:
            for i in serialized.data[0].views.top_songs.data:
                result.append(i.attributes.name)
        return {"top_songs": result}
    except Exception as e:
        return error_response(e)

# === Track Router ===
track_router = APIRouter(prefix="/music/track", tags=["Track"])

@track_router.get("/about/{track_id}")
async def about_track(track_id: int):
    try:
        track_info = await app.state.shazam.track_about(track_id=track_id)
        serialized = Serialize.track(data=track_info)
        return {
            "raw": track_info,
            "serialized": serialized
        }
    except Exception as e:
        return error_response(e)

@track_router.get("/listening_count/{track_id}")
async def track_listening_count(track_id: int):
    try:
        count = await app.state.shazam.listening_counter(track_id=track_id)
        return {"count": count}
    except Exception as e:
        return error_response(e)

@track_router.get("/related/{track_id}")
async def related_tracks(track_id: int, limit: int = 5, offset: int = 0):
    try:
        related = await app.state.shazam.related_tracks(track_id=track_id, limit=limit, offset=offset)
        return related
    except Exception as e:
        return error_response(e)

# === Search Router ===
search_router = APIRouter(prefix="/music/search", tags=["Search"])

@search_router.get("/artist")
async def search_artists(query: str, limit: int = 5):
    try:
        artists = await app.state.shazam.search_artist(query=query, limit=limit)
        results = []
        for artist in artists.get('artists', {}).get('hits', []):
            serialized = Serialize.artist(data=artist)
            results.append(serialized)
        return results
    except Exception as e:
        return error_response(e)

@search_router.get("/track")
async def search_tracks(query: str, limit: int = 5):
    try:
        tracks = await app.state.shazam.search_track(query=query, limit=limit)
        return tracks
    except Exception as e:
        return error_response(e)

# === Charts Router ===
charts_router = APIRouter(prefix="/music/charts", tags=["Charts"])

@charts_router.get("/city")
async def top_city_tracks(country_code: str, city_name: str, limit: int = 10):
    try:
        top_tracks = await app.state.shazam.top_city_tracks(country_code=country_code, city_name=city_name, limit=limit)
        serialized_list = []
        for track in top_tracks.get('tracks', []):
            serialized_list.append(Serialize.track(data=track))
        return {
            "raw": top_tracks,
            "serialized": serialized_list
        }
    except Exception as e:
        return error_response(e)

@charts_router.get("/country")
async def top_country_tracks(country_code: str, limit: int = 5):
    try:
        top_tracks = await app.state.shazam.top_country_tracks(country_code, limit)
        serialized_list = []
        for track in top_tracks.get('tracks', []):
            serialized_list.append(Serialize.track(data=track))
        return serialized_list
    except Exception as e:
        return error_response(e)

@charts_router.get("/country/genre")
async def top_country_genre_tracks(country_code: str, genre: str, limit: int = 5):
    try:
        genre_enum = None
        for g in GenreMusic:
            if g.value.lower() == genre.lower().replace('_','-'):
                genre_enum = g
                break
        if genre_enum is None:
            raise HTTPException(status_code=400, detail="無効なジャンル指定")
        
        top_tracks = await app.state.shazam.top_country_genre_tracks(country_code=country_code, genre=genre_enum, limit=limit)
        return top_tracks
    except Exception as e:
        return error_response(e)

@charts_router.get("/world/genre")
async def top_world_genre_tracks(genre: str, limit: int = 10):
    try:
        genre_enum = None
        for g in GenreMusic:
            if g.value.lower() == genre.lower().replace('_','-'):
                genre_enum = g
                break
        if genre_enum is None:
            raise HTTPException(status_code=400, detail="無効なジャンル指定")

        top_world_genre = await app.state.shazam.top_world_genre_tracks(genre=genre_enum, limit=limit)
        results = []
        for track in top_world_genre.get('tracks', []):
            serialized_track = Serialize.track(data=track)
            results.append({
                "track": serialized_track,
                "spotify_url": getattr(serialized_track, 'spotify_url', None)
            })
        return results
    except Exception as e:
        return error_response(e)

@charts_router.get("/world")
async def top_world_tracks(limit: int = 10):
    try:
        top_world = await app.state.shazam.top_world_tracks(limit=limit)
        serialized_list = []
        for track in top_world.get('tracks', []):
            serialized_list.append(Serialize.track(track))
        return {
            "raw": top_world,
            "serialized": serialized_list
        }
    except Exception as e:
        return error_response(e)

app.include_router(recognition_router)
app.include_router(artist_router)
app.include_router(track_router)
app.include_router(search_router)
app.include_router(charts_router)

app = app  # Necessário para o Vercel reconhecer a app

