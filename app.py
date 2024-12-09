from flask import Flask, render_template_string, request, jsonify
import plotly.graph_objects as go
import plotly.express as px
import pandas as pd
import numpy as np

# Load datasets
top_airports = pd.read_csv('top_airports.csv')
file_path = 'claims-data-2015.xlsx'
df = pd.read_excel(file_path)

# Preprocess datasets
df['Date Received'] = pd.to_datetime(df['Date Received'], errors='coerce')
df['Close Amount'] = pd.to_numeric(df['Close Amount'], errors='coerce')
df['Airline Name'] = df['Airline Name'].str.strip().str.lower()  # Normalize airline names
df = df[df['Item Category'] != '-']  # Remove rows where Item Category is just a dash

# Create map visualization
fig1 = px.scatter_mapbox(top_airports, lat='Latitude', lon='Longitude', size='Number of Claims',
                         color='Total Claim Amount', hover_name='Airport',
                         hover_data={'Number of Claims': True, 'Total Claim Amount': ':.2f'},
                         title="Top Airports by Number of Claims and Claim Amount")
fig1.update_layout(mapbox_style="open-street-map", mapbox_zoom=3, 
                  mapbox_center={"lat": 37.0902, "lon": -95.7129})
fig1.update_traces(marker=dict(sizemode='area', 
                              sizeref=2.*max(top_airports['Number of Claims'])/(40.**2)),
                   hovertemplate="<b>%{hovertext}</b><br>Claims: %{marker.size}<br>Total Claim Amount: $%{marker.color:.2f}<br>")


# 2. Monthly Claim Trends
monthly_claims = df.groupby(df['Date Received'].dt.to_period("M")).size().reset_index(name='Count')
monthly_claims['Date Received'] = monthly_claims['Date Received'].dt.to_timestamp()
fig2 = px.line(monthly_claims, x='Date Received', y='Count', title="Monthly Claim Trends",
               labels={'Date Received': 'Date', 'Count': 'Number of Claims'})
fig2.update_layout(clickmode='event+select', xaxis=dict(rangeslider=dict(visible=True)))
fig2.update_traces(mode='lines+markers', hovertemplate='Date: %{x}<br>Count: %{y}')

# 3. Bubble Chart for Airlines
airline_claims = df.groupby('Airline Name').agg({'Claim Number': 'count', 'Close Amount': 'mean'}).reset_index()
airline_claims.columns = ['Airline', 'Number of Claims', 'Average Settlement']
fig3 = px.scatter(airline_claims, x='Number of Claims', y='Average Settlement', size='Number of Claims',
                  color='Airline', title="Airline vs. Claim Frequency and Settlement",
                  labels={'Number of Claims': 'Number of Claims', 'Average Settlement': 'Average Settlement ($)'},
                  hover_data={'Airline': True, 'Number of Claims': True, 'Average Settlement': ':.2f'})
fig3.update_layout(clickmode='event+select')
fig3.update_traces(hovertemplate="<b>%{customdata[0]}</b><br>Claims: %{x}<br>Average Settlement: $%{y:.2f}<br>")

# Flask web application
app = Flask(__name__)

@app.route('/')
def index():
    html_template = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>Claims Data Visualization</title>
        <script src="https://cdn.plot.ly/plotly-latest.min.js"></script>
    </head>
    <body>
        <h1>Claims Data Analysis</h1>
        <div>
            <h2>Top Airports by Number of Claims and Claim Amount</h2>
            {fig1.to_html(full_html=False)}
        </div>
        <div>
            <h2>Monthly Claim Trends</h2>
            {fig2.to_html(full_html=False)}
        </div>
        <div>
            <h2>Airline vs. Claim Frequency and Settlement</h2>
            {fig3.to_html(full_html=False)}
        </div>
        <div id="dynamic-chart">
            <h2>Dynamic Chart (Click a Bubble to See Details)</h2>
            <div id="dynamic-chart-placeholder"></div>
        </div>
        <script>
            const fetchPieData = (airline) => {{
                fetch(`/get_pie_data?airline=${{airline}}`)
                .then(response => response.json())
                .then(data => {{
                    Plotly.newPlot('dynamic-chart-placeholder', data);
                }});
            }};
            
            document.querySelectorAll('.plotly-graph-div')[2].on('plotly_click', (data) => {{
                const airline = data.points[0].customdata[0];
                console.log("Airline clicked: ", airline);  // Debug log
                fetchPieData(airline);
            }});
        </script>
    </body>
    </html>
    """
    return render_template_string(html_template)

@app.route('/get_pie_data')
def get_pie_data():
    airline = request.args.get('airline').strip().lower()
    print(f"Requested airline: {airline}")  # Debugging

    # Filter the data for the selected airline
    filtered_data = df[df['Airline Name'] == airline]
    print(f"Filtered data for {airline}:\n", filtered_data)  # Debugging

    if filtered_data.empty:
        return jsonify({"error": "No data found for this airline"}), 404

    # Preprocess Item Categories: Take only the first item before the delimiter (;)
    filtered_data['Item Category'] = filtered_data['Item Category'].str.split(';').str[0]
    print(f"Processed Item Categories for {airline}:\n", filtered_data['Item Category'].unique())  # Debugging

    # Generate pie chart for Item Categories
    pie_data = filtered_data['Item Category'].value_counts()
    print(f"Pie data for {airline}:\n", pie_data)  # Debugging

    fig_pie = px.pie(
        values=pie_data.values.tolist(),
        names=pie_data.index.tolist(),
        title=f"Item Categories for {airline}"
    )

    # Ensure all non-JSON serializable objects are converted
    fig_pie_dict = fig_pie.to_dict()
    for trace in fig_pie_dict['data']:
        for key in trace:
            if isinstance(trace[key], pd.Series):
                trace[key] = trace[key].tolist()
            elif isinstance(trace[key], np.ndarray):
                trace[key] = trace[key].tolist()

    return jsonify(fig_pie_dict)


if __name__ == "__main__":
    app.run(debug=True)
