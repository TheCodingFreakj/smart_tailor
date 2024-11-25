from django.core.management.base import BaseCommand
from sklearn.calibration import LabelEncoder
from recommendations.models import UserActivity
import joblib
from sklearn.ensemble import RandomForestClassifier
import pandas as pd
from sklearn.model_selection import train_test_split

class Command(BaseCommand):
    help = 'Train the machine learning model based on user activity'

    def handle(self, *args, **kwargs):
        # Fetch data from the database
        activities = UserActivity.objects.all()
        data = pd.DataFrame(list(activities.values('user_id', 'product_id', 'action_type', 'timestamp')))

        # Preprocess the data
        data['timestamp'] = pd.to_datetime(data['timestamp'])
        data['hour_of_day'] = data['timestamp'].dt.hour
        data['day_of_week'] = data['timestamp'].dt.dayofweek
        user_encoder = LabelEncoder()
        data['user_id_encoded'] = user_encoder.fit_transform(data['user_id'])
        action_encoder = LabelEncoder()
        data['action_type_encoded'] = action_encoder.fit_transform(data['action_type'])

        # Feature extraction
        user_product_activity = data.groupby(['user_id', 'product_id']).agg({
            'action_type_encoded': ['sum', 'count'],
            'hour_of_day': 'mean',
            'day_of_week': 'mean'
        }).reset_index()

        user_product_activity.columns = ['user_id', 'product_id', 'action_sum', 'action_count', 'avg_hour_of_day', 'avg_day_of_week']
        
        X = user_product_activity[['action_sum', 'action_count', 'avg_hour_of_day', 'avg_day_of_week']]
        y = user_product_activity['action_sum']

        # Train-test split
        X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

        # Train the RandomForest model
        model = RandomForestClassifier(n_estimators=100, random_state=42)
        model.fit(X_train, y_train)

        # Save the model
        joblib.dump(model, '../../models/user_activity_model.pkl')

        self.stdout.write(self.style.SUCCESS('Model trained and saved successfully!'))
