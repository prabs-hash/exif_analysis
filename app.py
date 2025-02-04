from flask import Flask, render_template, request, send_file
import os
import datetime
from werkzeug.utils import secure_filename
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from PIL import Image
import piexif
from moviepy.video.io.VideoFileClip import VideoFileClip

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = 'uploads'

# Ensure the upload folder exists
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

def get_file_metadata(file_path):
    """Extract metadata from a file."""
    metadata = {
        'File Name': os.path.basename(file_path),
        'File Path': file_path,
        'File Size (bytes)': os.path.getsize(file_path),
        'Creation Time': datetime.datetime.fromtimestamp(os.path.getctime(file_path)).isoformat(),
        'Modification Time': datetime.datetime.fromtimestamp(os.path.getmtime(file_path)).isoformat(),
        'File Type': os.path.splitext(file_path)[1]
    }

    # Extract EXIF data if the file is an image
    if metadata['File Type'].lower() in ['.jpg', '.jpeg', '.png', '.tiff']:
        try:
            image = Image.open(file_path)
            exif_data = image._getexif()
            if exif_data:
                for tag_id, value in exif_data.items():
                    tag = piexif.TAGS['Exif'].get(tag_id, tag_id)
                    metadata[f'EXIF {tag}'] = value
        except Exception as e:
            metadata['EXIF Error'] = str(e)

    # Extract video metadata if the file is a video
    if metadata['File Type'].lower() in ['.mp4', '.avi', '.mkv', '.mov']:
        try:
            video = VideoFileClip(file_path)
            metadata['Video Resolution'] = f"{video.size[0]}x{video.size[1]}"
            metadata['Duration'] = str(datetime.timedelta(seconds=int(video.duration)))
            video.close()
        except Exception as e:
            metadata['Video Resolution'] = 'Error'
            metadata['Duration'] = 'Error'

    return metadata

def extract_metadata_from_directory(directory):
    """Extract metadata from all files in a directory."""
    metadata_list = []
    for root, dirs, files in os.walk(directory):
        for file in files:
            file_path = os.path.join(root, file)
            metadata = get_file_metadata(file_path)
            if metadata:
                metadata_list.append(metadata)
    return metadata_list

def save_metadata_to_pdf(metadata_list, output_file):
    """Save the extracted metadata to a PDF file."""
    c = canvas.Canvas(output_file, pagesize=letter)
    width, height = letter
    c.setFont("Helvetica", 10)

    y_position = height - 40  # Start from the top of the page
    c.drawString(30, y_position, "File Metadata Extraction")
    y_position -= 20

    for metadata in metadata_list:
        for key, value in metadata.items():
            c.drawString(30, y_position, f"{key}: {value}")
            y_position -= 15
            if y_position < 40:  # Check if we need to create a new page
                c.showPage()
                c.setFont("Helvetica", 10)
                y_position = height - 40

        y_position -= 10  # Add some space between different files

    c.save()

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/upload', methods=['GET', 'POST'])
def upload_directory():
    if request.method == 'POST':
        uploaded_files = request.files.getlist('files[]')
        output_name = request.form['output_name']
        output_pdf = os.path.join(app.config['UPLOAD_FOLDER'], f"{secure_filename(output_name)}.pdf")
        
        # Save uploaded files
        uploaded_dir = os.path.join(app.config['UPLOAD_FOLDER'], 'uploaded_files')
        os.makedirs(uploaded_dir, exist_ok=True)

        # Iterate over files and save them
        for file in uploaded_files:
            file_path = os.path.join(uploaded_dir, secure_filename(file.filename))

            # Ensure directory for the file path exists
            file_dir = os.path.dirname(file_path)
            os.makedirs(file_dir, exist_ok=True)

            file.save(file_path)

        # Extract metadata and save to PDF
        metadata_list = extract_metadata_from_directory(uploaded_dir)
        save_metadata_to_pdf(metadata_list, output_pdf)

        # Serve the PDF
        return send_file(output_pdf, as_attachment=True)

    return render_template('upload.html')

if __name__ == '__main__':
    app.run(debug=True)
