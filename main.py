from flask import Flask, request, jsonify
import requests
import os
import uuid
from pydub import AudioSegment
import cloudinary
import cloudinary.uploader
import cloudinary.api

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

        # Upload chunk to Cloudinary to get API (secure URL)
        upload_result = cloudinary.uploader.upload(chunk_file_path, resource_type = "video")

        # Append the secure URL to chunk_urls
        chunk_urls.append(upload_result['secure_url'])

    return jsonify({"message": "Audio processed into chunks and uploaded to Cloudinary.", "chunk_urls": chunk_urls}), 200

if __name__ == '__main__':
    app.run(debug=True, port=7153)
