FROM apache/airflow:2.9.2

# Bake project dependencies into the image instead of installing them on every
# container boot (the _PIP_ADDITIONAL_REQUIREMENTS approach is dev-only/fragile).
COPY requirements-airflow.txt /requirements-airflow.txt
RUN pip install --no-cache-dir -r /requirements-airflow.txt
