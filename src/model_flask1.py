from flask import Flask, request, render_template, redirect, url_for, send_from_directory, jsonify
import pickle
import pandas as pd
from werkzeug.utils import secure_filename
import os
import joblib
import numpy as np
from tensorflow.keras.models import load_model

app = Flask(__name__)

UPLOAD_FOLDER = 'uploads'
ALLOWED_EXTENSIONS = {'csv'}
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

model_pipeline = pickle.load(open("predictive_maintenance_model.pkl", "rb"))
lstm_model = load_model("lstm_model.h5")
scaler = joblib.load("scaler.pkl")
max_rul_value = joblib.load("max_rul.pkl")

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def predict_rul(input_list):
    arr = np.array(input_list).reshape(1, -1)
    scaled = scaler.transform(arr)
    reshaped = scaled.reshape(1, 1, scaled.shape[1])
    prediction = lstm_model.predict(reshaped)[0][0]
    return round(prediction * max_rul_value, 2)

@app.route("/model", methods=["GET"])
def Home():
    return render_template("model.html")

@app.route("/", methods=["GET"])
def Home_main():
    return render_template("home.html")

@app.route("/job-scheduling", methods=["GET", "POST"])
def job_scheduling():
    if request.method == 'POST':
        file = request.files.get('file')
        if not file:
            return "No file uploaded"
        filename = secure_filename(file.filename)
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(filepath)

        df = pd.read_csv(filepath)
        df['Scheduled_Duration'] = (pd.to_datetime(df['Scheduled_End']) - pd.to_datetime(df['Scheduled_Start'])).dt.total_seconds() / 60
        df['Actual_Duration'] = (pd.to_datetime(df['Actual_End']) - pd.to_datetime(df['Actual_Start'])).dt.total_seconds() / 60

        df['Alert'] = ["Delay Alert" if act > sched * 1.5 else "OK"
                       for sched, act in zip(df['Scheduled_Duration'], df['Actual_Duration'])]

        output_file = os.path.join(app.config['UPLOAD_FOLDER'], f"scheduled_{filename}")
        df.to_csv(output_file, index=False)

        return redirect(url_for('download_file', filename=f"scheduled_{filename}"))
    return render_template("scheduling.html")

@app.route("/predict", methods=["POST"])
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

    except ValueError as e:
        return render_template("model.html", prediction_text="Input error: Please enter valid numeric values for all fields.")

    return redirect(url_for('dashboard', **dashboard_data))

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

        except Exception as e:
            return render_template("model.html", error="An error occurred while processing the file. Please ensure it's a valid CSV.")

    return render_template("model.html")

@app.route('/uploads/<filename>')
def download_file(filename):
    try:
        return send_from_directory(app.config['UPLOAD_FOLDER'], filename, as_attachment=True)
    except Exception as e:
        return render_template("model.html", error="File not found or an error occurred while trying to download the file.")

if __name__ == "__main__":
    app.run(debug=True, host='0.0.0.0', port=100)
