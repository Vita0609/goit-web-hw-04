FROM python:3.12-slim


WORKDIR /app


COPY . /app


COPY requirements.txt /app/
RUN pip install --no-cache-dir -r requirements.txt


EXPOSE 3000
EXPOSE 5000


ENV NAME World
ENV SOCKET_HOST 0.0.0.0


CMD ["python", "main.py"]
