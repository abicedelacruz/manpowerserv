# Use official Python image
FROM python:3.11-slim
WORKDIR /app
COPY . /app
RUN pip install --no-cache-dir -r requirements.txt
ENV FLASK_APP=app.py
ENV FLASK_ENV=production
EXPOSE 10000
CMD ["gunicorn", "app:app", "-w", "4", "-b", "0.0.0.0:10000"]
