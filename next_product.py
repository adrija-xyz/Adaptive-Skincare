from firebase_admin import firestore
from collections import defaultdict
from firebase_admin import credentials, firestore, initialize_app

ROUTINE_STEPS = ["Cleanser", "Mask", "Moisturiser", "Serum", "Toner"]

def get_next_step_recommendations(user_name: str, current_step: str):
    cred = credentials.Certificate("../adaptive-skin-care-firebase-adminsdk-fbsvc-0589061927.json")
    initialize_app(cred)
    db = firestore.client()

    user_query = db.collection('users').where('name', '==', user_name).limit(1).stream()
    user_doc = next(user_query, None)
        
    if not user_doc:
        print("User not found!")
        return {"error": "User not found"}

    user_data = user_doc.to_dict()
    top_recs = user_data.get('top_recommendations', {})

    if current_step not in ROUTINE_STEPS:
        return {"error": f"'{current_step}' is not a valid routine step."}

    current_index = ROUTINE_STEPS.index(current_step)
    next_steps = ROUTINE_STEPS[current_index + 1:]

    next_recommendations = {}
    for step in next_steps:
        products = top_recs.get(step, [])
        if products:
            next_recommendations[step] = products[0]

    print(next_recommendations)

    return next_recommendations

# get_next_step_recommendations("Heidi Warren","Cleanser")