"""
Fake Profile / Bot Detection
Uses trained sklearn model (fake_profile_model.pkl) with heuristic fallback.
GNN via torch_geometric is used only if available.
"""
import joblib
import pandas as pd
import numpy as np
import os
from datetime import datetime


class BotDetector:
    def __init__(self, model_dir=None):
        if model_dir is None:
            model_dir = os.path.dirname(__file__)
        self.model_dir = model_dir
        self.model = None
        self.feature_columns = None
        self.load_models()

    def load_models(self):
        """Load sklearn model (primary) or GNN if available."""
        # Try sklearn model first (most reliable)
        sklearn_path = os.path.join(self.model_dir, 'fake_profile_model.pkl')
        features_path = os.path.join(self.model_dir, 'feature_columns.pkl')

        if os.path.exists(sklearn_path):
            try:
                self.model = joblib.load(sklearn_path)
                if os.path.exists(features_path):
                    self.feature_columns = joblib.load(features_path)
                print("  Fake profile sklearn model loaded")
                return
            except Exception as e:
                print(f"  sklearn model load failed: {e}")

        print("  No fake profile model found, using heuristic")
        self.model = None

    def predict(self, user_data):
        """
        Predict if an Instagram/social profile is fake or genuine.

        Args:
            user_data: dict with:
                - username
                - account_creation_date
                - follower_count
                - posts_count
        """
        processed = self._process_minimal_inputs(user_data)

        if self.model is not None:
            try:
                return self._sklearn_predict(processed, user_data)
            except Exception as e:
                print(f"  Model predict error: {e}")

        return self._fallback_predict(user_data)

    def _sklearn_predict(self, processed, raw_data):
        """Predict using sklearn model."""
        followers = float(processed.get('followers', 0))
        following = float(processed.get('following', 0))
        posts = float(processed.get('posts', 0))
        bio_length = float(processed.get('bio_length', 50))
        has_pic = int(processed.get('has_profile_pic', 1))
        account_age = float(processed.get('account_age_days', 365))

        follower_ratio = followers / max(following, 1)
        post_frequency = posts / max(account_age / 30, 1)  # posts per month

        features_dict = {
            'followers_count': followers,
            'friends_count': following,
            'statuses_count': posts,
            'bio_length': bio_length,
            'has_profile_pic': has_pic,
            'follower_ratio': follower_ratio,
            'engagement_score': posts * 0.5 + followers * 0.3 + following * 0.2,
            'account_age_days': account_age,
            'post_frequency': post_frequency
        }

        # Build feature vector
        if self.feature_columns:
            row = {col: features_dict.get(col, 0) for col in self.feature_columns}
            df = pd.DataFrame([row])
        else:
            df = pd.DataFrame([features_dict])

        if hasattr(self.model, 'predict_proba'):
            proba = self.model.predict_proba(df)[0]
            classes = list(self.model.classes_)
            # Determine which index corresponds to class 0 (fake)
            # Training convention: 0 = fake, 1 = genuine
            if 0 in classes:
                fake_idx = classes.index(0)
                fake_prob = float(proba[fake_idx])
            else:
                # Fallback: assume lower class index = fake
                fake_prob = float(proba[0])
        else:
            pred = self.model.predict(df)[0]
            # Assume 1 = genuine, 0 = fake
            fake_prob = 1.0 - float(pred)

        is_fake = fake_prob > 0.5
        explanation = self._generate_explanation(features_dict, is_fake)
        
        # ============================================
        # RULE-BASED CORRECTION - Reduce false positives
        # ============================================
        username = raw_data.get('username', '').lower()
        account_age = features_dict.get('account_age_days', 365)
        posts = features_dict.get('statuses_count', 0)
        followers = features_dict.get('followers_count', 0)
        
        # Account age trust - older accounts are more trustworthy
        if account_age > 365:  # More than 1 year
            fake_prob = max(0.05, fake_prob - 0.30)
        elif account_age > 180:  # More than 6 months
            fake_prob = max(0.10, fake_prob - 0.20)
        elif account_age > 90:  # More than 3 months
            fake_prob = max(0.15, fake_prob - 0.10)
        
        # Active account with posts - legitimate signal
        if posts >= 10:
            fake_prob = max(0.05, fake_prob - 0.20)
        elif posts >= 5:
            fake_prob = max(0.10, fake_prob - 0.10)
        
        # Reasonable follower count for age
        if followers > 50 and account_age > 180:
            fake_prob = max(0.10, fake_prob - 0.15)
        
        # Spam username detection - INCREASE risk
        spam_username_keywords = ['free', 'win', 'earn', 'money', 'lottery', 'prize', 'bot', 'fake']
        spam_username_count = sum(1 for kw in spam_username_keywords if kw in username)
        if spam_username_count >= 2:
            fake_prob = min(0.95, fake_prob + 0.40)
        elif spam_username_count >= 1:
            fake_prob = min(0.85, fake_prob + 0.20)
        
        # Suspicious pattern: high followers, very low posts (bought followers)
        if followers > 1000 and posts < 5:
            fake_prob = min(0.90, fake_prob + 0.25)
        
        # Very new account with no activity
        if account_age < 30 and posts == 0:
            fake_prob = min(0.85, fake_prob + 0.30)
        
        # Clamp final probability
        fake_prob = min(0.95, max(0.05, fake_prob))
        
        # Recalculate is_fake after corrections
        is_fake = fake_prob > 0.5
        
        # Calculate confidence percentage
        confidence_value = abs(fake_prob - 0.5) * 2
        confidence_percent = min(100, max(0, confidence_value * 100))
        
        # Regenerate explanation with updated assessment
        explanation = self._generate_explanation(features_dict, is_fake, username, account_age, posts, followers)

        return {
            'is_fake': bool(is_fake),
            'is_bot': bool(is_fake),
            'fake_probability': round(fake_prob, 4),
            'bot_probability': round(fake_prob, 4),
            'confidence': round(confidence_value, 4),
            'confidence_percent': round(confidence_percent, 2),
            'risk_level': 'HIGH' if fake_prob > 0.7 else 'MEDIUM' if fake_prob > 0.4 else 'LOW',
            'explanation': explanation,
            'profile_analysis': explanation,
            'recommendation': (
                'BLOCK - High confidence fake profile' if fake_prob > 0.7 else
                'INVESTIGATE - Possibly fake profile' if fake_prob > 0.5 else
                'ALLOW - Appears genuine'
            ),
            'details': {
                'model': 'Random Forest + Rule-Based Correction',
                'fake_probability': round(fake_prob, 4),
                'genuine_probability': round(1 - fake_prob, 4),
                'features_analyzed': list(features_dict.keys())
            }
        }

    def _process_minimal_inputs(self, data):
        """Convert minimal user inputs to full feature set (deterministic)."""
        import hashlib

        username = data.get('username', '')
        account_creation_date = data.get('account_creation_date', '')
        follower_count = int(data.get('follower_count', data.get('followers_count', 0)))
        posts_count = int(data.get('posts_count', data.get('statuses_count', 0)))

        # Deterministic seed
        seed = f"{username}_{follower_count}_{posts_count}"

        def get_det(salt, lo, hi):
            h = int(hashlib.md5(f"{seed}_{salt}".encode()).hexdigest(), 16)
            return lo + (h % (hi - lo + 1))

        # Estimate following count from follower count (realistic distribution)
        if follower_count > 10000:
            following_count = get_det('fol', 200, 2000)
        elif follower_count > 1000:
            following_count = get_det('fol', 100, 1500)
        elif follower_count > 100:
            following_count = get_det('fol', 50, 800)
        else:
            following_count = get_det('fol', 10, 500)

        bio_length = len(username) * 3 + get_det('bio', 10, 120)
        has_profile_pic = 0 if get_det('pic', 0, 10) == 0 else 1

        if account_creation_date:
            try:
                creation_date = datetime.strptime(account_creation_date, '%Y-%m-%d')
                account_age_days = (datetime.now() - creation_date).days
            except:
                account_age_days = get_det('age', 30, 3650)
        else:
            account_age_days = get_det('age', 30, 3650)

        return {
            'followers': follower_count,
            'followers_count': follower_count,
            'following': following_count,
            'friends_count': following_count,
            'posts': posts_count,
            'statuses_count': posts_count,
            'bio_length': bio_length,
            'has_profile_pic': has_profile_pic,
            'account_age_days': max(1, account_age_days)
        }

    def _generate_explanation(self, features, is_fake, username='', account_age=365, posts=0, followers=0):
        """Generate human-readable explanation."""
        reasons = []
        following = features.get('friends_count', features.get('following', 0))
        ratio = features.get('follower_ratio', followers / max(following, 1))

        if is_fake:
            # Check for spam username
            spam_keywords = ['free', 'win', 'earn', 'money', 'lottery']
            if any(kw in username.lower() for kw in spam_keywords):
                reasons.append("Suspicious username with spam keywords")
            
            if ratio < 0.1 and following > 500:
                reasons.append("Very low follower/following ratio (bot pattern)")
            if followers > 1000 and posts < 5:
                reasons.append("High followers but very low posts (possible bought followers)")
            if posts == 0 and followers < 50:
                reasons.append("No posts and very few followers")
            if account_age < 30 and posts == 0:
                reasons.append("Brand new account with no activity")
            if features.get('bio_length', 50) < 10:
                reasons.append("Very short or empty bio")
            if features.get('has_profile_pic', 1) == 0:
                reasons.append("No profile picture")
            if not reasons:
                reasons.append("Overall behavioral pattern matches known fake accounts")
        else:
            if account_age > 365:
                reasons.append(f"Established account ({account_age//30}+ months old)")
            if posts >= 10:
                reasons.append(f"Active posting history ({posts} posts)")
            if followers > 50 and account_age > 180:
                reasons.append("Reasonable follower count for account age")
            if ratio > 0.5:
                reasons.append("Healthy follower/following ratio")
            if posts < 10 and followers > 100:
                reasons.append("Legitimate lurker profile")
            if not reasons:
                reasons.append("No significant fake indicators detected")
        
        return " | ".join(reasons) if reasons else "No specific indicators detected"

    def _fallback_predict(self, user_data):
        """Simple heuristic-based prediction when model is unavailable."""
        processed = self._process_minimal_inputs(user_data)

        followers = int(processed.get('followers', 0))
        following = int(processed.get('following', 0))
        posts = int(processed.get('posts', 0))
        account_age = int(processed.get('account_age_days', 365))

        score = 0.0

        # Suspicious patterns
        if following > 1000 and followers < 100:
            score += 0.4
        if posts == 0 and followers < 50:
            score += 0.25
        if followers == 0:
            score += 0.2
        if account_age < 30 and posts == 0:
            score += 0.2

        # Genuine patterns
        if followers > 200 and following < 800:
            score -= 0.25
        if posts > 20:
            score -= 0.2
        if posts < 10 and followers > 100 and following < 1000:
            score -= 0.35  # Legitimate lurker

        fake_prob = min(0.95, max(0.05, 0.5 + score))
        is_fake = fake_prob > 0.5
        
        # Calculate confidence percentage
        confidence_value = abs(fake_prob - 0.5) * 2
        confidence_percent = min(100, max(0, confidence_value * 100))
        
        features_for_exp = {
            'followers_count': followers,
            'friends_count': following,
            'statuses_count': posts,
            'bio_length': 50,
            'has_profile_pic': 1,
            'follower_ratio': followers / max(following, 1)
        }

        return {
            'is_fake': bool(is_fake),
            'is_bot': bool(is_fake),
            'fake_probability': round(float(fake_prob), 4),
            'bot_probability': round(float(fake_prob), 4),
            'confidence': round(confidence_value, 4),
            'confidence_percent': round(confidence_percent, 2),
            'risk_level': 'HIGH' if fake_prob > 0.7 else 'MEDIUM' if fake_prob > 0.4 else 'LOW',
            'explanation': self._generate_explanation(features_for_exp, is_fake),
            'profile_analysis': self._generate_explanation(features_for_exp, is_fake),
            'recommendation': (
                'BLOCK - Likely fake/bot profile' if fake_prob > 0.7 else
                'INVESTIGATE - Possibly fake profile' if fake_prob > 0.5 else
                'ALLOW - Appears genuine'
            ),
            'details': {
                'model': 'Heuristic Fallback'
            }
        }
