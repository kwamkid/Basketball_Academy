# Import app from app.py
from app import app

# This is for Cloud Run
if __name__ == "__main__":
    import os
    port = int(os.environ.get('PORT', 8080))
    app.run(debug=False, host='0.0.0.0', port=port)