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
#### 6. Run server with runserver_plus to use HTTPS
```
python manage.py runserver_plus --cert-file cert.pem --key-file key.pem
```