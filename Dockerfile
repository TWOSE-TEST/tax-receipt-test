FROM ubuntu


RUN apt-get update
RUN apt install tzdata -y
ENV TZ="America/Edmonton"
RUN apt-get install -y python3.10
RUN apt-get install -y python3-pip
RUN apt-get install -y python3.10-distutils
RUN apt-get install -y wkhtmltopdf
WORKDIR /tax-receipts/
COPY requirements.txt requirements.txt
RUN pip install -r requirements.txt

COPY . .

EXPOSE 8000

CMD gunicorn -w 4 -b :8000 app:app

