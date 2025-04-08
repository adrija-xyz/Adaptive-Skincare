import pandas as pd
import json
from collections import defaultdict
from firebase_admin import credentials, firestore, initialize_app

def update_user_top_recommendations():
    cred = credentials.Certificate("../adaptive-skin-care-firebase-adminsdk-fbsvc-0589061927.json")
    initialize_app(cred)
    db = firestore.client()

    users_ref = db.collection('users')
    users_docs = list(users_ref.stream())
    user_list = [doc.to_dict() for doc in users_docs]
    users_df = pd.DataFrame(user_list)
    users_df['doc_id'] = [doc.id for doc in users_docs]

    def get_union(row):
        list1 = row.get('content_recommendations', [])
        list2 = row.get('recommendations_CF', [])
        if not isinstance(list1, list):
            list1 = []
        if not isinstance(list2, list):
            list2 = []
        return list(set(list1) | set(list2))
    
    users_df['combined_recommendations'] = users_df.apply(get_union, axis=1)

    products_ref = db.collection('product')
    products_docs = products_ref.stream()
    product_list = [doc.to_dict() for doc in products_docs]
    products_df = pd.DataFrame(product_list)

    product_type_map = dict(zip(products_df['product_name'], products_df['product_type']))

    for _, row in users_df.iterrows():
        recommendations = row.get('combined_recommendations', [])
        product_type_to_products = defaultdict(list)

        for prod in recommendations:
            prod_type = product_type_map.get(prod, 'Unknown')
            product_type_to_products[prod_type].append({'product': prod})

        for prod_type in product_type_to_products:
            product_type_to_products[prod_type] = product_type_to_products[prod_type][:10]

        doc_id = row['doc_id']
        db.collection('users').document(doc_id).update({
            'top_recommendations': dict(product_type_to_products)
        })

    print("Top recommendations updated in Firestore.")

# update_user_top_recommendations()