import os
import pandas as pd
import matplotlib.pyplot as plt
from flask import Flask, render_template, request, send_file, redirect
from datetime import datetime
from collections import defaultdict

# Initialize Flask app
app = Flask(__name__)

# Set up the upload folder and allowed file extensions
UPLOAD_FOLDER = 'uploads'
OUTPUT_FOLDER = 'outputs'
ALLOWED_EXTENSIONS = {'csv'}

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['OUTPUT_FOLDER'] = OUTPUT_FOLDER

# Function to check file extensions
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# Route for the home page (upload form)
@app.route('/')
def index():
    return render_template('index.html')

# Route to handle CSV file upload
@app.route('/upload', methods=['POST'])
def upload_file():
    # Get the uploaded file
    if 'file' not in request.files:
        return redirect(request.url)
    file = request.files['file']

    if file.filename == '':
        return redirect(request.url)

    if file and allowed_file(file.filename):
        filename = os.path.join(app.config['UPLOAD_FOLDER'], file.filename)
        file.save(filename)

        # Process the CSV file
        output_file, graphs = process_csv(filename)

        # Provide download link for output file and graphs
        return render_template('output.html', output_file=output_file, graphs=graphs)

    return 'Invalid file format. Please upload a CSV file.'

# Function to process the uploaded CSV file
def process_csv(filepath):
    # Load CSV into pandas dataframe
    df = pd.read_csv(filepath)

    # Ensure datetime columns are in the right format
    df['Scheduled_Start'] = pd.to_datetime(df['Scheduled_Start'])
    df['Scheduled_End'] = pd.to_datetime(df['Scheduled_End'])
    df['Actual_Start'] = pd.to_datetime(df['Actual_Start'], errors='coerce')
    df['Actual_End'] = pd.to_datetime(df['Actual_End'], errors='coerce')

    # Compute additional columns (if needed)
    df['Calculated_Scheduled_Duration'] = (df['Scheduled_End'] - df['Scheduled_Start']).dt.total_seconds() / 3600
    df['Calculated_Actual_Duration'] = (df['Actual_End'] - df['Actual_Start']).dt.total_seconds() / 3600

    # Generate output CSV file
    output_filepath = os.path.join(app.config['OUTPUT_FOLDER'], 'output_schedule.csv')
    df.to_csv(output_filepath, index=False)

    # Create graphs
    graph_paths = create_graphs(df)

    return output_filepath, graph_paths

# Function to create graphs based on the data
def create_graphs(df):
    graph_paths = []
    
    # Graph 1: Job Scheduling Timeline
    plt.figure(figsize=(10, 6))
    plt.scatter(df['Scheduled_Start'], df['Machine_ID'], c='green', label='Scheduled')
    plt.scatter(df['Actual_Start'], df['Machine_ID'], c='red', label='Actual')
    plt.title('Job Scheduling Timeline')
    plt.xlabel('Time')
    plt.ylabel('Machine ID')
    plt.legend()
    timeline_path = os.path.join(app.config['OUTPUT_FOLDER'], 'schedule_timeline.png')
    plt.savefig(timeline_path)
    graph_paths.append(timeline_path)
    plt.close()

    # Graph 2: Machine Efficiency (Scheduled vs Actual Duration)
    plt.figure(figsize=(10, 6))
    plt.bar(df['Machine_ID'], df['Calculated_Scheduled_Duration'], alpha=0.6, label='Scheduled Duration')
    plt.bar(df['Machine_ID'], df['Calculated_Actual_Duration'], alpha=0.6, label='Actual Duration', color='orange')
    plt.title('Machine Efficiency (Scheduled vs Actual Duration)')
    plt.xlabel('Machine ID')
    plt.ylabel('Duration (hours)')
    plt.legend()
    efficiency_path = os.path.join(app.config['OUTPUT_FOLDER'], 'machine_efficiency.png')
    plt.savefig(efficiency_path)
    graph_paths.append(efficiency_path)
    plt.close()

    # Graph 3: Breakdown Alerts by Machine
    machine_failure_counts = df['Machine_ID'].value_counts()
    plt.figure(figsize=(10, 6))
    machine_failure_counts.plot(kind='bar', color='red')
    plt.title('Breakdown Alerts by Machine')
    plt.xlabel('Machine ID')
    plt.ylabel('Number of Failures')
    breakdown_path = os.path.join(app.config['OUTPUT_FOLDER'], 'breakdown_alerts.png')
    plt.savefig(breakdown_path)
    graph_paths.append(breakdown_path)
    plt.close()

    return graph_paths

# Route to download the output file and graphs
@app.route('/download/<filename>')
def download_file(filename):
    return send_file(os.path.join(app.config['OUTPUT_FOLDER'], filename), as_attachment=True)

if __name__ == '__main__':
    app.run(debug=True)
