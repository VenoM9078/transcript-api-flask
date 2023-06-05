from flask import Flask, request, jsonify
import requests
import os
import uuid
from pydub import AudioSegment
import cloudinary
import cloudinary.uploader
import cloudinary.api
from pytube import YouTube
from moviepy.editor import AudioFileClip

app = Flask(__name__)

# Set up Cloudinary configuration
cloudinary.config(
    cloud_name = 'dldgy1k9c',
    api_key = '373631273284145',
    api_secret = 'PMrfrrHZ_KgkCZ50MszJKFApDOI'
)

@app.route('/process_audio', methods=['POST'])
def process_audio():
    if 'url' not in request.json:
        return jsonify({"error": "No URL provided."}), 400

    url = request.json['url']

    # check if file is an mp3
    if not url.lower().endswith('.mp3'):
        return jsonify({"error": "URL must point to an MP3 file."}), 400

    response = requests.get(url, stream=True)

    if response.status_code != 200:
        return jsonify({"error": "Could not download file."}), 400

    # create a temporary file for the downloaded audio
    temp_audio_path = "temp_audio.mp3"
    with open(temp_audio_path, 'wb') as f:
        f.write(response.content)

    # Load your MP3 file
    audio = AudioSegment.from_mp3(temp_audio_path)

    # The duration of each chunk in milliseconds
    chunk_duration_ms = 10 * 60 * 1000  # 10 minutes

    # Create a unique folder name using a UUID
    folder_name = "audio_chunks/" + str(uuid.uuid4())
    os.makedirs(folder_name, exist_ok=True)

    # Array for storing Cloudinary URLs of chunks
    chunk_urls = []

    # Create chunks of 10 minutes
    for i in range(0, len(audio), chunk_duration_ms):
        chunk = audio[i:i + chunk_duration_ms]
        chunk_file_path = f'{folder_name}/chunk_{i // chunk_duration_ms}.mp3'
        chunk.export(chunk_file_path, format="mp3")

        # Upload chunk to Cloudinary
        upload_result = cloudinary.uploader.upload(chunk_file_path, resource_type = "video")

        # Append the secure URL to chunk_urls
        chunk_urls.append(upload_result['secure_url'])

    return jsonify({"message": "Audio processed into chunks and uploaded to Cloudinary.", "chunk_urls": chunk_urls}), 200


from pytube import YouTube
from pydub import AudioSegment

import time

@app.route('/upload-yt', methods=['POST'])
def upload_yt():
    if 'url' not in request.json:
        return jsonify({"error": "No URL provided."}), 400

    url = request.json['url']

    # Download YouTube video
    try:
        yt = YouTube(url)
        video = yt.streams.filter(progressive=True, file_extension='mp4', res="720p").order_by('resolution').desc().first()
        audio = yt.streams.filter(only_audio=True).first()
    except Exception as e:
        return jsonify({"error": "Could not download YouTube video."}), 400

    # Create youtube directory if it doesn't exist
    if not os.path.exists('youtube'):
        os.makedirs('youtube')

    # Save video and audio to temporary files

    video.download(output_path="youtube", filename="temp_video")
    audio.download(output_path="youtube", filename="temp_audio")

    os.rename("youtube/temp_video", "youtube/temp_video.mp4")
    os.rename("youtube/temp_audio", "youtube/temp_audio.mp4")

    video_file = "youtube/temp_video.mp4"
    audio_file = "youtube/temp_audio.mp4"  # audio is downloaded as .mp4

    # Wait for downloads to finish

    while not os.path.exists(video_file) or not os.path.exists(audio_file):
        time.sleep(1)

    # Convert audio to MP3 using pydub
    audio = AudioSegment.from_file(audio_file)
    audio.export("youtube/temp_audio.mp3", format='mp3')

    # Upload video and audio files to Cloudinary
    try:
        video_cloudinary_result = cloudinary.uploader.upload(video_file, resource_type="video")
        audio_cloudinary_result = cloudinary.uploader.upload("youtube/temp_audio.mp3", resource_type="video")
    except Exception as e:
        return jsonify({"error": "Could not upload files to Cloudinary."}), 400

    # Remove temporary files
    os.remove(video_file)
    os.remove(audio_file)
    os.remove("youtube/temp_audio.mp3")

    # Return the secure URLs for the uploaded files
    return jsonify({"audioFile": audio_cloudinary_result['secure_url'], "videoFile": video_cloudinary_result['secure_url']}), 200



if __name__ == '__main__':
    app.run(debug=True, port=7153)