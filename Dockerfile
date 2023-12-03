FROM python:3.11
RUN apt update && apt install -y libgl1
ADD ./requirements.txt /tmp/requirements.txt
RUN pip install -r /tmp/requirements.txt
ADD . /code
WORKDIR /code
EXPOSE 5001
CMD ["python", "ICP-Checker.py"]
