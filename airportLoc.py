import pandas as pd

# Load claims dataset
file_path = 'claims-data-2015.xlsx' 
df = pd.read_excel(file_path)

# Convert 'Close Amount' to numeric, coercing errors
df['Close Amount'] = pd.to_numeric(df['Close Amount'], errors='coerce')

# Download and process airport location data
url = 'https://raw.githubusercontent.com/jpatokal/openflights/master/data/airports.dat'
columns = [
    'Airport ID', 'name', 'city', 'country', 'IATA', 'ICAO', 'latitude_deg', 'longitude_deg',
    'altitude', 'timezone', 'DST', 'tz', 'type', 'source'
]

try:
    airport_data = pd.read_csv(url, header=None, names=columns)
except Exception as e:
    print(f"Error downloading data: {e}")
    # Use local file if download fails
    airport_data = pd.read_csv('airports.dat', header=None, names=columns)

airport_locations = airport_data[['name', 'latitude_deg', 'longitude_deg']].copy()
airport_locations.columns = ['Airport', 'Latitude', 'Longitude']

# Clean airport names to ensure matching
df['Airport Name'] = df['Airport Name'].str.strip().str.upper()
airport_locations.loc[:, 'Airport'] = airport_locations['Airport'].str.strip().str.upper()

# Merge claims data with location data
top_airports = df.groupby('Airport Name').agg({'Claim Number': 'count', 'Close Amount': 'sum'}).nlargest(10, 'Claim Number').reset_index()
top_airports.columns = ['Airport', 'Number of Claims', 'Total Claim Amount']
top_airports = pd.merge(top_airports, airport_locations, left_on='Airport', right_on='Airport')

# Save the merged data to CSV
top_airports.to_csv('top_airports.csv', index=False)