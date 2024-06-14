import uvicorn
from app import app

if __name__ == "__main__":
    # uvicorn.run(app, host="0.0.0.0", port=443, reload=True,ssl_keyfile="./key.pem", ssl_certfile="./cert.pem")
    uvicorn.run(app, host="0.0.0.0", port=443)
