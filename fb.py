import firebase_admin
from firebase_admin import credentials, db

# Firebase setup
if not firebase_admin._apps:
    cred = credentials.Certificate("serviceAccountKey.json")
    firebase_admin.initialize_app(cred, {
        'databaseURL': 'https://athentication-3c73e-default-rtdb.firebaseio.com/'
    })

def test_firebase():
    try:
        ref = db.reference('/complaints')
        ref.push({
            'role': "Test",
            'issue': "This is a test issue"
        })
        print("Issue submitted to Firebase.")
    except Exception as e:
        print(f"Error saving to Firebase: {e}")

test_firebase()
