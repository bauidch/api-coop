FROM python:3.6-slim

COPY --chown=1000 requirements.txt requirements.txt
RUN pip install -U pip && pip install -r requirements.txt

COPY --chown=1000 ./src /app/src
COPY --chown=1000 wsgi.py /app/wsgi.py

COPY --chown=1000 resources/entrypoint.sh /entrypoint.sh

ENTRYPOINT [ "/entrypoint.sh" ]
