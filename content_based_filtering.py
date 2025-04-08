import pandas as pd
import numpy as np
from sklearn.metrics.pairwise import cosine_similarity
from sklearn.preprocessing import MinMaxScaler
from collections import Counter
from geopy.distance import geodesic

import firebase_admin
from firebase_admin import credentials, firestore

# Initialize Firebase
cred = credentials.Certificate("./adaptive-skin-care-firebase-adminsdk-fbsvc-0589061927.json")
firebase_admin.initialize_app(cred)
db = firestore.client()

# Load products
products_ref = db.collection('product')
products_docs = products_ref.stream()
product_list = [doc.to_dict() for doc in products_docs]
products_df = pd.DataFrame(product_list)

# Load users
users_ref = db.collection('users')
users_docs = users_ref.stream()
user_list = [doc.to_dict() for doc in users_docs]
users_df = pd.DataFrame(user_list)

# Clean price and normalize
products_df['price'] = products_df['price'].str.replace('£', '', regex=False).astype(float)
scaler = MinMaxScaler()
products_df['normalized_price'] = scaler.fit_transform(products_df[['price']])

# Create product feature matrix
product_features = products_df.apply(
    lambda row: row['concern_vector'] + [row['economics']],
    axis=1
).tolist()
product_matrix = np.array(product_features)

# Loop through users and print top 25 recommendations
for user in user_list:
    try:
        user_name = user['name']
        preferred_brands = []

        # Collect brands from user interaction
        for product_name in user['likes'] + user['browsing_history'] + user['cart']:
            brand = products_df[products_df['product_name'] == product_name]['brand_name'].values
            if brand.size > 0:
                preferred_brands.append(brand[0])
        brand_scores = Counter(preferred_brands)

        # Construct user vector
        user_concern_vector = user['concerns']
        user_price_pref = user['price_pref']
        user_vector = np.array(user_concern_vector + [user_price_pref]).reshape(1, -1)

        # Filter products to exclude
        disliked = user['dislikes']
        cart = user['cart']
        exclude_products = set(disliked + cart)
        filtered_products = products_df[~products_df['product_name'].isin(exclude_products)].reset_index(drop=True)

        # Product matrix after filtering
        filtered_product_matrix = np.array([
            row['concern_vector'] + [row['economics']]
            for _, row in filtered_products.iterrows()
        ])

        # Brand boost
        filtered_products['brand_boost'] = filtered_products['brand_name'].apply(lambda brand: brand_scores.get(brand, 0))

        # Distance boost
        user_loc = tuple(user['address'])
        def get_distance(warehouse_loc):
            if isinstance(warehouse_loc, str):
                warehouse_loc = eval(warehouse_loc)
            return geodesic(user_loc, tuple(warehouse_loc)).km
        filtered_products['distance_km'] = filtered_products['warehouse'].apply(get_distance)
        filtered_products['distance_boost'] = 1 / (filtered_products['distance_km'] + 1)

        # Similarity score
        similarities = cosine_similarity(user_vector, filtered_product_matrix)[0]
        filtered_products['similarity'] = similarities

        # Final score
        filtered_products['final_score'] = (
            0.6 * filtered_products['similarity'] +
            0.2 * filtered_products['brand_boost'] +
            0.2 * filtered_products['distance_boost']
        )

        # Top 25 recommendations
        top_25 = filtered_products.sort_values(by='final_score', ascending=False).head(25)
        recommended_products = top_25['product_name'].tolist()

        # Print result
        print(f"Top 25 Recommendations for {user_name}:")
        for i, product in enumerate(recommended_products, 1):
            print(f"{i}. {product}")

    except Exception as e:
        print(f"Failed for user {user.get('name', 'Unknown')}: {str(e)}")
