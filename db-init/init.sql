CREATE TABLE IF NOT EXISTS dim_time (
    time_key SERIAL PRIMARY KEY,
    call_date DATE NOT NULL,
    year INT NOT NULL,
    month INT NOT NULL,
    day INT NOT NULL,
    weekday VARCHAR(10) NOT NULL
);

CREATE TABLE IF NOT EXISTS dim_district (
    district_key SERIAL PRIMARY KEY,
    district_name VARCHAR(50) UNIQUE NOT NULL,
    station_area INT,
    supervisor_district INT
);

CREATE TABLE IF NOT EXISTS dim_battalion (
    battalion_key SERIAL PRIMARY KEY,
    battalion_name VARCHAR(50) UNIQUE NOT NULL
);

CREATE TABLE IF NOT EXISTS fact_fire_incidents (
    incident_number INT PRIMARY KEY,
    time_key INT REFERENCES dim_time(time_key),
    district_key INT REFERENCES dim_district(district_key),
    battalion_key INT REFERENCES dim_battalion(battalion_key),
    zipcode VARCHAR(10),
    incident_type VARCHAR(255),
    property_loss FLOAT,
    alarm_count INT,
    incident_count INT NOT NULL
);
