FROM python:3-alpine3.8

WORKDIR /app

COPY . .

# Install Python dependencies
RUN pip3 install -r requirements.txt

EXPOSE 8000

CMD ["python3", "main.py"]
