from flask import Flask, request, jsonify, render_template, send_from_directory
import os
import json
import base64
from datetime import datetime
import uuid
from flask_cors import CORS  # Add CORS support for cross-domain requests

app = Flask(__name__)
CORS(app)  # Enable CORS for all routes

# Configuration
UPLOAD_FOLDER = 'static/qr_codes'
SHOPS_DATA_FILE = 'data/shops.json'

# Ensure directories exist
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs('data', exist_ok=True)
os.makedirs('data/print_jobs', exist_ok=True)

# Initialize shops data if it doesn't exist
if not os.path.exists(SHOPS_DATA_FILE):
    with open(SHOPS_DATA_FILE, 'w') as f:
        json.dump([], f)

# Load shops data
def load_shops():
    try:
        with open(SHOPS_DATA_FILE, 'r') as f:
            return json.load(f)
    except:
        return []

# Save shops data
def save_shops(shops):
    with open(SHOPS_DATA_FILE, 'w') as f:
        json.dump(shops, f, indent=2)

@app.route('/')
def index():
    """Home page with basic service information"""
    return render_template('index.html')

@app.route('/api/register_shop', methods=['POST'])
def register_shop():
    """Register a new Xerox shop with QR code"""
    try:
        data = request.json
        
        # Validate required fields
        required_fields = ['shop_id', 'server_url']
        for field in required_fields:
            if field not in data:
                return jsonify({'error': f'Missing required field: {field}'}), 400
        
        # Process QR code image if present
        qr_filename = None
        if 'qr_code_image' in data and data['qr_code_image']:
            qr_data = base64.b64decode(data['qr_code_image'])
            qr_filename = f"qr_{data['shop_id']}_{uuid.uuid4().hex[:8]}.png"
            qr_path = os.path.join(UPLOAD_FOLDER, qr_filename)
            
            with open(qr_path, 'wb') as f:
                f.write(qr_data)
        
        # Load existing shops
        shops = load_shops()
        
        # Check if shop_id already exists
        for shop in shops:
            if shop['shop_id'] == data['shop_id']:
                # Update existing shop
                shop.update({
                    'shop_name': data.get('shop_name', ''),
                    'server_url': data['server_url'],
                    'updated_at': datetime.now().isoformat()
                })
                
                if qr_filename:
                    shop['qr_code_path'] = qr_filename
                
                save_shops(shops)
                return jsonify({'message': 'Shop updated successfully', 'shop_id': data['shop_id']}), 200
        
        # Create new shop record
        new_shop = {
            'shop_id': data['shop_id'],
            'shop_name': data.get('shop_name', ''),
            'server_url': data['server_url'],
            'created_at': datetime.now().isoformat(),
            'qr_code_path': qr_filename
        }
        
        shops.append(new_shop)
        save_shops(shops)
        
        return jsonify({'message': 'Shop registered successfully', 'shop_id': data['shop_id']}), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/shops', methods=['GET'])
def get_shops():
    """Get list of registered shops"""
    shops = load_shops()
    return jsonify(shops)

@app.route('/api/submit-print-job', methods=['POST'])
def submit_print_job():
    """Endpoint for mobile app to submit print jobs"""
    try:
        # Get form data
        shop_id = request.form.get('shop_id')
        copies = request.form.get('copies', 1)
        color = request.form.get('color', 'false').lower() == 'true'
        paper_size = request.form.get('paper_size', 'A4')
        
        # Get file
        if 'file' not in request.files:
            return jsonify({'error': 'No file part'}), 400
            
        file = request.files['file']
        
        if file.filename == '':
            return jsonify({'error': 'No selected file'}), 400
            
        # Validate shop_id
        shops = load_shops()
        shop_found = False
        for shop in shops:
            if shop['shop_id'] == shop_id:
                shop_found = True
                break
                
        if not shop_found:
            return jsonify({'error': 'Invalid shop ID'}), 400
            
        # Create print jobs directory if it doesn't exist
        print_jobs_dir = os.path.join('data', 'print_jobs', shop_id)
        os.makedirs(print_jobs_dir, exist_ok=True)
        
        # Save file
        job_id = f"job_{uuid.uuid4().hex}"
        file_ext = os.path.splitext(file.filename)[1]
        save_filename = f"{job_id}{file_ext}"
        file_path = os.path.join(print_jobs_dir, save_filename)
        file.save(file_path)
        
        # Save job details
        job_details = {
            'job_id': job_id,
            'shop_id': shop_id,
            'filename': file.filename,
            'file_path': file_path,
            'copies': copies,
            'color': color,
            'paper_size': paper_size,
            'status': 'pending',
            'created_at': datetime.now().isoformat()
        }
        
        jobs_file = os.path.join('data', 'print_jobs', f"{shop_id}_jobs.json")
        
        # Load existing jobs
        jobs = []
        if os.path.exists(jobs_file):
            with open(jobs_file, 'r') as f:
                try:
                    jobs = json.load(f)
                except:
                    jobs = []
        
        jobs.append(job_details)
        
        # Save updated jobs
        with open(jobs_file, 'w') as f:
            json.dump(jobs, f, indent=2)
            
        return jsonify({
            'message': 'Print job submitted successfully',
            'job_id': job_id
        }), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/admin')
def admin_dashboard():
    """Admin dashboard to view shops and print jobs"""
    shops = load_shops()
    return render_template('admin.html', shops=shops)

@app.route('/admin/jobs/<shop_id>')
def shop_jobs(shop_id):
    """View print jobs for a specific shop"""
    jobs_file = os.path.join('data', 'print_jobs', f"{shop_id}_jobs.json")
    jobs = []
    
    if os.path.exists(jobs_file):
        with open(jobs_file, 'r') as f:
            try:
                jobs = json.load(f)
            except:
                jobs = []
    
    shops = load_shops()
    shop_name = ""
    for shop in shops:
        if shop['shop_id'] == shop_id:
            shop_name = shop.get('shop_name', shop_id)
            break
            
    return render_template('jobs.html', jobs=jobs, shop_id=shop_id, shop_name=shop_name)

# Serve QR code images
@app.route('/static/qr_codes/<path:filename>')
def serve_qr_code(filename):
    return send_from_directory(UPLOAD_FOLDER, filename)

# Create simple HTML templates
@app.route('/templates/<template_name>')
def get_template(template_name):
    return send_from_directory('templates', template_name)

if __name__ == '__main__':
    # Create basic templates if they don't exist
    os.makedirs('templates', exist_ok=True)
    
    # Index template
    if not os.path.exists('templates/index.html'):
        with open('templates/index.html', 'w') as f:
            f.write('''
<!DOCTYPE html>
<html>
<head>
    <title>Xerox Print Service</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 0; padding: 20px; line-height: 1.6; }
        .container { max-width: 800px; margin: 0 auto; }
        h1 { color: #2c3e50; }
        .card { border: 1px solid #ddd; border-radius: 4px; padding: 20px; margin-bottom: 20px; }
    </style>
</head>
<body>
    <div class="container">
        <h1>Xerox Print Service</h1>
        <div class="card">
            <h2>Welcome to the Xerox Print Service</h2>
            <p>This service allows users to send print jobs directly to Xerox shops using QR codes.</p>
            <p>To get started, shop owners need to register their shop using the desktop application.</p>
        </div>
        <p><a href="/admin">Admin Dashboard</a></p>
    </div>
</body>
</html>
            ''')
    
    # Admin template
    if not os.path.exists('templates/admin.html'):
        with open('templates/admin.html', 'w') as f:
            f.write('''
<!DOCTYPE html>
<html>
<head>
    <title>Admin Dashboard - Xerox Print Service</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 0; padding: 20px; line-height: 1.6; }
        .container { max-width: 1000px; margin: 0 auto; }
        h1 { color: #2c3e50; }
        table { width: 100%; border-collapse: collapse; margin-top: 20px; }
        th, td { padding: 12px; text-align: left; border-bottom: 1px solid #ddd; }
        th { background-color: #f2f2f2; }
        tr:hover { background-color: #f5f5f5; }
        .btn { display: inline-block; padding: 8px 16px; background-color: #3498db; color: white; 
               text-decoration: none; border-radius: 4px; }
        .btn:hover { background-color: #2980b9; }
        .qr-code { max-width: 100px; max-height: 100px; }
    </style>
</head>
<body>
    <div class="container">
        <h1>Admin Dashboard</h1>
        <h2>Registered Shops</h2>
        
        {% if shops %}
        <table>
            <thead>
                <tr>
                    <th>Shop ID</th>
                    <th>Shop Name</th>
                    <th>Server URL</th>
                    <th>QR Code</th>
                    <th>Registered</th>
                    <th>Actions</th>
                </tr>
            </thead>
            <tbody>
                {% for shop in shops %}
                <tr>
                    <td>{{ shop.shop_id }}</td>
                    <td>{{ shop.shop_name or 'N/A' }}</td>
                    <td>{{ shop.server_url }}</td>
                    <td>
                        {% if shop.qr_code_path %}
                        <img src="/static/qr_codes/{{ shop.qr_code_path }}" class="qr-code">
                        {% else %}
                        No QR Code
                        {% endif %}
                    </td>
                    <td>{{ shop.created_at }}</td>
                    <td>
                        <a href="/admin/jobs/{{ shop.shop_id }}" class="btn">View Jobs</a>
                    </td>
                </tr>
                {% endfor %}
            </tbody>
        </table>
        {% else %}
        <p>No shops registered yet.</p>
        {% endif %}
        
        <p><a href="/">Back to Home</a></p>
    </div>
</body>
</html>
            ''')
    
    # Jobs template
    if not os.path.exists('templates/jobs.html'):
        with open('templates/jobs.html', 'w') as f:
            f.write('''
<!DOCTYPE html>
<html>
<head>
    <title>Print Jobs - Xerox Print Service</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 0; padding: 20px; line-height: 1.6; }
        .container { max-width: 1000px; margin: 0 auto; }
        h1, h2 { color: #2c3e50; }
        table { width: 100%; border-collapse: collapse; margin-top: 20px; }
        th, td { padding: 12px; text-align: left; border-bottom: 1px solid #ddd; }
        th { background-color: #f2f2f2; }
        tr:hover { background-color: #f5f5f5; }
        .status-pending { color: orange; }
        .status-completed { color: green; }
        .status-failed { color: red; }
        .btn { display: inline-block; padding: 8px 16px; background-color: #3498db; color: white; 
               text-decoration: none; border-radius: 4px; }
        .btn:hover { background-color: #2980b9; }
    </style>
</head>
<body>
    <div class="container">
        <h1>Print Jobs for {{ shop_name }}</h1>
        <h3>Shop ID: {{ shop_id }}</h3>
        
        {% if jobs %}
        <table>
            <thead>
                <tr>
                    <th>Job ID</th>
                    <th>Filename</th>
                    <th>Copies</th>
                    <th>Color</th>
                    <th>Paper Size</th>
                    <th>Status</th>
                    <th>Created</th>
                    <th>Actions</th>
                </tr>
            </thead>
            <tbody>
                {% for job in jobs %}
                <tr>
                    <td>{{ job.job_id }}</td>
                    <td>{{ job.filename }}</td>
                    <td>{{ job.copies }}</td>
                    <td>{{ 'Yes' if job.color else 'No' }}</td>
                    <td>{{ job.paper_size }}</td>
                    <td class="status-{{ job.status }}">{{ job.status }}</td>
                    <td>{{ job.created_at }}</td>
                    <td>
                        <button class="btn" onclick="updateStatus('{{ job.job_id }}', 'completed')">Mark Completed</button>
                    </td>
                </tr>
                {% endfor %}
            </tbody>
        </table>
        {% else %}
        <p>No print jobs for this shop yet.</p>
        {% endif %}
        
        <p><a href="/admin">Back to Admin Dashboard</a></p>
    </div>
    
    <script>
        function updateStatus(jobId, status) {
            // In a real implementation, this would call an API to update the job status
            alert('This functionality would update job ' + jobId + ' to status: ' + status);
            // Reload the page to show the updated status
            // location.reload();
        }
    </script>
</body>
</html>
            ''')
    
    app.run(debug=True, host='0.0.0.0', port=6989)
