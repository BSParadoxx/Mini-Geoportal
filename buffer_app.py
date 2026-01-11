from flask import Blueprint, Flask, request, send_file, render_template, jsonify
import os
import geopandas as gpd
import zipfile
import shutil


buffer_app = Blueprint('buffer_app', __name__)

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['RESULT_FOLDER'] = 'results'
app.secret_key = 'your_secret_key_here'

# Allow only zip files for upload
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() == 'zip'

# Perform buffer analysis on the extracted shapefile
def perform_buffer_analysis(upload_folder, result_folder, shapefile, buffer_distance):
    gdf = gpd.read_file(shapefile)
    gdf['geometry'] = gdf['geometry'].buffer(buffer_distance)
    
    result_filename = 'buffer_result.geojson'
    result_filepath = os.path.join(result_folder, result_filename)
    gdf.to_file(result_filepath, driver='GeoJSON')
    
    return result_filepath

@app.route('/')
def index():
    return render_template('buffer.html')

@app.route('/upload-buffer', methods=['POST'])
def upload_buffer():
    if 'vector_file' not in request.files:
        return jsonify({'error': 'No file part'}), 400
    file = request.files['vector_file']
    if file.filename == '':
        return jsonify({'error': 'No selected file'}), 400
    if file and allowed_file(file.filename):
        filename = file.filename
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        
        os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
        os.makedirs(app.config['RESULT_FOLDER'], exist_ok=True)
        
        file.save(file_path)
        try:
            with zipfile.ZipFile(file_path, 'r') as zip_ref:
                extract_folder = os.path.join(app.config['UPLOAD_FOLDER'], filename.rsplit('.', 1)[0])
                zip_ref.extractall(extract_folder)
            
            shp_files = [os.path.join(extract_folder, f) for f in os.listdir(extract_folder) if f.endswith('.shp')]
            if not shp_files:
                return jsonify({'error': 'No .shp file found in the zip archive'}), 400
            
            buffer_distance = float(request.form['buffer_distance'])
            result_filepath = perform_buffer_analysis(extract_folder, app.config['RESULT_FOLDER'], shp_files[0], buffer_distance)
            
            # Return result file path to be processed by client-side JavaScript
            return jsonify({'result': result_filepath})
        except Exception as e:
            return jsonify({'error': str(e)}), 500
    else:
        return jsonify({'error': 'Unsupported file format'}), 400

if __name__ == '__main__':
    app.run(debug=True)
