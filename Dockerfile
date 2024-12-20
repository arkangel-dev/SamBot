FROM ultrafunk/undetected-chromedriver
WORKDIR /app
COPY requirements.txt /app
RUN pip install --no-cache-dir -r requirements.txt
COPY . /app
CMD ["python", "run.py"]