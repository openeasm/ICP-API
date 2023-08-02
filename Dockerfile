FROM python3:latest
ADD ./requirements.txt /tmp/requirements.txt
RUN pip install -r /tmp/requirements.txt
ADD . /code
WORKDIR /code
CMD ["python", "app.py"]