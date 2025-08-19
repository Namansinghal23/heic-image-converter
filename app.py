from flask import Flask, request, send_file, jsonify, session
import os
import uuid
from datetime import datetime
import zipfile
from werkzeug.utils import secure_filename
from PIL import Image
import io

# Try different HEIC libraries
HEIC_SUPPORT_METHOD = None

# Method 1: Try pillow-heif
try:
    from pillow_heif import register_heif_opener
    register_heif_opener()
    HEIC_SUPPORT_METHOD = "pillow-heif"
    print("✅ HEIC support enabled via pillow-heif")
except ImportError:
    print("⚠️  pillow-heif not available")

# Method 2: Try imageio
if HEIC_SUPPORT_METHOD is None:
    try:
        import imageio.v3 as iio
        HEIC_SUPPORT_METHOD = "imageio"
        print("✅ HEIC support enabled via imageio")
    except ImportError:
        try:
            import imageio
            HEIC_SUPPORT_METHOD = "imageio"
            print("✅ HEIC support enabled via imageio (v2)")
        except ImportError:
            print("⚠️  imageio not available")

if HEIC_SUPPORT_METHOD is None:
    print("❌ No HEIC support available.")
else:
    print(f"🎯 Using {HEIC_SUPPORT_METHOD} for HEIC conversion")

app = Flask(__name__)
app.secret_key = 'your-secret-key-change-this'

# Configuration
UPLOAD_FOLDER = 'temp_uploads'
CONVERTED_FOLDER = 'temp_converted'
ALLOWED_EXTENSIONS = {'heic', 'heif', 'jpg', 'jpeg', 'png', 'bmp', 'gif', 'tiff', 'webp'}
MAX_FILE_SIZE = 16 * 1024 * 1024  # 16MB

# Create directories if they don't exist
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(CONVERTED_FOLDER, exist_ok=True)

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def get_file_format(filename):
    return filename.rsplit('.', 1)[1].lower() if '.' in filename else None

def convert_heic_with_imageio(input_path):
    """Convert HEIC using imageio"""
    try:
        # Try imageio v3 first
        try:
            import imageio.v3 as iio
            heic_array = iio.imread(input_path)
        except:
            # Fallback to imageio v2
            import imageio
            heic_array = imageio.imread(input_path)
        
        # Convert numpy array to PIL Image
        if len(heic_array.shape) == 3:
            pil_image = Image.fromarray(heic_array, 'RGB')
        else:
            pil_image = Image.fromarray(heic_array)
        
        return pil_image
    except Exception as e:
        raise Exception(f"imageio HEIC conversion failed: {str(e)}")

def convert_image(input_path, output_format):
    """Convert image to specified format with HEIC support"""
    try:
        input_format = get_file_format(input_path)
        
        # Handle HEIC/HEIF files
        if input_format in ['heic', 'heif']:
            if HEIC_SUPPORT_METHOD == "pillow-heif":
                # Use pillow-heif (best method)
                img = Image.open(input_path)
            elif HEIC_SUPPORT_METHOD == "imageio":
                # Use imageio as fallback
                img = convert_heic_with_imageio(input_path)
            else:
                raise Exception("HEIC support not available. Please install pillow-heif or imageio")
        else:
            # Regular image formats
            img = Image.open(input_path)
        
        # Convert to RGB if necessary (for JPEG)
        if output_format.lower() == 'jpeg' and img.mode in ('RGBA', 'LA', 'P'):
            # Create white background for transparent images
            background = Image.new('RGB', img.size, (255, 255, 255))
            if img.mode == 'P':
                img = img.convert('RGBA')
            if img.mode == 'RGBA':
                background.paste(img, mask=img.split()[-1])
            else:
                background.paste(img)
            img = background
        
        # Create output filename
        unique_id = str(uuid.uuid4())[:8]
        output_filename = f"converted_{unique_id}.{output_format.lower()}"
        output_path = os.path.join(CONVERTED_FOLDER, output_filename)
        
        # Save with high quality
        if output_format.lower() == 'jpeg':
            img.save(output_path, 'JPEG', quality=95, optimize=True)
        else:  # PNG
            img.save(output_path, 'PNG', optimize=True)
        
        return output_path, output_filename
            
    except Exception as e:
        raise Exception(f"Conversion failed: {str(e)}")

@app.route('/')
def index():
    if 'conversion_history' not in session:
        session['conversion_history'] = []
    
    # Dynamic support message
    if HEIC_SUPPORT_METHOD:
        support_message = f"✅ HEIC/HEIF support enabled via {HEIC_SUPPORT_METHOD}! Also supports: JPG, PNG, BMP, GIF, TIFF, WebP"
        status_class = "success"
    else:
        support_message = "Currently supports: JPG, PNG, BMP, GIF, TIFF, WebP"
        status_class = "warning"
    
    return f'''
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{"HEIC " if HEIC_SUPPORT_METHOD else ""}Image Converter</title>
    <style>
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}
        
        body {{
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            padding: 20px;
        }}
        
        .container {{
            max-width: 800px;
            margin: 0 auto;
            background: white;
            border-radius: 20px;
            box-shadow: 0 20px 40px rgba(0,0,0,0.1);
            overflow: hidden;
        }}
        
        .header {{
            background: linear-gradient(135deg, #4facfe 0%, #00f2fe 100%);
            color: white;
            padding: 30px;
            text-align: center;
        }}
        
        .header h1 {{
            font-size: 2.5rem;
            margin-bottom: 10px;
            font-weight: 300;
        }}
        
        .header p {{
            font-size: 1.1rem;
            opacity: 0.9;
        }}
        
        .notice {{
            background: {"#d4edda" if status_class == "success" else "#fff3cd"};
            border: 1px solid {"#c3e6cb" if status_class == "success" else "#ffeaa7"};
            color: {"#155724" if status_class == "success" else "#856404"};
            padding: 15px;
            margin: 20px;
            border-radius: 10px;
        }}
        
        .notice.success {{
            background: #d4edda;
            border-color: #c3e6cb;
            color: #155724;
        }}
        
        .notice.warning {{
            background: #fff3cd;
            border-color: #ffeaa7;
            color: #856404;
        }}
        
        .main-content {{
            padding: 40px;
        }}
        
        .upload-section {{
            background: #f8f9fa;
            border: 3px dashed #dee2e6;
            border-radius: 15px;
            padding: 40px;
            text-align: center;
            transition: all 0.3s ease;
            cursor: pointer;
            margin-bottom: 30px;
        }}
        
        .upload-section:hover {{
            border-color: #4facfe;
            background: #e3f2fd;
        }}
        
        .upload-section.dragover {{
            border-color: #4facfe;
            background: #e3f2fd;
            transform: scale(1.02);
        }}
        
        .upload-icon {{
            font-size: 4rem;
            color: #6c757d;
            margin-bottom: 20px;
        }}
        
        .upload-text {{
            font-size: 1.2rem;
            color: #495057;
            margin-bottom: 10px;
        }}
        
        .upload-subtext {{
            font-size: 0.9rem;
            color: #6c757d;
            margin-bottom: 20px;
        }}
        
        .file-input {{
            display: none;
        }}
        
        .btn {{
            padding: 12px 30px;
            border: none;
            border-radius: 25px;
            cursor: pointer;
            font-size: 1rem;
            font-weight: 500;
            transition: all 0.3s ease;
            text-transform: uppercase;
            letter-spacing: 1px;
        }}
        
        .btn-primary {{
            background: linear-gradient(135deg, #4facfe 0%, #00f2fe 100%);
            color: white;
        }}
        
        .btn-primary:hover {{
            transform: translateY(-2px);
            box-shadow: 0 10px 20px rgba(79, 172, 254, 0.3);
        }}
        
        .btn-success {{
            background: linear-gradient(135deg, #56ab2f 0%, #a8e6cf 100%);
            color: white;
        }}
        
        .btn-success:hover {{
            transform: translateY(-2px);
            box-shadow: 0 10px 20px rgba(86, 171, 47, 0.3);
        }}
        
        .format-selection {{
            margin: 30px 0;
            text-align: center;
        }}
        
        .format-selection h3 {{
            margin-bottom: 20px;
            color: #495057;
        }}
        
        .format-options {{
            display: flex;
            gap: 20px;
            justify-content: center;
        }}
        
        .format-option {{
            position: relative;
        }}
        
        .format-option input[type="radio"] {{
            display: none;
        }}
        
        .format-label {{
            display: block;
            padding: 15px 30px;
            background: #f8f9fa;
            border: 2px solid #dee2e6;
            border-radius: 25px;
            cursor: pointer;
            transition: all 0.3s ease;
            font-weight: 500;
            text-transform: uppercase;
            letter-spacing: 1px;
        }}
        
        .format-option input[type="radio"]:checked + .format-label {{
            background: linear-gradient(135deg, #4facfe 0%, #00f2fe 100%);
            color: white;
            border-color: #4facfe;
            transform: translateY(-2px);
            box-shadow: 0 10px 20px rgba(79, 172, 254, 0.3);
        }}
        
        .selected-files {{
            margin: 20px 0;
        }}
        
        .file-list {{
            background: #f8f9fa;
            border-radius: 10px;
            padding: 20px;
            margin-top: 15px;
        }}
        
        .file-item {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding: 10px;
            background: white;
            border-radius: 8px;
            margin-bottom: 10px;
            box-shadow: 0 2px 5px rgba(0,0,0,0.1);
        }}
        
        .file-item:last-child {{
            margin-bottom: 0;
        }}
        
        .file-info {{
            flex: 1;
        }}
        
        .file-name {{
            font-weight: 500;
            color: #495057;
        }}
        
        .file-size {{
            font-size: 0.8rem;
            color: #6c757d;
        }}
        
        .convert-section {{
            text-align: center;
            margin-top: 30px;
        }}
        
        .result-section {{
            margin-top: 30px;
            padding: 20px;
            background: #f8f9fa;
            border-radius: 15px;
            display: none;
        }}
        
        .success-message {{
            color: #28a745;
            margin-bottom: 15px;
        }}
        
        .error-message {{
            color: #dc3545;
            margin-bottom: 15px;
        }}
        
        .history-section {{
            margin-top: 40px;
            padding: 30px;
            background: #f8f9fa;
            border-radius: 15px;
        }}
        
        .history-header {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 20px;
        }}
        
        .history-header h3 {{
            color: #495057;
        }}
        
        .btn-outline {{
            background: transparent;
            border: 2px solid #dee2e6;
            color: #6c757d;
            padding: 8px 20px;
            font-size: 0.9rem;
        }}
        
        .btn-outline:hover {{
            border-color: #4facfe;
            color: #4facfe;
        }}
        
        .history-list {{
            max-height: 300px;
            overflow-y: auto;
        }}
        
        .history-item {{
            background: white;
            border-radius: 10px;
            padding: 15px;
            margin-bottom: 10px;
            box-shadow: 0 2px 5px rgba(0,0,0,0.1);
        }}
        
        .history-time {{
            font-size: 0.9rem;
            color: #6c757d;
            margin-bottom: 5px;
        }}
        
        .history-details {{
            color: #495057;
            font-weight: 500;
        }}
        
        .history-files {{
            font-size: 0.8rem;
            color: #6c757d;
            margin-top: 5px;
        }}
        
        .loading {{
            display: none;
            text-align: center;
            padding: 20px;
        }}
        
        .spinner {{
            border: 4px solid #f3f3f3;
            border-top: 4px solid #4facfe;
            border-radius: 50%;
            width: 40px;
            height: 40px;
            animation: spin 1s linear infinite;
            margin: 0 auto 10px;
        }}
        
        @keyframes spin {{
            0% {{ transform: rotate(0deg); }}
            100% {{ transform: rotate(360deg); }}
        }}
        
        .empty-state {{
            text-align: center;
            padding: 40px;
            color: #6c757d;
        }}
        
        @media (max-width: 768px) {{
            .container {{
                margin: 10px;
                border-radius: 15px;
            }}
            
            .header h1 {{
                font-size: 2rem;
            }}
            
            .main-content {{
                padding: 20px;
            }}
            
            .format-options {{
                flex-direction: column;
                align-items: center;
            }}
            
            .format-label {{
                width: 200px;
            }}
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🖼️ {"HEIC " if HEIC_SUPPORT_METHOD else ""}Image Converter</h1>
            <p>Convert your {"HEIC/HEIF and other " if HEIC_SUPPORT_METHOD else ""}images to PNG or JPEG format with high quality</p>
        </div>
        
        <div class="notice {status_class}">
            <strong>📝 Status:</strong> {support_message}
            {'' if HEIC_SUPPORT_METHOD else '<br><strong>💡 Tip:</strong> For HEIC support, install: <code>pip install pillow-heif</code> or <code>pip install imageio</code>'}
        </div>
        
        <div class="main-content">
            <!-- Upload Section -->
            <div class="upload-section" onclick="document.getElementById('fileInput').click()">
                <div class="upload-icon">📁</div>
                <div class="upload-text">Click here or drag & drop your image files</div>
                <div class="upload-subtext">{"HEIC, HEIF, " if HEIC_SUPPORT_METHOD else ""}JPG, PNG, BMP, GIF, TIFF, WebP supported • Max 16MB per file</div>
                <button class="btn btn-primary" type="button">Choose Files</button>
                <input type="file" id="fileInput" class="file-input" multiple accept=".heic,.heif,.jpg,.jpeg,.png,.bmp,.gif,.tiff,.webp">
            </div>
            
            <!-- Format Selection -->
            <div class="format-selection">
                <h3>Choose Output Format</h3>
                <div class="format-options">
                    <div class="format-option">
                        <input type="radio" name="format" value="png" id="formatPNG" checked>
                        <label for="formatPNG" class="format-label">PNG</label>
                    </div>
                    <div class="format-option">
                        <input type="radio" name="format" value="jpeg" id="formatJPEG">
                        <label for="formatJPEG" class="format-label">JPEG</label>
                    </div>
                </div>
            </div>
            
            <!-- Selected Files -->
            <div class="selected-files" id="selectedFiles" style="display: none;">
                <h3>Selected Files:</h3>
                <div class="file-list" id="fileList"></div>
            </div>
            
            <!-- Convert Button -->
            <div class="convert-section">
                <button class="btn btn-success" id="convertBtn" onclick="convertFiles()" style="display: none;">
                    Convert Images
                </button>
            </div>
            
            <!-- Loading -->
            <div class="loading" id="loading">
                <div class="spinner"></div>
                <p>Converting your images...</p>
            </div>
            
            <!-- Result Section -->
            <div class="result-section" id="resultSection">
                <div id="resultMessage"></div>
            </div>
        </div>
        
        <!-- History Section -->
        <div class="history-section">
            <div class="history-header">
                <h3>📋 Conversion History</h3>
                <button class="btn btn-outline" onclick="clearHistory()">Clear History</button>
            </div>
            <div class="history-list" id="historyList">
                <div class="empty-state">
                    <p>No conversion history yet. Convert some images to see your history here!</p>
                </div>
            </div>
        </div>
    </div>

    <script>
        let selectedFiles = [];
        
        // File input change event
        document.getElementById('fileInput').addEventListener('change', handleFileSelect);
        
        // Drag and drop functionality
        const uploadSection = document.querySelector('.upload-section');
        
        uploadSection.addEventListener('dragover', (e) => {{
            e.preventDefault();
            uploadSection.classList.add('dragover');
        }});
        
        uploadSection.addEventListener('dragleave', () => {{
            uploadSection.classList.remove('dragover');
        }});
        
        uploadSection.addEventListener('drop', (e) => {{
            e.preventDefault();
            uploadSection.classList.remove('dragover');
            const files = e.dataTransfer.files;
            handleFiles(files);
        }});
        
        function handleFileSelect(e) {{
            handleFiles(e.target.files);
        }}
        
        function handleFiles(files) {{
            selectedFiles = Array.from(files).filter(file => {{
                const ext = file.name.split('.').pop().toLowerCase();
                return ['heic', 'heif', 'jpg', 'jpeg', 'png', 'bmp', 'gif', 'tiff', 'webp'].includes(ext);
            }});
            
            if (selectedFiles.length === 0) {{
                alert('Please select supported image files ({"HEIC, HEIF, " if HEIC_SUPPORT_METHOD else ""}JPG, PNG, BMP, GIF, TIFF, WebP).');
                return;
            }}
            
            displaySelectedFiles();
            document.getElementById('convertBtn').style.display = 'inline-block';
        }}
        
        function displaySelectedFiles() {{
            const fileList = document.getElementById('fileList');
            const selectedFilesDiv = document.getElementById('selectedFiles');
            
            fileList.innerHTML = '';
            
            selectedFiles.forEach((file, index) => {{
                const fileItem = document.createElement('div');
                fileItem.className = 'file-item';
                fileItem.innerHTML = `
                    <div class="file-info">
                        <div class="file-name">${{file.name}}</div>
                        <div class="file-size">${{formatFileSize(file.size)}}</div>
                    </div>
                `;
                fileList.appendChild(fileItem);
            }});
            
            selectedFilesDiv.style.display = 'block';
        }}
        
        function formatFileSize(bytes) {{
            if (bytes === 0) return '0 Bytes';
            const k = 1024;
            const sizes = ['Bytes', 'KB', 'MB', 'GB'];
            const i = Math.floor(Math.log(bytes) / Math.log(k));
            return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
        }}
        
        async function convertFiles() {{
            if (selectedFiles.length === 0) {{
                alert('Please select files first.');
                return;
            }}
            
            const format = document.querySelector('input[name="format"]:checked').value;
            const formData = new FormData();
            
            selectedFiles.forEach(file => {{
                formData.append('files', file);
            }});
            formData.append('format', format);
            
            // Show loading
            document.getElementById('loading').style.display = 'block';
            document.getElementById('resultSection').style.display = 'none';
            document.getElementById('convertBtn').disabled = true;
            
            try {{
                const response = await fetch('/convert', {{
                    method: 'POST',
                    body: formData
                }});
                
                const result = await response.json();
                
                // Hide loading
                document.getElementById('loading').style.display = 'none';
                document.getElementById('convertBtn').disabled = false;
                
                if (result.success) {{
                    showResult(result);
                    loadHistory(); // Reload history
                    
                    // Reset form
                    selectedFiles = [];
                    document.getElementById('fileInput').value = '';
                    document.getElementById('selectedFiles').style.display = 'none';
                    document.getElementById('convertBtn').style.display = 'none';
                }} else {{
                    showError(result.error, result.details);
                }}
                
            }} catch (error) {{
                document.getElementById('loading').style.display = 'none';
                document.getElementById('convertBtn').disabled = false;
                showError('Network error: ' + error.message);
            }}
        }}
        
        function showResult(result) {{
            const resultSection = document.getElementById('resultSection');
            const resultMessage = document.getElementById('resultMessage');
            
            let message = `
                <div class="success-message">
                    <h4>✅ Conversion Successful!</h4>
                    <p>Your ${{result.single_file ? 'image has' : 'images have'}} been converted successfully.</p>
                </div>
            `;
            
            if (result.errors && result.errors.length > 0) {{
                message += `
                    <div class="error-message">
                        <h5>⚠️ Some files had issues:</h5>
                        <ul>
                            ${{result.errors.map(error => `<li>${{error}}</li>`).join('')}}
                        </ul>
                    </div>
                `;
            }}
            
            message += `
                <div style="margin-top: 20px;">
                    <a href="${{result.download_url}}" class="btn btn-success" download>
                        📥 Download ${{result.single_file ? 'Image' : 'Archive'}}
                    </a>
                </div>
            `;
            
            resultMessage.innerHTML = message;
            resultSection.style.display = 'block';
        }}
        
        function showError(error, details = null) {{
            const resultSection = document.getElementById('resultSection');
            const resultMessage = document.getElementById('resultMessage');
            
            let message = `
                <div class="error-message">
                    <h4>❌ Conversion Failed</h4>
                    <p>${{error}}</p>
                </div>
            `;
            
            if (details && details.length > 0) {{
                message += `
                    <div class="error-message">
                        <h5>Details:</h5>
                        <ul>
                            ${{details.map(detail => `<li>${{detail}}</li>`).join('')}}
                        </ul>
                    </div>
                `;
            }}
            
            resultMessage.innerHTML = message;
            resultSection.style.display = 'block';
        }}
        
        async function loadHistory() {{
            try {{
                const response = await fetch('/history');
                const data = await response.json();
                displayHistory(data.history);
            }} catch (error) {{
                console.error('Failed to load history:', error);
            }}
        }}
        
        function displayHistory(history) {{
            const historyList = document.getElementById('historyList');
            
            if (history.length === 0) {{
                historyList.innerHTML = `
                    <div class="empty-state">
                        <p>No conversion history yet. Convert some images to see your history here!</p>
                    </div>
                `;
                return;
            }}
            
            historyList.innerHTML = history.map(item => `
                <div class="history-item">
                    <div class="history-time">${{item.timestamp}}</div>
                    <div class="history-details">
                        Converted ${{item.files_count}} file${{item.files_count > 1 ? 's' : ''}} to ${{item.output_format}}
                    </div>
                    <div class="history-files">
                        Files: ${{item.files.join(', ')}}
                    </div>
                </div>
            `).join('');
        }}
        
        async function clearHistory() {{
            if (confirm('Are you sure you want to clear the conversion history?')) {{
                try {{
                    await fetch('/clear-history', {{ method: 'POST' }});
                    loadHistory();
                }} catch (error) {{
                    alert('Failed to clear history');
                }}
            }}
        }}
        
        // Load history on page load
        document.addEventListener('DOMContentLoaded', loadHistory);
    </script>
</body>
</html>
    '''

@app.route('/convert', methods=['POST'])
def convert_files():
    try:
        if 'files' not in request.files:
            return jsonify({'error': 'No files uploaded'}), 400
        
        files = request.files.getlist('files')
        output_format = request.form.get('format', 'png').lower()
        
        if not files or all(file.filename == '' for file in files):
            return jsonify({'error': 'No files selected'}), 400
        
        if output_format not in ['png', 'jpeg']:
            return jsonify({'error': 'Invalid output format'}), 400
        
        converted_files = []
        errors = []
        
        for file in files:
            if file.filename == '':
                continue
                
            filename = secure_filename(file.filename)
            
            # Check file size
            file.seek(0, os.SEEK_END)
            file_size = file.tell()
            file.seek(0)
            
            if file_size > MAX_FILE_SIZE:
                errors.append(f"{filename}: File too large (max 16MB)")
                continue
            
            # Check if file is allowed
            if not allowed_file(filename):
                errors.append(f"{filename}: Unsupported file format")
                continue
            
            # Check if trying to convert to same format
            input_format = get_file_format(filename)
            if input_format and input_format.lower() in ['jpg', 'jpeg'] and output_format == 'jpeg':
                errors.append(f"{filename}: File is already in JPEG format")
                continue
            elif input_format and input_format.lower() == 'png' and output_format == 'png':
                errors.append(f"{filename}: File is already in PNG format")
                continue
            
            try:
                # Save uploaded file temporarily
                unique_id = str(uuid.uuid4())[:8]
                temp_filename = f"temp_{unique_id}_{filename}"
                temp_path = os.path.join(UPLOAD_FOLDER, temp_filename)
                file.save(temp_path)
                
                # Convert the image
                output_path, output_filename = convert_image(temp_path, output_format)
                
                # Add to converted files list
                converted_files.append({
                    'original_name': filename,
                    'converted_name': output_filename,
                    'path': output_path,
                    'size': os.path.getsize(output_path)
                })
                
                # Clean up temp file
                os.remove(temp_path)
                
            except Exception as e:
                errors.append(f"{filename}: {str(e)}")
        
        if not converted_files:
            return jsonify({'error': 'No files could be converted', 'details': errors}), 400
        
        # Update conversion history
        if 'conversion_history' not in session:
            session['conversion_history'] = []
        
        history_entry = {
            'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'files_count': len(converted_files),
            'output_format': output_format.upper(),
            'files': [f['original_name'] for f in converted_files]
        }
        session['conversion_history'].append(history_entry)
        session.modified = True
        
        # If single file, return direct download
        if len(converted_files) == 1:
            return jsonify({
                'success': True,
                'single_file': True,
                'download_url': f"/download/{converted_files[0]['converted_name']}",
                'filename': converted_files[0]['converted_name'],
                'errors': errors if errors else None
            })
        
        # Multiple files - create zip
        zip_filename = f"converted_images_{datetime.now().strftime('%Y%m%d_%H%M%S')}.zip"
        zip_path = os.path.join(CONVERTED_FOLDER, zip_filename)
        
        with zipfile.ZipFile(zip_path, 'w') as zipf:
            for file_info in converted_files:
                zipf.write(file_info['path'], file_info['converted_name'])
        
        return jsonify({
            'success': True,
            'single_file': False,
            'download_url': f"/download/{zip_filename}",
            'filename': zip_filename,
            'converted_count': len(converted_files),
            'errors': errors if errors else None
        })
        
    except Exception as e:
        return jsonify({'error': f'Server error: {str(e)}'}), 500

@app.route('/download/<filename>')
def download_file(filename):
    try:
        file_path = os.path.join(CONVERTED_FOLDER, filename)
        if not os.path.exists(file_path):
            return "File not found", 404
        
        return send_file(file_path, as_attachment=True, download_name=filename)
        
    except Exception as e:
        return f"Download error: {str(e)}", 500

@app.route('/history')
def get_history():
    history = session.get('conversion_history', [])
    return jsonify({'history': history})

@app.route('/clear-history', methods=['POST'])
def clear_history():
    session['conversion_history'] = []
    session.modified = True
    return jsonify({'success': True})

# Cleanup function to remove old files (call periodically)
def cleanup_temp_files():
    """Remove files older than 1 hour from temp directories"""
    import time
    current_time = time.time()
    
    for folder in [UPLOAD_FOLDER, CONVERTED_FOLDER]:
        for filename in os.listdir(folder):
            file_path = os.path.join(folder, filename)
            if os.path.isfile(file_path):
                if current_time - os.path.getctime(file_path) > 3600:  # 1 hour
                    try:
                        os.remove(file_path)
                    except OSError:
                        pass

if __name__ == '__main__':
    print("🖼️  HEIC Image Converter Server Starting...")
    print("📋 Access the application at: http://localhost:5000")
    
    if HEIC_SUPPORT_METHOD:
        print(f"✅ HEIC/HEIF support: {HEIC_SUPPORT_METHOD}")
        print("🎯 Supports: HEIC, HEIF, JPG, PNG, BMP, GIF, TIFF, WebP")
    else:
        print("⚠️  HEIC support not available")
        print("🔧 Supports: JPG, PNG, BMP, GIF, TIFF, WebP")
        print("💡 For HEIC support: pip install pillow-heif")
    
    print("=" * 60)
    
    app.run(debug=True, host='0.0.0.0', port=5000)