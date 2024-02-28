FROM python:3.9-slim-bullseye as base

FROM base as build

# Install dependencies
COPY requirements.txt requirements.txt
RUN apt-get update && apt-get install -y libpq-dev gcc \
    && pip install --user --no-cache-dir -r requirements.txt \
    && rm -rf /var/lib/apt/lists/*

# Install Heralding
COPY . .
RUN python setup.py install --user

FROM base
COPY --from=build /root/.local /root/.local

ENV PATH=/root/.local/bin:$PATH

CMD ["heralding" ]
EXPOSE 21 22 23 25 80 110 143 443 465 993 995 1080 2222 3306 3389 5432 5900
