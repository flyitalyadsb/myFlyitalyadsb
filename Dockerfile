FROM python:latest
ENV PYTHONUNBUFFERED 1
WORKDIR /
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

EXPOSE 830

CMD ["python", "main.py"]
