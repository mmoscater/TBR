FROM python:latest
COPY requirements.txt requirements.txt
RUN pip install --upgrade pip
RUN pip install -r requirements.txt
COPY . .
ENTRYPOINT [ "python" ]
CMD ["baseball_card.py"]