## TO RUN THIS PROJECT YOU NEED:

#### 1. Turn .env.example into .env and fill in the available constants 
#### 2. Install dependencies:
```
pip install -r requirements.txt
```
#### 3. Configure and test connection to `PostgresSQL` database
#### 4. Apply migrations 
```
python manage.py migrate
```
#### 5. Generate ENCRYPTION_KEY and add to .env
```
>>> from cryptography.fernet import Fernet
>>> key = Fernet.generate_key()
>>> key
```
#### 6. Run broker
```
 docker run -d -p 5672:5672 rabbitmq
```
#### 7. Run celery beat:
```
 celery -A core beat 
```
#### 8. Run worker:
```
celery -A hilel12 worker -l INFO

or on Windows:
1. pip install eventlet
2. celery -A hilel12 worker -l INFO -P eventlet
```
#### 9. Run server with runserver_plus to use HTTPS
```
python manage.py runserver_plus --cert-file cert.pem --key-file key.pem
```
