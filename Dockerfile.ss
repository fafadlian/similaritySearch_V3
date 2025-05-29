FROM python:3.10.17-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app ./app

EXPOSE 443

CMD ["uvicorn", "app.__init__:create_app", "--factory", "--host", "0.0.0.0", "--port", "443"]
