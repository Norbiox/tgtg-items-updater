FROM python:3.10.7-slim

WORKDIR /src

COPY ./requirements.txt /src/requirements.txt
RUN pip install --no-cache-dir -r /src/requirements.txt

COPY ./main.py  /src/main.py
CMD ["python", "main.py"]