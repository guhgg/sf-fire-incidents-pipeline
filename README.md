
# San Francisco Fire Incidents ETL Pipeline
  
This project provides an **ETL pipeline** to extract, transform, and load fire incidents data from the San Francisco government dataset into a **PostgreSQL data warehouse**. The solution leverages **Airflow** to schedule daily loads, and a **star schema** to optimize query performance.

---

  
## Solution Overview

  

### Assumptions:

- The dataset is **updated daily** at the source.

- The fact table (`fact_fire_incidents`) stores fire incidents data. Dimensions (`dim_time`, `dim_district`, and `dim_battalion`) support analytical queries.

- The **schema follows a star model** to enable efficient aggregation.

-  **Airflow** manages the ETL process using a **daily DAG** to fetch new data from the source API.

  

### Key Components:

1.  **Airflow DAG:** Orchestrates the ETL process, including extracting data, transforming it, and loading it into PostgreSQL.

2.  **Docker Compose:** Sets up a local development environment with:

-  **PostGIS** database for the warehouse.

-  **PgAdmin:** For managing and inspecting the database.

3.  **PostgreSQL Star Schema:**

-  **Fact Table:** Stores fire incident records.

-  **Dimension Tables:** Time, District, and Battalion dimensions to support slicing and dicing data.

  

---

  

## Project Setup

  

### Prerequisites:

-  **Docker** and **Docker Compose** installed.

- Clone the repository containing this project.

  

### Steps to Run the Project:

1.  **Clone the repository:**

```bash

git clone sf-fire-incidents-pipeline

cd sf-fire-incidents-pipeline
```

2.  **Start the Docker services:**
```bash
docker-compose up -d
```
3.  **Wait for the airflow and database initialization:**
4.  **Access the following services:**
    
    -   **Airflow Web UI:** http://localhost:8080  
    -   **PgAdmin:** http://localhost:5050  
        (Login: `admin@admin.com` / `admin`)
        -- Host: db
        -- Port: 5432
        -- Username: postgres
        -- Password: postgres
        -- Database: fire_incidents_db
    -   **PostgreSQL:** `localhost:5432` (Database: `fire_incidents_db`)
4.  **Trigger the DAG:** In the Airflow UI, navigate to **DAGs**, find the `sf_fire_incidents_star_schema_etl` DAG, and trigger it manually to start the ETL process.

## **Database Schema**

-   **Fact Table:** `fact_fire_incidents`
   
| Column          | Data Type | Description                         |
|-----------------|-----------|-------------------------------------|
| incident_number | INT       | Unique ID for each incident         |
| time_key        | INT       | Foreign key to time dimension       |
| district_key    | INT       | Foreign key to district dimension   |
| battalion_key   | INT       | Foreign key to battalion dimension  |
| zipcode         | VARCHAR   | Zip code of the incident            |
| incident_type   | VARCHAR   | Description of the incident         |
| property_loss   | FLOAT     | Estimated property loss             |
| alarm_count     | INT       | Number of alarms for the incident   |
| incident_count  | INT       | Number of incidents (default 1)     |

    
-   **Dimension Tables:**
    
    -   **`dim_time`**: Stores date-related information (year, month, day).
    -   **`dim_district`**: Contains neighborhood district details.
    -   **`dim_battalion`**: Stores battalion information.

## **Report Example**

### **Query: Total Incidents by District and Year**

This report aggregates the total number of incidents and estimated property loss by **district** and **year**.

```sql
SELECT 
    t.year,
    d.district_name,
    COUNT(f.incident_number) AS total_incidents,
    SUM(f.property_loss) AS total_property_loss
FROM fact_fire_incidents f
JOIN dim_time t ON f.time_key = t.time_key
JOIN dim_district d ON f.district_key = d.district_key
GROUP BY t.year, d.district_name
ORDER BY total_incidents DESC;
```

| Year| District       | Total Incidents | Total Property Loss
|-----|----------------|-----------------| --------------------|
|2019 |Tenderloin      | 500             | 120000.00           |
|2019 |South of Market | 430             | 95000.00            |
|2019 |Outer Richmond  | 300             | 50000.00            |

## **Troubleshooting**

-   **Airflow Webserver/Scheduler Not Running:** Ensure the services are healthy by checking:
           
    `docker ps
    docker logs airflow_webserver` 
    
-   **Database Connection Issues:** Confirm the PostgreSQL services are running and available on port 5432:
            
    `docker logs fire_incidents_db` 
    
-   **PgAdmin Login Failure:** If login fails, try restarting the **pgadmin** service:
            
    `docker-compose restart pgadmin` 
    