
# Project Setup and Deployment

This guide walks you through setting up the application, installing dependencies, configuring PostgreSQL, and running the Gunicorn server.

## Prerequisites

Before starting, ensure you have the following installed on your server:

- **Git**: To clone the repository
- **Python 3.8+**: For running the Python application
- **PostgreSQL**: As the database for the application
- **Gunicorn**: To run the application server
- **UFW (Uncomplicated Firewall)**: For managing firewall rules

## Steps

### 1. **Update and Install Git**

```bash
sudo apt update
sudo apt install git -y
```

### 2. **Clone the Repository**

```bash
git clone https://github.com/NaUzAr/app
cd app
```

### 3. **Update and Upgrade the System**

```bash
sudo apt update
sudo apt upgrade -y
```

### 4. **Install PostgreSQL**

First, install the required dependencies and PostgreSQL:

```bash
sudo apt install -y wget gnupg
wget -qO - https://www.postgresql.org/media/keys/ACCC4CF8.asc | sudo apt-key add -
echo "deb http://apt.postgresql.org/pub/repos/apt $(lsb_release -cs)-pgdg main" | sudo tee /etc/apt/sources.list.d/pgdg.list
sudo apt update
sudo apt install -y postgresql postgresql-contrib
```

### 5. **Configure PostgreSQL**

Start and enable the PostgreSQL service:

```bash
sudo systemctl start postgresql
sudo systemctl enable postgresql
```

Switch to the `postgres` user and create a database and user:

```bash
sudo -u postgres psql <<EOF
CREATE DATABASE myapi_db;
CREATE USER myapi_user WITH ENCRYPTED PASSWORD 'securepassword';
GRANT ALL PRIVILEGES ON DATABASE myapi_db TO myapi_user;
\q
EOF
```

### 6. **Install Python 3.8 and Create Virtual Environment**

Install Python and `python3.8-venv`:

```bash
sudo apt install -y python3.8-venv
```

Create a virtual environment and activate it:

```bash
python3 -m venv myenv
source myenv/bin/activate
```

Install Python dependencies from `requirements.txt`:

```bash
pip install -r requirements.txt
```

### 7. **Configure PostgreSQL User Privileges**

Switch to the `postgres` user again and grant the necessary privileges:

```bash
sudo -i -u postgres psql <<EOF
\c myapi_db
GRANT ALL PRIVILEGES ON SCHEMA public TO myapi_user;
GRANT ALL PRIVILEGES ON DATABASE myapi_db TO myapi_user;
ALTER USER myapi_user WITH SUPERUSER;
\du myapi_user
\q
EOF
```

### 8. **Allow Port 7000 Through Firewall**

If you are using **UFW** to manage your firewall, you need to allow traffic on port 7000 (the port used by Gunicorn):

1. **Check if UFW is installed**:

```bash
sudo apt install ufw
```

2. **Allow traffic on port 7000**:

```bash
sudo ufw allow 7000/tcp
```

3. **Enable UFW** (if it is not enabled already):

```bash
sudo ufw enable
```

4. **Check UFW status** to confirm the rule is added:

```bash
sudo ufw status
```

You should see an entry allowing traffic on port 7000.

### 9. **Run Gunicorn Server**

To run the application using Gunicorn with Uvicorn workers, use the following command:

```bash
gunicorn app.main:app --workers 4 --worker-class uvicorn.workers.UvicornWorker --bind 0.0.0.0:7000
```

### 10. **Verify the Server**

You should now be able to access your application on port `7000` by navigating to `http://<your-server-ip>:7000`. If there are any issues, check the firewall and Gunicorn logs for troubleshooting.

---

### Troubleshooting

- **Firewall issues**: If you're unable to access the server, ensure that UFW allows traffic on port 7000, or check if other firewall services (e.g., `iptables`) are blocking access.
- **Gunicorn not starting**: Make sure you have all necessary dependencies installed and that there are no issues with your codebase.
