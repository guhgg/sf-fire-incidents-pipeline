FROM apache/airflow:2.6.2-python3.10

COPY requirements.txt /requirements.txt
RUN pip install --no-cache-dir -r /requirements.txt

COPY airflow_config/webserver_config.py /opt/airflow/webserver_config.py
