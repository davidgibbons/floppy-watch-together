FROM python:3.13-alpine
WORKDIR /app
COPY floppy_watch_together.py .
USER 65534:65534
ENTRYPOINT ["python", "-u", "floppy_watch_together.py"]
