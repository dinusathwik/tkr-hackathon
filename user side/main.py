
from flask import Flask, request, jsonify, render_template, send_from_directory
import requests
import os
import json
from werkzeug.utils import secure_filename
import uuid

app = Flask(__name__)
UPLOAD_FOLDER = 'temp_uploads'
ALLOWED_EXTENSIONS = {'pdf', 'docx', 'xlsx', 'pptx', 'jpg', 'jpeg', 'png'}
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size

os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs('templates', exist_ok=True)

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'GET':
        return render_template('index.html')

    if request.method == 'POST':
        if 'file' not in request.files:
            return jsonify({'error': 'No file uploaded'}), 400

        file = request.files['file']
        if file.filename == '':
            return jsonify({'error': 'No file selected'}), 400

        if not allowed_file(file.filename):
            return jsonify({'error': 'File type not supported'}), 400

        try:
            # Get print options from form
            copies = request.form.get('copies', '1')
            paper_size = request.form.get('paperSize', 'A4')
            orientation = request.form.get('orientation', 'auto')
            print_type = request.form.get('printType', 'bw')
            shop_id = request.form.get('shopId')
            server_url = request.form.get('serverUrl')
            
            if not shop_id or not server_url:
                return jsonify({'error': 'Shop ID and Server URL are required'}), 400

            # Save file temporarily
            filename = secure_filename(file.filename)
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(filepath)

            # Prepare data for Xerox API server
            color = print_type == 'color'
            
            # Create a multipart form data
            with open(filepath, 'rb') as f:
                files = {'file': (filename, f)}
                data = {
                    'shop_id': shop_id,
                    'copies': copies,
                    'color': str(color).lower(),
                    'paper_size': paper_size
                }
                
                # Send to the Xerox server
                submit_url = f"{server_url}/api/submit-print-job"
                response = requests.post(submit_url, files=files, data=data)

            # Clean up temp file
            os.remove(filepath)

            if response.status_code == 200:
                result = response.json()
                return jsonify({
                    'message': 'Print job submitted successfully',
                    'jobId': result.get('job_id', 'Unknown'),
                    'status': 'success'
                })
            else:
                return jsonify({
                    'error': f'Print service error: {response.text}',
                    'status': 'error'
                }), 500

        except Exception as e:
            return jsonify({
                'error': f'Server error: {str(e)}',
                'status': 'error'
            }), 500

@app.route('/scan', methods=['GET'])
def scan_page():
    return render_template('scan.html')

# Add route to serve the HTML template
@app.route('/templates/<path:path>')
def send_template(path):
    return send_from_directory('templates', path)

# Create templates if they don't exist
if not os.path.exists('templates/index.html'):
    with open('templates/index.html', 'w') as f:
        f.write('''
<!DOCTYPE html>
<html>
<head>
    <title>Xerox Print Service</title>
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <style>
        body { font-family: Arial, sans-serif; margin: 0; padding: 20px; line-height: 1.6; }
        .container { max-width: 800px; margin: 0 auto; }
        h1 { color: #2c3e50; }
        .btn { display: inline-block; padding: 10px 20px; background-color: #3498db; 
               color: white; text-decoration: none; border-radius: 4px; border: none; cursor: pointer; }
        .btn:hover { background-color: #2980b9; }
    </style>
</head>
<body>
    <div class="container">
        <h1>Welcome to Mobile Print Service</h1>
        <p>Scan a Xerox shop QR code to print your documents.</p>
        <a href="/scan" class="btn">Scan QR Code</a>
    </div>
</body>
</html>
        ''')

if not os.path.exists('templates/scan.html'):
    with open('templates/scan.html', 'w') as f:
        f.write('''
<!DOCTYPE html>
<html>
<head>
    <title>Scan QR Code - Xerox Print</title>
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <script src="https://cdn.jsdelivr.net/npm/jsqr@1.4.0/dist/jsQR.min.js"></script>
    <style>
        body { font-family: Arial, sans-serif; margin: 0; padding: 20px; line-height: 1.6; }
        .container { max-width: 800px; margin: 0 auto; }
        h1 { color: #2c3e50; }
        .btn { display: inline-block; padding: 10px 20px; background-color: #3498db; 
               color: white; text-decoration: none; border-radius: 4px; border: none; cursor: pointer; }
        .btn:hover { background-color: #2980b9; }
        #scanner { width: 100%; max-width: 500px; margin: 0 auto; }
        #video { width: 100%; border: 1px solid #ddd; }
        #upload-form { display: none; margin-top: 20px; }
        input, select { padding: 8px; margin-bottom: 10px; width: 100%; }
        label { display: block; margin-top: 10px; }
        #success, #error { display: none; padding: 10px; margin-top: 20px; border-radius: 4px; }
        #success { background-color: #dff0d8; color: #3c763d; border: 1px solid #d6e9c6; }
        #error { background-color: #f2dede; color: #a94442; border: 1px solid #ebccd1; }
    </style>
</head>
<body>
    <div class="container">
        <h1>Scan QR Code</h1>
        
        <div id="scanner">
            <video id="video" autoplay></video>
            <button id="start-scan" class="btn">Start Scanner</button>
            <p id="scanning-status">Press the button to start scanning</p>
        </div>
        
        <div id="upload-form">
            <h2>Upload Document</h2>
            <p id="shop-info"></p>
            
            <form id="print-form">
                <input type="hidden" id="shop-id" name="shopId">
                <input type="hidden" id="server-url" name="serverUrl">
                
                <label for="file">Select Document:</label>
                <input type="file" id="file" name="file" required>
                
                <label for="copies">Copies:</label>
                <input type="number" id="copies" name="copies" min="1" value="1">
                
                <label for="paperSize">Paper Size:</label>
                <select id="paperSize" name="paperSize">
                    <option value="A4">A4</option>
                    <option value="Letter">Letter</option>
                    <option value="Legal">Legal</option>
                </select>
                
                <label for="printType">Print Type:</label>
                <select id="printType" name="printType">
                    <option value="bw">Black & White</option>
                    <option value="color">Color</option>
                </select>
                
                <button type="submit" class="btn" style="margin-top: 20px;">Submit Print Job</button>
            </form>
        </div>
        
        <div id="success"></div>
        <div id="error"></div>
        
        <p><a href="/" class="btn" style="margin-top: 20px;">Back to Home</a></p>
    </div>
    
    <script>
        document.addEventListener('DOMContentLoaded', function() {
            const startButton = document.getElementById('start-scan');
            const video = document.getElementById('video');
            const scanningStatus = document.getElementById('scanning-status');
            const uploadForm = document.getElementById('upload-form');
            const shopInfo = document.getElementById('shop-info');
            const shopIdInput = document.getElementById('shop-id');
            const serverUrlInput = document.getElementById('server-url');
            const printForm = document.getElementById('print-form');
            const successDiv = document.getElementById('success');
            const errorDiv = document.getElementById('error');
            
            let scanner = null;
            
            startButton.addEventListener('click', function() {
                startScanner();
            });
            
            function startScanner() {
                // Access the device camera
                navigator.mediaDevices.getUserMedia({ video: { facingMode: "environment" } })
                    .then(function(stream) {
                        video.srcObject = stream;
                        scanner = setInterval(scanQRCode, 500);
                        startButton.style.display = 'none';
                        scanningStatus.textContent = 'Scanning for QR code...';
                    })
                    .catch(function(error) {
                        scanningStatus.textContent = 'Could not access camera: ' + error.message;
                    });
            }
            
            function scanQRCode() {
                if (video.readyState === video.HAVE_ENOUGH_DATA) {
                    // Create a temporary canvas to capture the video frame
                    const canvas = document.createElement('canvas');
                    canvas.width = video.videoWidth;
                    canvas.height = video.videoHeight;
                    const ctx = canvas.getContext('2d');
                    ctx.drawImage(video, 0, 0, canvas.width, canvas.height);
                    
                    // Get image data for QR code scanning
                    const imageData = ctx.getImageData(0, 0, canvas.width, canvas.height);
                    const code = jsQR(imageData.data, imageData.width, imageData.height, {
                        inversionAttempts: "dontInvert",
                    });
                    
                    if (code) {
                        // Stop scanning
                        clearInterval(scanner);
                        video.srcObject.getTracks().forEach(track => track.stop());
                        
                        // Parse QR code data
                        try {
                            const qrData = JSON.parse(code.data);
                            if (qrData.shop_id && qrData.server_url) {
                                scanningStatus.textContent = 'QR code detected!';
                                shopInfo.textContent = 'Printing at: ' + (qrData.shop_name || qrData.shop_id);
                                shopIdInput.value = qrData.shop_id;
                                serverUrlInput.value = qrData.server_url;
                                
                                // Hide scanner, show upload form
                                document.getElementById('scanner').style.display = 'none';
                                uploadForm.style.display = 'block';
                            } else {
                                scanningStatus.textContent = 'Invalid QR code format';
                                startButton.style.display = 'inline-block';
                            }
                        } catch (e) {
                            scanningStatus.textContent = 'Could not parse QR code data';
                            startButton.style.display = 'inline-block';
                        }
                    }
                }
            }
            
            // Handle form submission
            printForm.addEventListener('submit', function(e) {
                e.preventDefault();
                
                const formData = new FormData(printForm);
                
                // Show loading state
                const submitBtn = printForm.querySelector('button[type="submit"]');
                const originalBtnText = submitBtn.textContent;
                submitBtn.textContent = 'Submitting...';
                submitBtn.disabled = true;
                
                // Clear previous messages
                successDiv.style.display = 'none';
                errorDiv.style.display = 'none';
                
                fetch('/', {
                    method: 'POST',
                    body: formData
                })
                .then(response => response.json())
                .then(data => {
                    submitBtn.textContent = originalBtnText;
                    submitBtn.disabled = false;
                    
                    if (data.status === 'success') {
                        successDiv.textContent = data.message + ' Job ID: ' + data.jobId;
                        successDiv.style.display = 'block';
                        printForm.reset();
                    } else {
                        errorDiv.textContent = data.error || 'An error occurred';
                        errorDiv.style.display = 'block';
                    }
                })
                .catch(error => {
                    submitBtn.textContent = originalBtnText;
                    submitBtn.disabled = false;
                    
                    errorDiv.textContent = 'Network error: ' + error.message;
                    errorDiv.style.display = 'block';
                });
            });
        });
    </script>
</body>
</html>
        ''')

if __name__ == '__main__':
    app.run(debug=True, port=8988)
