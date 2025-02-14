from flask import Flask, request, jsonify, send_file, render_template
import yt_dlp
import os

app = Flask(__name__)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/get-formats', methods=['POST'])
def get_formats():
    data = request.json
    url = data.get('url')
    
    if not url:
        return jsonify({"error": "URL is required"}), 400
        
    ydl_opts = {
        'quiet': True,
        'no_warnings': True,
    }
    
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            formats = []
            for f in info['formats']:
                # Include all formats for more options
                formats.append({
                    'format_id': f['format_id'],
                    'ext': f.get('ext', 'unknown'),
                    'resolution': f'{f.get("height", "unknown")}p' if f.get("height") else 'audio only' if f.get("acodec") != "none" else 'unknown',
                    'filesize': f.get('filesize', 'unknown'),
                    'vcodec': f.get('vcodec', 'none'),
                    'acodec': f.get('acodec', 'none'),
                    'format_note': f.get('format_note', '')
                })
            return jsonify(formats)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/download', methods=['POST'])
def download_video():
    data = request.json
    url = data.get('url')
    format_id = data.get('format')
    
    if not url:
        return jsonify({"error": "URL is required"}), 400

    try:
        # First, get format information
        with yt_dlp.YoutubeDL({'quiet': True}) as ydl:
            info = ydl.extract_info(url, download=False)
            # Find if format exists
            selected_format = next(
                (f for f in info['formats'] if f['format_id'] == format_id),
                None
            ) if format_id else None

        # Set download options based on format
        ydl_opts = {
            'outtmpl': 'downloads/%(title)s.%(ext)s',
            'merge_output_format': 'mp4',  # Default to MP4 when possible
        }

        if format_id:
            if selected_format:
                # If format has only video or only audio, we need to download both
                if selected_format['vcodec'] == 'none' or selected_format['acodec'] == 'none':
                    ydl_opts['format'] = f'{format_id}+bestaudio/best'
                else:
                    ydl_opts['format'] = format_id
            else:
                return jsonify({"error": f"Format {format_id} not found"}), 400
        else:
            # Default to best quality if no format specified
            ydl_opts['format'] = 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best'

        # Download the video
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info_dict = ydl.extract_info(url, download=True)
            file_path = ydl.prepare_filename(info_dict)
            
            # Ensure the file exists
            if not os.path.exists(file_path):
                # Check for .mp4 version if original doesn't exist
                mp4_path = file_path.rsplit('.', 1)[0] + '.mp4'
                if os.path.exists(mp4_path):
                    file_path = mp4_path
                else:
                    return jsonify({"error": "Download failed: File not found"}), 500

            return send_file(file_path, as_attachment=True)

    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    if not os.path.exists('downloads'):
        os.makedirs('downloads')
    app.run(debug=True)