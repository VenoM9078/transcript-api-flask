import pydub
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
import time
import logging

logging.basicConfig(filename='app.log', level=logging.INFO)

l = logging.getLogger("pydub.converter")
l.setLevel(logging.DEBUG)
l.addHandler(logging.StreamHandler())


# Specify the paths to ffprobe and ffmpeg
ffprobe_path = "/usr/bin/ffprobe"
ffmpeg_path = "/usr/bin/ffmpeg"

# Set the environment variables for pydub
os.environ["PATH"] += os.pathsep + os.path.dirname(ffmpeg_path)
os.environ["PATH"] += os.pathsep + os.path.dirname(ffprobe_path)

# Set the paths for ffprobe and ffmpeg in pydub
AudioSegment.ffmpeg = ffmpeg_path
AudioSegment.ffprobe = ffprobe_path
AudioSegment.converter = "/usr/bin/ffmpeg"

app = Flask(__name__)

# Set up Cloudinary configuration
cloudinary.config(
    cloud_name = 'dldgy1k9c',
    api_key = '373631273284145',
    api_secret = 'PMrfrrHZ_KgkCZ50MszJKFApDOI'
)

@app.route('/process_audio', methods=['POST'])
def process_audio():
    logging.info('Processing audio request')

    if 'url' not in request.json:
        logging.error('No URL provided in request')
        return jsonify({"error": "No URL provided."}), 400

    url = request.json['url']
    logging.info('Received audio URL: %s', url)

    # check if file is an mp3
    if not url.lower().endswith('.mp3'):
        logging.error('URL does not point to an MP3 file')
        return jsonify({"error": "URL must point to an MP3 file."}), 400

    response = requests.get(url, stream=True)

    if response.status_code != 200:
        logging.error('Could not download file, status code: %s', response.status_code)
        return jsonify({"error": "Could not download file."}), 400

    # create a temporary file for the downloaded audio
    temp_audio_path = "temp_audio.mp3"
    with open(temp_audio_path, 'wb') as f:
        f.write(response.content)
    logging.info('Audio downloaded and saved to temp file')

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
        logging.info('Created chunk and saved as MP3')

        # Upload chunk to Cloudinary
        try:
            upload_result = cloudinary.uploader.upload(chunk_file_path, resource_type = "video")
        except Exception as e:
            logging.error('Failed to upload chunk to Cloudinary: %s', str(e))
            return jsonify({"error": "Failed to upload chunk to Cloudinary."}), 500

        # Append the secure URL to chunk_urls
        chunk_urls.append(upload_result['secure_url'])
        logging.info('Chunk uploaded to Cloudinary: %s', upload_result['secure_url'])

    logging.info('Audio processed into chunks and uploaded to Cloudinary.')
    return jsonify({"message": "Audio processed into chunks and uploaded to Cloudinary.", "chunk_urls": chunk_urls}), 200

@app.route('/upload-yt', methods=['POST'])
def upload_yt():
    if 'url' not in request.json:
        return jsonify({"error": "No URL provided."}), 400

    url = request.json['url']

    # Generate a unique identifier for the files
    unique_id = str(uuid.uuid4())

    # Download YouTube video
    try:
        yt = YouTube(url)
        video = yt.streams.filter(progressive=True, file_extension='mp4', res="720p").order_by(
            'resolution').desc().first()
        audio = yt.streams.filter(only_audio=True).first()
    except Exception as e:
        return jsonify({"error": "Could not download YouTube video."}), 400

    # Create youtube directory if it doesn't exist
    if not os.path.exists('youtube'):
        os.makedirs('youtube')

    # Save video and audio to temporary files with the unique identifier
    video.download(output_path="youtube", filename=f"temp_video_{unique_id}")
    audio.download(output_path="youtube", filename=f"temp_audio_{unique_id}")

    os.rename(f"youtube/temp_video_{unique_id}", f"youtube/temp_video_{unique_id}.mp4")
    os.rename(f"youtube/temp_audio_{unique_id}", f"youtube/temp_audio_{unique_id}.mp4")

    video_file = f"youtube/temp_video_{unique_id}.mp4"
    audio_file = f"youtube/temp_audio_{unique_id}.mp4"  # audio is downloaded as .mp4

    # Wait for downloads to finish
    while not os.path.exists(video_file) or not os.path.exists(audio_file):
        time.sleep(1)

    # Convert audio to MP3 using pydub
    audio = AudioSegment.from_file(audio_file)
    audio.export(f"youtube/temp_audio_{unique_id}.mp3", format='mp3')

    # Upload video and audio files to Cloudinary
    try:
        video_cloudinary_result = cloudinary.uploader.upload(video_file, resource_type="video")
        audio_cloudinary_result = cloudinary.uploader.upload(f"youtube/temp_audio_{unique_id}.mp3",
                                                             resource_type="video")
    except Exception as e:
        return jsonify({"error": "Could not upload files to Cloudinary."}), 400

    # Remove temporary files
    os.remove(video_file)
    os.remove(audio_file)
    os.remove(f"youtube/temp_audio_{unique_id}.mp3")

    # Return the secure URLs for the uploaded files
    return jsonify({"audioFile": audio_cloudinary_result['secure_url'], "videoFile": video_cloudinary_result['secure_url']}), 200


if __name__ == '__main__':
    app.run(debug=True, port=5173)