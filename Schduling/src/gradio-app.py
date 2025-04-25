import gradio as gr
import pandas as pd
import plotly.express as px
from datetime import datetime

# Core function
def process_jobs(csv_file):
    df = pd.read_csv(csv_file)

    # Convert date columns
    for col in ['Scheduled_Start', 'Scheduled_End', 'Actual_Start', 'Actual_End']:
        df[col] = pd.to_datetime(df[col], errors='coerce')

    # Add Calculated Durations if not present
    df['Calculated_Scheduled_Duration'] = (df['Scheduled_End'] - df['Scheduled_Start']).dt.total_seconds() / 3600
    df['Calculated_Actual_Duration'] = (df['Actual_End'] - df['Actual_Start']).dt.total_seconds() / 3600

    # Identify breakdowns: jobs with 'Failed' or NaT in 'Actual_End'
    breakdowns = df[df['Job_Status'].str.contains('Failed|Delayed', na=False)].copy()

    breakdowns['Alert_Message'] = breakdowns.apply(
        lambda row: f"Machine {row['Machine_ID']} failed during Job {row['Job_ID']}", axis=1
    )

    # Recommend replacements
    def recommend_replacement(row):
        same_ops = df[
            (df['Operation_Type'] == row['Operation_Type']) &
            (df['Machine_ID'] != row['Machine_ID']) &
            (df['Machine_Availability'] > 85)
        ].sort_values(by=['Machine_Availability', 'Energy_Consumption'], ascending=[False, True])
        if not same_ops.empty:
            return same_ops.iloc[0]['Machine_ID']
        return "⚠️ No Replacement Found"

    if not breakdowns.empty:
        breakdowns['Suggested_Replacement'] = breakdowns.apply(recommend_replacement, axis=1)

    # Gantt chart: visualize all jobs
    chart_df = df.dropna(subset=['Scheduled_Start', 'Scheduled_End']).copy()
    chart_df['Duration_Hours'] = chart_df['Calculated_Scheduled_Duration']
    chart = px.timeline(chart_df,
                        x_start="Scheduled_Start", x_end="Scheduled_End",
                        y="Machine_ID", color="Job_Status",
                        hover_name="Job_ID", title="📅 Machine Job Schedule Timeline")
    chart.update_yaxes(autorange="reversed")

    # Return table view and chart
    return df, breakdowns[['Job_ID', 'Machine_ID', 'Alert_Message', 'Suggested_Replacement']], chart

# Gradio Interface
app = gr.Interface(
    fn=process_jobs,
    inputs=gr.File(label="Upload Job Schedule CSV"),
    outputs=[
        gr.Dataframe(label="📋 Full Job Schedule"),
        gr.Dataframe(label="🚨 Breakdown Alerts & Replacements"),
        gr.Plot(label="📈 Job Timeline Visualization")
    ],
    title="🔧 Smart Job Scheduler & Breakdown Monitor",
    description="Upload your manufacturing job schedule CSV. Get visual insights, breakdown alerts, and machine recommendations!"
)

app.launch()
