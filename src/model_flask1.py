# --- model_flask1.py (Final Clean Combined Version) ---

from flask import Flask, request, render_template, redirect, url_for, send_from_directory
import pandas as pd
import os
import json
import pickle
import joblib
import numpy as np
from tensorflow.keras.models import load_model
from werkzeug.utils import secure_filename

# --- Initialize Flask ---
app = Flask(__name__)

# --- Configuration ---
UPLOAD_FOLDER = 'uploads'
ALLOWED_EXTENSIONS = {'csv'}
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# --- Load Predictive Maintenance Models ---
model_pipeline = pickle.load(open("predictive_maintenance_model.pkl", "rb"))
lstm_model = load_model("lstm_model.h5")
scaler = joblib.load("scaler.pkl")
max_rul_value = joblib.load("max_rul.pkl")

# --- Helper Functions ---
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def predict_rul(input_list):
    arr = np.array(input_list).reshape(1, -1)
    scaled = scaler.transform(arr)
    reshaped = scaled.reshape(1, 1, scaled.shape[1])
    prediction = lstm_model.predict(reshaped)[0][0]
    return round(prediction * max_rul_value, 2)

# --- Routes ---

# Home Page for Scheduling
@app.route('/')
def home():
    return render_template('scheduling.html')

# --- Predictive Maintenance Pages ---

# Manual Input Page
@app.route('/model', methods=['GET'])
def model_page():
    return render_template('model.html')

# Predict from Form Data
@app.route('/predict', methods=['POST'])
def predict():
    try:
        air_temperature = float(request.form['air_temperature'])
        process_temperature = float(request.form['process_temperature'])
        rotational_speed = int(request.form['rotational_speed'])
        torque = float(request.form['torque'])
        tool_wear = int(request.form['tool_wear'])
        machine_type = request.form['machine_type']

        data = {
            'Air temperature [K]': [air_temperature],
            'Process temperature [K]': [process_temperature],
            'Rotational speed [rpm]': [rotational_speed],
            'Torque [Nm]': [torque],
            'Tool wear [min]': [tool_wear],
            'Type': [machine_type]
        }
        input_df = pd.DataFrame(data)
        prediction = model_pipeline.predict(input_df)
        prediction_text = "Yes" if prediction[0] == 1 else "No"

        power = rotational_speed * torque
        input_for_rul = [air_temperature, process_temperature, rotational_speed, torque, tool_wear, power]
        rul = predict_rul(input_for_rul)

        dashboard_data = {
            "air_temperature": air_temperature,
            "process_temperature": process_temperature,
            "rotational_speed": rotational_speed,
            "torque": torque,
            "tool_wear": tool_wear,
            "machine_type": machine_type,
            "prediction_text": prediction_text,
            "rul": rul
        }

    except ValueError:
        return render_template("model.html", prediction_text="Input error: Please enter valid numeric values for all fields.")

    return redirect(url_for('dashboard', **dashboard_data))

# Maintenance Prediction Dashboard
@app.route('/dashboard')
def dashboard():
    air_temperature = request.args.get('air_temperature', type=float)
    process_temperature = request.args.get('process_temperature', type=float)
    rotational_speed = request.args.get('rotational_speed', type=int)
    torque = request.args.get('torque', type=float)
    tool_wear = request.args.get('tool_wear', type=int)
    machine_type = request.args.get('machine_type', type=str)
    prediction_text = request.args.get('prediction_text', type=str)
    rul = request.args.get('rul', type=float)

    efficiency = 100 - (tool_wear / 2.5)
    if prediction_text == "No":
        if efficiency <= 35:
            efficiency_text = "Change of Tools required"
        elif efficiency <= 60:
            efficiency_text = "Monitor Tools"
        else:
            efficiency_text = "Everything is working fine."
    else:
        efficiency_text = "Urgent Maintenance Required"

    return render_template('dashboard.html',
                           air_temperature=air_temperature,
                           process_temperature=process_temperature,
                           rotational_speed=rotational_speed,
                           torque=torque,
                           tool_wear=tool_wear,
                           machine_type=machine_type,
                           prediction_text=prediction_text,
                           efficiency_text=efficiency_text,
                           efficiency=efficiency,
                           rul=rul)

# Upload CSV for Bulk Maintenance Prediction
@app.route('/upload', methods=['GET', 'POST'])
def upload_file():
    if request.method == 'POST':
        try:
            if 'file' not in request.files:
                return redirect(request.url)
            file = request.files['file']
            if file.filename == '':
                return redirect(request.url)
            if file and allowed_file(file.filename):
                filename = secure_filename(file.filename)
                file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                file.save(file_path)

                data = pd.read_csv(file_path)
                if 'UID' in data.columns:
                    data.drop('UID', axis=1, inplace=True)

                prediction = model_pipeline.predict(data)
                failure_types = ["Heat Dissipation", "No Failure", "Over Strain", "Power Failure", "Random Failure", "Tool Wear Failure"]
                data['Predicted_Value'] = [failure_types[i] for i in prediction]

                output_filename = 'output_' + filename
                output_filepath = os.path.join(app.config['UPLOAD_FOLDER'], output_filename)
                data.to_csv(output_filepath, index=False)

                return redirect(url_for('download_file', filename=output_filename))

        except Exception:
            return render_template("model.html", error="An error occurred while processing the file. Please ensure it's a valid CSV.")

    return render_template("model.html")

# Download Predicted Output
@app.route('/uploads/<filename>')
def download_file(filename):
    try:
        return send_from_directory(app.config['UPLOAD_FOLDER'], filename, as_attachment=True)
    except Exception:
        return render_template("model.html", error="File not found or an error occurred while trying to download the file.")

# --- Job Scheduling Pages ---

# Upload CSV for Job Scheduling
@app.route('/job-scheduling', methods=['GET', 'POST'])
def job_scheduling():
    if request.method == 'POST':
        file = request.files.get('file')
        algorithm_choice = request.form.get('algorithm')

        if not file or file.filename == '':
            return render_template("scheduling.html", error="No file selected.")

        filename = secure_filename(file.filename)
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(filepath)

        df = pd.read_csv(filepath)

        expected_columns = ['Job_Name', 'Machine_Name', 'Start_Time', 'End_Time']
        if not all(col in df.columns for col in expected_columns):
            return render_template("scheduling.html", error="CSV format incorrect. Must have Job_Name, Machine_Name, Start_Time, End_Time.")

        scheduled_df = pd.DataFrame({
            "Job": df['Job_Name'],
            "Machine": df['Machine_Name'],
            "Start": pd.to_datetime(df['Start_Time']),
            "End": pd.to_datetime(df['End_Time'])
        })

        output_filename = 'scheduled_jobs.csv'
        output_filepath = os.path.join(app.config['UPLOAD_FOLDER'], output_filename)
        scheduled_df.to_csv(output_filepath, index=False)

        return redirect(url_for('visualization_results'))

    return render_template('scheduling.html')

# Visualization Page for Job Scheduling
@app.route('/visualization-results')
def visualization_results():
    output_filepath = os.path.join(app.config['UPLOAD_FOLDER'], 'scheduled_jobs.csv')

    if not os.path.exists(output_filepath):
        return "Scheduled jobs output file not found!"

    df = pd.read_csv(output_filepath)

    gantt_data = []
    for idx, row in df.iterrows():
        gantt_data.append({
            "Task": row['Job'],
            "Machine": row['Machine'],
            "Start": row['Start'],
            "Finish": row['End']
        })

    utilization = df['Machine'].value_counts(normalize=True) * 100
    utilization_data = [{"Machine": machine, "Utilization": round(percent, 2)} for machine, percent in utilization.items()]

    breakdown_alerts = ["⚠️ Example breakdown alert"]
    rescheduling_info = ["🔄 Example rescheduling alert"]

    final_schedule_table = []
    for idx, row in df.iterrows():
        final_schedule_table.append({
            "Job": row['Job'],
            "Machine": row['Machine'],
            "Start": pd.to_datetime(row['Start']).strftime('%H:%M'),
            "End": pd.to_datetime(row['End']).strftime('%H:%M')
        })

    return render_template('visualization.html',
                            gantt_data=json.dumps(gantt_data),
                            utilization_data=json.dumps(utilization_data),
                            breakdown_alerts=json.dumps(breakdown_alerts),
                            rescheduling_info=json.dumps(rescheduling_info),
                            final_schedule_table=json.dumps(final_schedule_table))

# --- Run the Server ---
if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=100)
